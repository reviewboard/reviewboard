from __future__ import unicode_literals

import bz2
import gc
import hashlib
import os
import warnings

from django.conf import settings
from django.db import models, reset_queries, connection
from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.utils.encoding import smart_unicode
from django.utils.six.moves import range
from django.utils.translation import ugettext as _
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.diffviewer.differ import DiffCompatVersion
from reviewboard.diffviewer.errors import DiffTooBigError, EmptyDiffError
from reviewboard.scmtools.core import PRE_CREATION, UNKNOWN, FileNotFoundError


class FileDiffManager(models.Manager):
    """A manager for FileDiff objects.

    This contains utility methods for locating FileDiffs that haven't been
    migrated to use RawFileDiffData.
    """
    MIGRATE_OBJECT_LIMIT = 200

    def unmigrated(self):
        """Queries FileDiffs that store their own diff content."""
        return self.exclude(
            (Q(diff64='') | Q(diff64__isnull=True)) &
            (Q(parent_diff64='') | Q(parent_diff64__isnull=True)))

    def get_migration_counts(self):
        """Returns the number of items that need to be migrated.

        The result is a dictionary containing a breakdown of the various
        counts, and the total count of all items for display.
        """
        from reviewboard.diffviewer.models import LegacyFileDiffData

        unmigrated_filediffs_count = self.unmigrated().count()
        legacy_fdd_count = LegacyFileDiffData.objects.count()

        return {
            'filediffs': unmigrated_filediffs_count,
            'legacy_file_diff_data': legacy_fdd_count,
            'total_count': unmigrated_filediffs_count + legacy_fdd_count,
        }

    def migrate_all(self, batch_done_cb=None, counts=None, batch_size=40):
        """Migrates diff content in FileDiffs to use RawFileDiffData.

        This will run through all unmigrated FileDiffs and migrate them,
        condensing their storage needs and removing the content from
        FileDiffs.

        This will return a dictionary with the result of the process.
        """
        from reviewboard.diffviewer.models import LegacyFileDiffData

        total_diffs_migrated = 0
        total_diff_size = 0
        total_bytes_saved = 0

        unmigrated_filediffs = self.unmigrated()
        legacy_data_items = LegacyFileDiffData.objects.all()

        if counts:
            unmigrated_filediffs_count = counts['filediffs']
            legacy_data_items_count = counts['legacy_file_diff_data']
            total_count = counts['total_count']
        else:
            unmigrated_filediffs_count = unmigrated_filediffs.count()
            legacy_data_items_count = legacy_data_items.count()
            total_count = legacy_data_items_count + unmigrated_filediffs_count

        migration_tasks = (
            (self._migrate_filediffs,
             unmigrated_filediffs,
             unmigrated_filediffs_count),
            (self._migrate_legacy_fdd,
             legacy_data_items,
             legacy_data_items_count),
        )

        for migrate_func, queryset, count in migration_tasks:
            for batch_info in migrate_func(queryset, count, batch_size):
                total_diffs_migrated += batch_info[0]
                total_diff_size += batch_info[1]
                total_bytes_saved += batch_info[2]

                if callable(batch_done_cb):
                    batch_done_cb(total_diffs_migrated, total_count)

        return {
            'diffs_migrated': total_diffs_migrated,
            'old_diff_size': total_diff_size,
            'new_diff_size': total_diff_size - total_bytes_saved,
            'bytes_saved': total_bytes_saved,
        }

    def _migrate_legacy_fdd(self, legacy_data_items, count, batch_size):
        """Migrates data from LegacyFileDiffData to RawFileDiffData.

        This will go through every LegacyFileDiffData and convert them to
        RawFileDiffData entries, removing the old versions. All associated
        FileDiffs are then updated to point to the new RawFileDiffData entry
        instead of the old LegacyFileDiffData.
        """
        from reviewboard.diffviewer.models import RawFileDiffData

        cursor = connection.cursor()

        legacy_data_items = legacy_data_items.annotate(
            num_filediffs=Count('filediffs'),
            num_parent_filediffs=Count('parent_filediffs'))

        for batch in self._iter_batches(legacy_data_items, count, batch_size):
            batch_total_diff_size = 0
            batch_total_bytes_saved = 0
            raw_fdds = []
            all_diff_hashes = []
            filediff_hashes = []
            parent_filediff_hashes = []

            for legacy_fdd in batch:
                raw_fdd = RawFileDiffData.objects.create_from_legacy(
                    legacy_fdd, save=False)

                raw_fdds.append(raw_fdd)

                binary_hash = legacy_fdd.binary_hash

                old_diff_size = len(legacy_fdd.get_binary_base64())
                batch_total_diff_size += old_diff_size
                batch_total_bytes_saved += old_diff_size - len(raw_fdd.binary)

                # Update all associated FileDiffs to use the new objects
                # instead of the old ones.
                if legacy_fdd.num_filediffs > 0:
                    filediff_hashes.append(binary_hash)

                if legacy_fdd.num_parent_filediffs > 0:
                    parent_filediff_hashes.append(binary_hash)

                all_diff_hashes.append(binary_hash)

            try:
                # Attempt to create all the entries we want in one go.
                RawFileDiffData.objects.bulk_create(raw_fdds)
            except IntegrityError:
                # One or more entries in the batch conflicte with an existing
                # entry, meaning it was already created. We'll just need to
                # operate on the contents of this batch one-by-one.
                for raw_fdd in raw_fdds:
                    try:
                        raw_fdd.save()
                    except IntegrityError:
                        raw_fdd = RawFileDiffData.objects.get(
                            binary_hash=raw_fdd.binary_hash)

            if filediff_hashes:
                self._transition_hashes(cursor, 'diff_hash', filediff_hashes)

            if parent_filediff_hashes:
                self._transition_hashes(cursor, 'parent_diff_hash',
                                        parent_filediff_hashes)

            legacy_data_items.filter(pk__in=all_diff_hashes).delete()

            yield (len(batch), batch_total_diff_size,
                   batch_total_bytes_saved, filediff_hashes,
                   parent_filediff_hashes, all_diff_hashes)

    def _migrate_filediffs(self, queryset, count, batch_size):
        """Migrates old diff data from a FileDiff into a RawFileDiffData."""
        for batch in self._iter_batches(queryset, count, batch_size):
            batch_total_diff_size = 0
            batch_total_bytes_saved = 0

            for filediff in batch:
                diff_size = len(filediff.get_diff64_base64())
                parent_diff_size = len(filediff.get_parent_diff64_base64())

                batch_total_diff_size += diff_size + parent_diff_size

                diff_hash_is_new, parent_diff_hash_is_new = \
                    filediff._migrate_diff_data(recalculate_counts=False)

                if diff_size > 0 and not diff_hash_is_new:
                    batch_total_bytes_saved += diff_size

                if parent_diff_size > 0 and not parent_diff_hash_is_new:
                    batch_total_bytes_saved += parent_diff_size

            yield len(batch), batch_total_diff_size, batch_total_bytes_saved

    def _iter_batches(self, queryset, count, batch_size, object_limit=200):
        """Iterates through items in a queryset, yielding batches.

        This will gather up to a specified number of items from a
        queryset at a time, process them into batches of a specified
        size, and yield them.

        After each set of objects fetched from the database, garbage
        collection will be forced and stored queries reset, in order to
        reduce memory usage.
        """
        if count == 0:
            return

        batch = []

        for i in range(0, count, object_limit):
            # Every time we work on a batch,, we're re-querying the list of
            # objects. This result from the query is expected not to have any
            # previously-processed objects from a yielded batch. It may,
            # however, have objects we've previously seen that haven't been
            # yielded in a batch yet. That's why we're indexing from the
            # length of the batch to the object limit.
            for item in queryset[len(batch):object_limit].iterator():
                batch.append(item)

                if len(batch) == batch_size:
                    yield batch
                    batch = []

            # Do all we can to limit the memory usage by resetting any stored
            # queries (if DEBUG is True), and force garbage collection of
            # anything we may have from processing an object.
            reset_queries()
            gc.collect()

        if batch:
            yield batch

    def _transition_hashes(self, cursor, hash_field_name, diff_hashes):
        """Transitions FileDiff-associated hashes to RawFileDiffData.

        This queries all FileDiffs and RawFileDiffData entries referencing
        the given list of diff hashes, and updates the FileDiffs to point
        to those instead of the formerly-associated LegacyFileDiffDatas.
        """
        from reviewboard.diffviewer.models import RawFileDiffData

        legacy_hash_field_name = 'legacy_%s' % hash_field_name

        # Since this is a pretty complex operation, we're going to sanity-check
        # results on DEBUG setups, to help catch issues that might come up as
        # this code changes.
        if settings.DEBUG:
            old_filediff_info = dict(
                (filediff.pk, getattr(filediff, legacy_hash_field_name).pk)
                for filediff in self.filter(**{
                    legacy_hash_field_name + '__in': diff_hashes,
                })
            )
        else:
            old_filediff_info = None

        # If the database supports joins on updates, then we can craft
        # a query that will massively speed up the diff transition time.
        # Otherwise, we need to fall back on doing a select and then an
        # update per result.
        #
        # The queries are different between databases (yay standards), so
        # we can't be smart and do this in a generic way. We have to check
        # the database types.
        if connection.vendor == 'mysql':
            cursor.execute(
                'UPDATE %(filediff_table)s'
                '  INNER JOIN %(raw_fdd_table)s raw_fdd'
                '    ON raw_fdd.binary_hash = '
                '       %(filediff_table)s.%(hash_field_name)s_id'
                '  SET'
                '    raw_%(hash_field_name)s_id = raw_fdd.id,'
                '    %(hash_field_name)s_id = NULL'
                '  WHERE raw_fdd.binary_hash IN (%(diff_hashes)s)'
                % {
                    'filediff_table': self.model._meta.db_table,
                    'raw_fdd_table': RawFileDiffData._meta.db_table,
                    'hash_field_name': hash_field_name,
                    'diff_hashes': ','.join(
                        "'%s'" % diff_hash
                        for diff_hash in diff_hashes
                    ),
                })
        elif connection.vendor == 'postgresql':
            cursor.execute(
                'UPDATE %(filediff_table)s'
                '  SET'
                '    raw_%(hash_field_name)s_id = raw_fdd.id,'
                '    %(hash_field_name)s_id = NULL'
                '  FROM %(raw_fdd_table)s raw_fdd'
                '  WHERE'
                '    raw_fdd.binary_hash IN (%(diff_hashes)s) AND'
                '    raw_fdd.binary_hash = '
                '        %(hash_field_name)s_id'
                % {
                    'filediff_table': self.model._meta.db_table,
                    'raw_fdd_table': RawFileDiffData._meta.db_table,
                    'hash_field_name': hash_field_name,
                    'diff_hashes': ','.join(
                        "'%s'" % diff_hash
                        for diff_hash in diff_hashes
                    ),
                })
        else:
            raw_fdds = RawFileDiffData.objects.filter(
                binary_hash__in=diff_hashes).only('pk', 'binary_hash')

            for raw_fdd in raw_fdds:
                self.filter(**{
                    legacy_hash_field_name: raw_fdd.binary_hash
                }).update(**{
                    hash_field_name: raw_fdd.pk,
                    legacy_hash_field_name: None
                })

        if settings.DEBUG:
            new_filediff_info = dict(
                (filediff.pk, getattr(filediff, hash_field_name).binary_hash)
                for filediff in self.filter(pk__in=old_filediff_info.keys())
            )

            assert old_filediff_info == new_filediff_info


