"""Managers for reviewboard.diffviewer.models."""

from __future__ import unicode_literals

import bz2
import gc
import hashlib
import warnings
from functools import partial

from django.conf import settings
from django.db import models, reset_queries, connection
from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.utils.six.moves import range

from reviewboard.diffviewer.commit_utils import get_file_exists_in_history
from reviewboard.diffviewer.differ import DiffCompatVersion
from reviewboard.diffviewer.diffutils import check_diff_size
from reviewboard.diffviewer.filediff_creator import create_filediffs


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
        """Return or create a new stored entry for diff data.

        Args:
            data (bytes):
                The diff data to store or return an entry for.

        Returns:
            reviewboard.diffviewer.models.raw_file_diff_data.RawFileDiffData:
            The entry for the diff data.

        Raises:
            TypeError:
                The data passed in was not a bytes string.
        """
        if not isinstance(data, bytes):
            raise TypeError(
                'RawFileDiffData.objects.get_or_create_data expects a '
                'bytes value, not %s'
                % type(data))

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


class BaseDiffManager(models.Manager):
    """A base manager class for creating models out of uploaded diffs"""

    def create_from_data(self, *args, **kwargs):
        """Create a model instance from data.

        Subclasses must implement this method.

        See :py:meth:`create_from_upload` for the fields that will be passed to
        this method.

        Returns:
            django.db.models.Model:
            The model instance.
        """
        raise NotImplementedError

    def create_from_upload(self, repository, diff_file, parent_diff_file=None,
                           request=None, validate_only=False, **kwargs):
        """Create a model instance from a form upload.

        This parses a diff and optional parent diff covering one or more files,
        validates, and constructs either:

        * a :py:class:`~reviewboard.diffviewer.models.diffset.DiffSet` or
        * a :py:class:`~reviewboard.diffviewer.models.diffcommit.DiffCommit`

        and the child :py:class:`FileDiffs
        <reviewboard.diffviewer.models.filediff.FileDiff>` representing the
        diff.

        This can optionally validate the diff without saving anything to the
        database. In this case, no value will be returned. Instead, callers
        should take any result as success.

        This function also accepts a number of keyword arguments when creating
        a :py:class:`~reviewboard.diffviewer.model.DiffCommit`. In that case,
        the following fields are required (except for the committer fields when
        the underlying SCM does not distinguish betwen author and committer):

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the diff applies to.

            diff_file (django.core.files.uploadedfile.UploadedFile):
                The diff file uploaded in the form.

            parent_diff_file (django.core.files.uploadedfile.UploadedFile,
                              optional):
                The parent diff file uploaded in the form.

            request (django.http.HttpRequest, optional):
                The current HTTP request, if any. This will result in better
                logging.

            validate_only (bool, optional):
                Whether to just validate and not save. If ``True``, then this
                won't populate the database at all and will return ``None``
                upon success. This defaults to ``False``.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`create_from_data`.

                See :py:meth:`~DiffSetManager.create_from_data` and
                :py:meth:`DiffCommitManager.create_from_data` for acceptable
                keyword arguments.

        Returns:
            reviewboard.diffviewer.models.diffset.DiffSet:
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
        check_diff_size(diff_file, parent_diff_file)

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
            request=request,
            validate_only=validate_only,
            **kwargs)


class DiffCommitManager(BaseDiffManager):
    """A custom manager for DiffCommit objects.

    This includes utilities for creating diffsets based on the data from form
    uploads, webapi requests, and upstream repositories.
    """

    def by_diffset_ids(self, diffset_ids):
        """Return the commits grouped by DiffSet IDs.

        Args:
            diffset_ids (list of int):
                The primary keys of the DiffSets to retrieve commits for.

        Returns:
            dict:
            A mapping of :py:class:`~reviewboard.diffviewer.models.diffset.
            DiffSet` primary keys to lists of
            :py:class:`DiffCommits <reviewboard.diffviewer.models.diffcommit.
            DiffCommit>`.
        """
        commits_by_diffset_id = {
            pk: []
            for pk in diffset_ids
        }

        for commit in self.filter(diffset_id__in=diffset_ids):
            commits_by_diffset_id[commit.diffset_id].append(commit)

        return commits_by_diffset_id

    def create_from_data(self,
                         repository,
                         diff_file_name,
                         diff_file_contents,
                         parent_diff_file_name,
                         parent_diff_file_contents,
                         diffset,
                         commit_id,
                         parent_id,
                         commit_message,
                         author_name,
                         author_email,
                         author_date,
                         validation_info=None,
                         request=None,
                         committer_name=None,
                         committer_email=None,
                         committer_date=None,
                         base_commit_id=None,
                         check_existence=True,
                         validate_only=False):
        """Create a DiffCommit from raw diff data.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the diff was posted against.

            diff_file_name (unicode):
                The name of the diff file.

            diff_file_contents (bytes):
                The contents of the diff file.

            parent_diff_file_name (unicode):
                The name of the parent diff file.

            parent_diff_file_contents (bytes):
                The contents of the parent diff file.

            diffset (reviewboard.diffviewer.models.diffset.DiffSet):
                The DiffSet to attach the created DiffCommit to.

            commit_id (unicode):
                The unique identifier of the commit.

            parent_id (unicode):
                The unique identifier of the parent commit.

            commit_message (unicode):
                The commit message.

            author_name (unicode):
                The author's name.

            author_email (unicode):
                The author's e-mail address.

            author_date (datetime.datetime):
                The date and time that the commit was authored.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            validation_info (dict, optional):
                A dictionary of parsed validation information from the
                :py:class:`~reviewboard.webapi.resources.validate_diffcommit.
                ValidateDiffCommitResource`.

            committer_name (unicode, optional):
                The committer's name.

            committer_email (unicode, optional)
                The committer's e-mail address.

            committer_date (datetime.datetime, optional):
                The date and time that the commit was committed.

            base_commit_id (unicode, optional):
                The ID of the commit that the diff is based upon. This is
                needed by some SCMs or hosting services to properly look up
                files, if the diffs represent blob IDs instead of commit IDs
                and the service doesn't support those lookups.

            check_existence (bool, optional):
                Whether or not existence checks should be performed against
                the upstream repository.

            validate_only (bool, optional):
                Whether to just validate and not save. If ``True``, then this
                won't populate the database at all and will return ``None``
                upon success. This defaults to ``False``.

        Returns:
            reviewboard.diffviewer.models.diffcommit.DiffCommit:
            The created model instance.
        """
        diffcommit = self.model(
            filename=diff_file_name,
            diffset=diffset,
            commit_id=commit_id,
            parent_id=parent_id,
            author_name=author_name,
            author_email=author_email,
            author_date=author_date,
            commit_message=commit_message,
            committer_name=committer_name,
            committer_email=committer_email,
            committer_date=committer_date)

        if not validate_only:
            diffcommit.save()

        get_file_exists = partial(get_file_exists_in_history,
                                  validation_info or {},
                                  repository,
                                  parent_id)

        create_filediffs(
            get_file_exists=get_file_exists,
            diff_file_contents=diff_file_contents,
            parent_diff_file_contents=parent_diff_file_contents,
            repository=repository,
            request=request,
            basedir='',
            base_commit_id=base_commit_id,
            diffset=diffset,
            diffcommit=diffcommit,
            validate_only=validate_only,
            check_existence=check_existence)

        if validate_only:
            return None

        return diffcommit


class DiffSetManager(BaseDiffManager):
    """A custom manager for DiffSet objects.

    This includes utilities for creating diffsets based on the data from form
    uploads, webapi requests, and upstream repositories.
    """

    def create_from_data(self,
                         repository,
                         diff_file_name,
                         diff_file_contents,
                         parent_diff_file_name=None,
                         parent_diff_file_contents=None,
                         diffset_history=None,
                         basedir=None,
                         request=None,
                         base_commit_id=None,
                         check_existence=True,
                         validate_only=False,
                         **kwargs):
        """Create a DiffSet from raw diff data.

        This parses a diff and optional parent diff covering one or more files,
        validates, and constructs :py:class:`DiffSets
        <reviewboard.diffviewer.models.diffset.DiffSet>` and
        :py:class:`FileDiffs <reviewboard.diffviewer.models.filediff.FileDiff>`
        representing the diff.

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

            diffset_history (reviewboard.diffviewer.models.diffset_history.
                             DiffSetHistory, optional):
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

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            reviewboard.diffviewer.models.diffset.DiffSet:
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
        diffset = self.model(
            name=diff_file_name,
            revision=0,
            basedir=basedir,
            history=diffset_history,
            repository=repository,
            diffcompat=DiffCompatVersion.DEFAULT,
            base_commit_id=base_commit_id)

        if not validate_only:
            diffset.save()

        create_filediffs(
            get_file_exists=repository.get_file_exists,
            diff_file_contents=diff_file_contents,
            parent_diff_file_contents=parent_diff_file_contents,
            repository=repository,
            request=request,
            basedir=basedir,
            base_commit_id=base_commit_id,
            diffset=diffset,
            check_existence=check_existence,
            validate_only=validate_only
        )

        if validate_only:
            return None

        return diffset

    def create_empty(self, repository, diffset_history=None, **kwargs):
        """Create a DiffSet with no attached FileDiffs.

        An empty DiffSet must be created before
        :py:class:`DiffCommits <reviewboard.diffviewer.models.diffcommit.
        DiffCommit>` can be added to it. When the DiffCommits are created,
        the :py:class:`FileDiffs <reviewboard.diffviewer.models.filediff.
        FileDiff>` will be attached to the DiffSet.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to create the DiffSet in.

            diffset_history (reviewboard.diffviewer.models.diffset_history.
                             DiffSetHistory, optional):
                An optional DiffSetHistory instance to attach the DiffSet to.

            **kwargs (dict):
                Additional keyword arguments to pass to :py:meth:`create`.

        Returns:
            reviewboard.diffviewer.models.diffset.DiffSet:
            The created DiffSet.
        """
        kwargs.setdefault('revision', 0)
        return super(DiffSetManager, self).create(
            name='diff',
            history=diffset_history,
            repository=repository,
            diffcompat=DiffCompatVersion.DEFAULT,
            **kwargs)