class RawFileDiffDataManager(models.Manager):
    """A custom manager for RawFileDiffData.

    This provides conveniences for creating an entry based on a
    LegacyFileDiffData object.
    """
    def process_diff_data(self, data):
        """Processes a diff, returning the resulting content and compression.

        If the content would benefit from being compressed, this will
        return the compressed content and the value for the compression
        flag. Otherwise, it will return the raw content.
        """
        compressed_data = bz2.compress(data, 9)

        if len(compressed_data) < len(data):
            return compressed_data, self.model.COMPRESSION_BZIP2
        else:
            return data, None

    def get_or_create_from_data(self, data):
        binary_hash = self._hash_hexdigest(data)
        processed_data, compression = self.process_diff_data(data)

        return self.get_or_create(
            binary_hash=binary_hash,
            defaults={
                'binary': processed_data,
                'compression': compression,
            })

    def create_from_legacy(self, legacy, save=True):
        processed_data, compression = self.process_diff_data(legacy.binary)

        raw_file_diff_data = self.model(binary_hash=legacy.binary_hash,
                                        binary=processed_data,
                                        compression=compression)
        raw_file_diff_data.extra_data = legacy.extra_data

        if save:
            raw_file_diff_data.save()

        return raw_file_diff_data

    def _hash_hexdigest(self, diff):
        hasher = hashlib.sha1()
        hasher.update(diff)
        return hasher.hexdigest()


class DiffSetManager(models.Manager):
    """A custom manager for DiffSet objects.

    This includes utilities for creating diffsets based on the data from form
    uploads, webapi requests, and upstream repositories.
    """

    # Extensions used for intelligent sorting of header files
    # before implementation files.
    HEADER_EXTENSIONS = ["h", "H", "hh", "hpp", "hxx", "h++"]
    IMPL_EXTENSIONS = ["c", "C", "cc", "cpp", "cxx", "c++", "m", "mm", "M"]

    def create_from_upload(self, repository, diff_file, parent_diff_file=None,
                           diffset_history=None, basedir=None, request=None,
                           base_commit_id=None, validate_only=False, **kwargs):
        """Create a DiffSet from a form upload.

        This parses a diff and optional parent diff covering one or more files,
        validates, and constructs :py:class:`DiffSets
        <reviewboard.diffviewer.models.DiffSet>` and :py:class:`FileDiffs
        <reviewboard.diffviewer.models.FileDiff>` representing the diff.

        This can optionally validate the diff without saving anything to the
        database. In this case, no value will be returned. Instead, callers
        should take any result as success.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the diff applies to.

            diff_file (django.core.files.uploadedfile.UploadedFile):
                The diff file uploaded in the form.

            parent_diff_file (django.core.files.uploadedfile.UploadedFile, optional):
                The parent diff file uploaded in the form.

            diffset_history (reviewboard.diffviewer.models.DiffSetHistory, optional):
                The history object to associate the DiffSet with. This is
                not required if using ``validate_only=True``.

            basedir (unicode, optional):
                The base directory to prepend to all file paths in the diff.

            request (django.http.HttpRequest, optional):
                The current HTTP request, if any. This will result in better
                logging.

            base_commit_id (unicode, optional):
                The ID of the commit that the diff is based upon. This is
                needed by some SCMs or hosting services to properly look up
                files, if the diffs represent blob IDs instead of commit IDs
                and the service doesn't support those lookups.

            validate_only (bool, optional):
                Whether to just validate and not save. If ``True``, then this
                won't populate the database at all and will return ``None``
                upon success. This defaults to ``False``.

        Returns:
            reviewboard.diffviewer.models.DiffSet:
            The resulting DiffSet stored in the database, if processing
            succeeded and ``validate_only=False``.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the main diff or parent diff.

            reviewboard.diffviewer.errors.DiffTooBigError:
                The diff file was too big to be uploaded, based on the
                configured maximum diff size in settings.

            reviewboard.diffviewer.errors.EmptyDiffError:
                The provided diff file did not contain any file changes.

            reviewboard.scmtools.core.FileNotFoundError:
                A file specified in the diff could not be found in the
                repository.

            reviewboard.scmtools.core.SCMError:
                There was an error talking to the repository when validating
                the existence of a file.

            reviewboard.scmtools.git.ShortSHA1Error:
                A SHA1 specified in the diff was in the short form, which
                could not be used to look up the file. This is applicable only
                to Git.
        """
        if 'save' in kwargs:
            warnings.warn('The save parameter to '
                          'DiffSet.objects.create_from_upload is deprecated. '
                          'Please set validate_only instead.',
                          DeprecationWarning)
            validate_only = not kwargs['save']

        siteconfig = SiteConfiguration.objects.get_current()
        max_diff_size = siteconfig.get('diffviewer_max_diff_size')

        if max_diff_size > 0:
            if diff_file.size > max_diff_size:
                raise DiffTooBigError(
                    _('The supplied diff file is too large'),
                    max_diff_size=max_diff_size)

            if parent_diff_file and parent_diff_file.size > max_diff_size:
                raise DiffTooBigError(
                    _('The supplied parent diff file is too large'),
                    max_diff_size=max_diff_size)

        if parent_diff_file:
            parent_diff_file_name = parent_diff_file.name
            parent_diff_file_contents = parent_diff_file.read()
        else:
            parent_diff_file_name = None
            parent_diff_file_contents = None

        return self.create_from_data(
            repository=repository,
            diff_file_name=diff_file.name,
            diff_file_contents=diff_file.read(),
            parent_diff_file_name=parent_diff_file_name,
            parent_diff_file_contents=parent_diff_file_contents,
            diffset_history=diffset_history,
            basedir=basedir,
            request=request,
            base_commit_id=base_commit_id,
            validate_only=validate_only)

    def create_from_data(self, repository, diff_file_name, diff_file_contents,
                         parent_diff_file_name=None,
                         parent_diff_file_contents=None,
                         diffset_history=None, basedir=None, request=None,
                         base_commit_id=None, check_existence=True,
                         validate_only=False, **kwargs):
        """Create a DiffSet from raw diff data.

        This parses a diff and optional parent diff covering one or more files,
        validates, and constructs :py:class:`DiffSets
        <reviewboard.diffviewer.models.DiffSet>` and :py:class:`FileDiffs
        <reviewboard.diffviewer.models.FileDiff>` representing the diff.

        This can optionally validate the diff without saving anything to the
        database. In this case, no value will be returned. Instead, callers
        should take any result as success.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the diff applies to.

            diff_file_name (unicode):
                The filename of the main diff file.

            diff_file_contents (bytes):
                The contents of the main diff file.

            parent_diff_file_name (unicode, optional):
                The filename of the parent diff, if one is provided.

            parent_diff_file_contents (bytes, optional):
                The contents of the parent diff, if one is provided.

            diffset_history (reviewboard.diffviewer.models.DiffSetHistory, optional):
                The history object to associate the DiffSet with. This is
                not required if using ``validate_only=True``.

            basedir (unicode, optional):
                The base directory to prepend to all file paths in the diff.

            request (django.http.HttpRequest, optional):
                The current HTTP request, if any. This will result in better
                logging.

            base_commit_id (unicode, optional):
                The ID of the commit that the diff is based upon. This is
                needed by some SCMs or hosting services to properly look up
                files, if the diffs represent blob IDs instead of commit IDs
                and the service doesn't support those lookups.

            check_existence (bool, optional):
                Whether to check for file existence as part of the validation
                process. This defaults to ``True``.

            validate_only (bool, optional):
                Whether to just validate and not save. If ``True``, then this
                won't populate the database at all and will return ``None``
                upon success. This defaults to ``False``.

        Returns:
            reviewboard.diffviewer.models.DiffSet:
            The resulting DiffSet stored in the database, if processing
            succeeded and ``validate_only=False``.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the main diff or parent diff.

            reviewboard.diffviewer.errors.EmptyDiffError:
                The provided diff file did not contain any file changes.

            reviewboard.scmtools.core.FileNotFoundError:
                A file specified in the diff could not be found in the
                repository.

            reviewboard.scmtools.core.SCMError:
                There was an error talking to the repository when validating
                the existence of a file.

            reviewboard.scmtools.git.ShortSHA1Error:
                A SHA1 specified in the diff was in the short form, which
                could not be used to look up the file. This is applicable only
                to Git.
        """
        from reviewboard.diffviewer.diffutils import convert_to_unicode
        from reviewboard.diffviewer.models import FileDiff

        if 'save' in kwargs:
            warnings.warn('The save parameter to '
                          'DiffSet.objects.create_from_data is deprecated. '
                          'Please set validate_only instead.',
                          DeprecationWarning)
            validate_only = not kwargs['save']

        tool = repository.get_scmtool()
        parser = tool.get_parser(diff_file_contents)

        files = list(self._process_files(
            parser,
            basedir,
            repository,
            base_commit_id,
            request,
            check_existence=check_existence and not parent_diff_file_contents))

        # Parse the diff
        if len(files) == 0:
            raise EmptyDiffError(_("The diff file is empty"))

        # Sort the files so that header files come before implementation.
        files.sort(cmp=self._compare_files, key=lambda f: f.origFile)

        # Parse the parent diff
        parent_files = {}

        # This is used only for tools like Mercurial that use atomic changeset
        # IDs to identify all file versions but not individual file version
        # IDs.
        parent_commit_id = None

        if parent_diff_file_contents:
            diff_filenames = set([f.origFile for f in files])

            parent_parser = tool.get_parser(parent_diff_file_contents)

            # If the user supplied a base diff, we need to parse it and
            # later apply each of the files that are in the main diff
            for f in self._process_files(parent_parser, basedir,
                                         repository, base_commit_id, request,
                                         check_existence=check_existence,
                                         limit_to=diff_filenames):
                parent_files[f.newFile] = f

            # This will return a non-None value only for tools that use
            # commit IDs to identify file versions as opposed to file revision
            # IDs.
            parent_commit_id = parent_parser.get_orig_commit_id()

        diffset = self.model(
            name=diff_file_name, revision=0,
            basedir=basedir,
            history=diffset_history,
            repository=repository,
            diffcompat=DiffCompatVersion.DEFAULT,
            base_commit_id=base_commit_id)

        if not validate_only:
            diffset.save()

        encoding_list = repository.get_encoding_list()
        filediffs = []

        for f in files:
            parent_file = None
            orig_rev = None
            parent_content = b''

            if f.origFile in parent_files:
                parent_file = parent_files[f.origFile]
                parent_content = parent_file.data
                orig_rev = parent_file.origInfo

            # If there is a parent file there is not necessarily an original
            # revision for the parent file in the case of a renamed file in
            # git.
            if not orig_rev:
                if parent_commit_id and f.origInfo != PRE_CREATION:
                    orig_rev = parent_commit_id
                else:
                    orig_rev = f.origInfo

            enc, orig_file = convert_to_unicode(f.origFile, encoding_list)
            enc, dest_file = convert_to_unicode(f.newFile, encoding_list)

            if f.deleted:
                status = FileDiff.DELETED
            elif f.moved:
                status = FileDiff.MOVED
            elif f.copied:
                status = FileDiff.COPIED
            else:
                status = FileDiff.MODIFIED

            filediff = FileDiff(
                diffset=diffset,
                source_file=parser.normalize_diff_filename(orig_file),
                dest_file=parser.normalize_diff_filename(dest_file),
                source_revision=smart_unicode(orig_rev),
                dest_detail=f.newInfo,
                binary=f.binary,
                status=status)

            if (parent_file and
                (parent_file.moved or parent_file.copied) and
                parent_file.insert_count == 0 and
                parent_file.delete_count == 0):
                filediff.extra_data = {'parent_moved': True}

            if not validate_only:
                # This state all requires making modifications to the database.
                # We only want to do this if we're saving.
                filediff.diff = f.data
                filediff.parent_diff = parent_content

                filediff.set_line_counts(raw_insert_count=f.insert_count,
                                         raw_delete_count=f.delete_count)

                filediffs.append(filediff)

        if validate_only:
            return None

        if filediffs:
            FileDiff.objects.bulk_create(filediffs)

        return diffset

    def _normalize_filename(self, filename, basedir):
        """Normalize a file name to be relative to the repository root."""
        if filename.startswith('/'):
            return filename

        return os.path.join(basedir, filename).replace('\\', '/')

    def _process_files(self, parser, basedir, repository, base_commit_id,
                       request, check_existence=False, limit_to=None):
        tool = repository.get_scmtool()

        for f in parser.parse():
            source_filename, source_revision = tool.parse_diff_revision(
                f.origFile,
                f.origInfo,
                moved=f.moved,
                copied=f.copied)

            dest_filename = self._normalize_filename(f.newFile, basedir)
            source_filename = self._normalize_filename(source_filename,
                                                       basedir)

            if limit_to is not None and dest_filename not in limit_to:
                # This file isn't actually needed for the diff, so save
                # ourselves a remote file existence check and some storage.
                continue

            # FIXME: this would be a good place to find permissions errors
            if (source_revision != PRE_CREATION and
                source_revision != UNKNOWN and
                not f.binary and
                not f.deleted and
                not f.moved and
                not f.copied and
                (check_existence and
                 not repository.get_file_exists(source_filename,
                                                source_revision,
                                                base_commit_id=base_commit_id,
                                                request=request))):
                raise FileNotFoundError(source_filename, source_revision,
                                        base_commit_id)

            f.origFile = source_filename
            f.origInfo = source_revision
            f.newFile = dest_filename

            yield f

    def _compare_files(self, filename1, filename2):
        """
        Compares two files, giving precedence to header files over source
        files. This allows the resulting list of files to be more
        intelligently sorted.
        """
        if filename1.find('.') != -1 and filename2.find('.') != -1:
            basename1, ext1 = filename1.rsplit('.', 1)
            basename2, ext2 = filename2.rsplit('.', 1)

            if basename1 == basename2:
                if (ext1 in self.HEADER_EXTENSIONS and
                        ext2 in self.IMPL_EXTENSIONS):
                    return -1
                elif (ext1 in self.IMPL_EXTENSIONS and
                      ext2 in self.HEADER_EXTENSIONS):
                    return 1

        return cmp(filename1, filename2)
