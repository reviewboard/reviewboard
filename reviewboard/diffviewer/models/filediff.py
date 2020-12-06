"""FileDiff model definition."""

from __future__ import unicode_literals

import logging
from itertools import chain

from django.db import models
from django.db.models import Q
from django.utils import six
from django.utils.six.moves import range
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import Base64Field, JSONField

from reviewboard.diffviewer.managers import FileDiffManager
from reviewboard.diffviewer.models.diffcommit import DiffCommit
from reviewboard.diffviewer.models.legacy_file_diff_data import \
    LegacyFileDiffData
from reviewboard.diffviewer.models.raw_file_diff_data import RawFileDiffData
from reviewboard.scmtools.core import PRE_CREATION


@python_2_unicode_compatible
class FileDiff(models.Model):
    """A diff of a single file.

    This contains the patch and information needed to produce original and
    patched versions of a single file in a repository.
    """

    _ANCESTORS_KEY = '__ancestors'

    COPIED = 'C'
    DELETED = 'D'
    MODIFIED = 'M'
    MOVED = 'V'

    STATUSES = (
        (COPIED, _('Copied')),
        (DELETED, _('Deleted')),
        (MODIFIED, _('Modified')),
        (MOVED, _('Moved')),
    )

    _IS_PARENT_EMPTY_KEY = '__parent_diff_empty'

    diffset = models.ForeignKey('DiffSet',
                                related_name='files',
                                verbose_name=_('diff set'))

    commit = models.ForeignKey(DiffCommit,
                               related_name='files',
                               verbose_name=_('diff commit'),
                               null=True)

    source_file = models.CharField(_('source file'), max_length=1024)
    dest_file = models.CharField(_('destination file'), max_length=1024)
    source_revision = models.CharField(_('source file revision'),
                                       max_length=512)
    dest_detail = models.CharField(_('destination file details'),
                                   max_length=512)
    binary = models.BooleanField(_('binary file'), default=False)
    status = models.CharField(_('status'), max_length=1, choices=STATUSES)

    diff64 = Base64Field(
        _('diff'),
        db_column='diff_base64',
        blank=True)
    legacy_diff_hash = models.ForeignKey(
        LegacyFileDiffData,
        db_column='diff_hash_id',
        related_name='filediffs',
        null=True,
        blank=True)
    diff_hash = models.ForeignKey(
        RawFileDiffData,
        db_column='raw_diff_hash_id',
        related_name='filediffs',
        null=True,
        blank=True)

    parent_diff64 = Base64Field(
        _('parent diff'),
        db_column='parent_diff_base64',
        blank=True)
    legacy_parent_diff_hash = models.ForeignKey(
        LegacyFileDiffData,
        db_column='parent_diff_hash_id',
        related_name='parent_filediffs',
        null=True,
        blank=True)
    parent_diff_hash = models.ForeignKey(
        RawFileDiffData,
        db_column='raw_parent_diff_hash_id',
        related_name='parent_filediffs',
        null=True,
        blank=True)

    extra_data = JSONField(null=True)

    objects = FileDiffManager()

    @property
    def source_file_display(self):
        """The displayed filename for the source/original file.

        This may be different than :py:attr:`source_file`, as the associated
        :py:class:`~reviewboard.scmtools.core.SCMTool` may normalize it for
        display.

        Type:
            unicode
        """
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(
            self.source_file,
            extra_data=self.extra_data)

    @property
    def dest_file_display(self):
        """The displayed filename for the destination/modified file.

        This may be different than :py:attr:`dest_file`, as the associated
        :py:class:`~reviewboard.scmtools.core.SCMTool` may normalize it for
        display.

        Type:
            unicode
        """
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(
            self.dest_file,
            extra_data=self.extra_data)

    @property
    def deleted(self):
        return self.status == self.DELETED

    @property
    def copied(self):
        return self.status == self.COPIED

    @property
    def moved(self):
        return self.status == self.MOVED

    @property
    def modified(self):
        """Whether this file is a modification to an existing file."""
        return self.status == self.MODIFIED

    @property
    def is_new(self):
        return self.source_revision == PRE_CREATION

    @property
    def status_string(self):
        """The FileDiff's status as a human-readable string."""
        if self.status == FileDiff.COPIED:
            return 'copied'
        elif self.status == FileDiff.DELETED:
            return 'deleted'
        elif self.status == FileDiff.MODIFIED:
            return 'modified'
        elif self.status == FileDiff.MOVED:
            return 'moved'
        else:
            logging.error('Unknown FileDiff status %r for FileDiff %s',
                          self.status, self.pk)
            return 'unknown'

    def _get_diff(self):
        if self._needs_diff_migration():
            self._migrate_diff_data()

        return self.diff_hash.content

    def _set_diff(self, diff):
        # Add hash to table if it doesn't exist, and set diff_hash to this.
        self.diff_hash, is_new = \
            RawFileDiffData.objects.get_or_create_from_data(diff)
        self.diff64 = b''

        return is_new

    diff = property(_get_diff, _set_diff)

    @property
    def is_diff_empty(self):
        """Whether or not the diff is empty."""
        line_counts = self.get_line_counts()

        return (line_counts['raw_insert_count'] == 0 and
                line_counts['raw_delete_count'] == 0)


    def _get_parent_diff(self):
        if self._needs_parent_diff_migration():
            self._migrate_diff_data()

        if self.parent_diff_hash:
            return self.parent_diff_hash.content
        else:
            return None

    def _set_parent_diff(self, parent_diff):
        if not parent_diff:
            return False

        # Add hash to table if it doesn't exist, and set diff_hash to this.
        self.parent_diff_hash, is_new = \
            RawFileDiffData.objects.get_or_create_from_data(parent_diff)
        self.parent_diff64 = b''

        return is_new

    parent_diff = property(_get_parent_diff, _set_parent_diff)

    def is_parent_diff_empty(self, cache_only=False):
        """Return whether or not the parent diff is empty.

        Args:
            cache_only (bool, optional):
                Whether or not to only use cached results.

        Returns:
            bool:
            Whether or not the parent diff is empty. This is true if either
            there is no parent diff or if the parent diff has no insertions and
            no deletions.
        """
        assert self.parent_diff_hash_id is not None, 'No parent diff.'

        if cache_only:
            return self.extra_data.get(self._IS_PARENT_EMPTY_KEY, False)

        if (not self.extra_data or
            self._IS_PARENT_EMPTY_KEY not in self.extra_data):
            parent_diff_hash = self.parent_diff_hash

            if (parent_diff_hash.insert_count is None or
                parent_diff_hash.delete_count is None):
                tool = self.get_repository().get_scmtool()
                parent_diff_hash.recalculate_line_counts(tool)

            self.extra_data[self._IS_PARENT_EMPTY_KEY] = (
                parent_diff_hash.insert_count == 0 and
                parent_diff_hash.delete_count == 0)

            self.save(update_fields=('extra_data',))

        return self.extra_data[self._IS_PARENT_EMPTY_KEY]

    @property
    def orig_sha1(self):
        """The computed SHA1 hash of the original file.

        This may be ``None``, in which case it will be populated when the
        diff is next viewed.
        """
        return self.extra_data.get('orig_sha1')

    @property
    def patched_sha1(self):
        """The computed SHA1 hash of the patched file.

        This may be ``None``, in which case it will be populated when the
        diff is next viewed.
        """
        return self.extra_data.get('patched_sha1')

    @property
    def orig_sha256(self):
        """The computed SHA256 hash of the original file.

        This may be ``None``, in which case it will be populated when the
        diff is next viewed.

        Version Added:
            4.0
        """
        return self.extra_data.get('orig_sha256')

    @property
    def patched_sha256(self):
        """The computed SHA256 hash of the patched file.

        This may be ``None``, in which case it will be populated when the
        diff is next viewed.

        Version Added:
            4.0
        """
        return self.extra_data.get('patched_sha256')

    @property
    def encoding(self):
        """The encoding of the source and patched file.

        This will check the ``encoding`` key in :py:attr:`extra_data`.
        If not available, then this will be ``None``.

        Version Added:
            4.0
        """
        return self.extra_data.get('encoding')

    def get_line_counts(self):
        """Return the stored line counts for the diff.

        This will return all the types of line counts that can be set.

        Returns:
            dict:
            A dictionary with the following keys:

            * ``raw_insert_count``
            * ``raw_delete_count``
            * ``insert_count``
            * ``delete_count``
            * ``replace_count``
            * ``equal_count``
            * ``total_line_count``

            These are not all guaranteed to have values set, and may instead be
            ``None``. Only ``raw_insert_count``, ``raw_delete_count``
            ``insert_count``, and ``delete_count`` are guaranteed to have
            values set.

            If there isn't a processed number of inserts or deletes stored,
            then ``insert_count`` and ``delete_count`` will be equal to the raw
            versions.
        """
        if ('raw_insert_count' not in self.extra_data or
            'raw_delete_count' not in self.extra_data):
            if not self.diff_hash:
                self._migrate_diff_data()

            if self.diff_hash.insert_count is None:
                self._recalculate_line_counts(self.diff_hash)

            self.extra_data.update({
                'raw_insert_count': self.diff_hash.insert_count,
                'raw_delete_count': self.diff_hash.delete_count,
            })

            if self.pk:
                self.save(update_fields=['extra_data'])

        raw_insert_count = self.extra_data['raw_insert_count']
        raw_delete_count = self.extra_data['raw_delete_count']

        return {
            'raw_insert_count': raw_insert_count,
            'raw_delete_count': raw_delete_count,
            'insert_count': self.extra_data.get('insert_count',
                                                raw_insert_count),
            'delete_count': self.extra_data.get('delete_count',
                                                raw_delete_count),
            'replace_count': self.extra_data.get('replace_count'),
            'equal_count': self.extra_data.get('equal_count'),
            'total_line_count': self.extra_data.get('total_line_count'),
        }

    def set_line_counts(self, raw_insert_count=None, raw_delete_count=None,
                        insert_count=None, delete_count=None,
                        replace_count=None, equal_count=None,
                        total_line_count=None):
        """Set the line counts on the FileDiff.

        There are many types of useful line counts that can be set.

        Args:
            raw_insert_count (int, optional):
                The insert count on the original patch.

                This will be set on the
                :py:class:`reviewboard.diffviewer.models.raw_file_diff_data.RawFileDiffData`
                as well.

            raw_delete_count (int, optional):
                The delete count in the original patch.

                This will be set on the
                :py:class:`reviewboard.diffviewer.models.raw_file_diff_data.RawFileDiffData`
                as well.

            insert_count (int, optional):
                The number of lines that were inserted in the diff.

            delete_count (int, optional):
                The number of lines that were deleted in the diff.

            replace_count (int, optional):
                The number of lines that were replaced in the diff.

            equal_count (int, optional):
                The number of lines that were identical in the diff.

            total_line_count (int, optional):
                The total line count.
        """
        updated = False

        if not self.diff_hash_id:
            # This really shouldn't happen, but if it does, we should handle
            # it gracefully.
            logging.warning('Attempting to call set_line_counts on '
                            'un-migrated FileDiff %s' % self.pk)
            self._migrate_diff_data(False)

        if (insert_count is not None and
            raw_insert_count is not None and
            self.diff_hash.insert_count is not None and
            self.diff_hash.insert_count != insert_count):
            # Allow overriding, but warn. This really shouldn't be called.
            logging.warning('Attempting to override insert count on '
                            'RawFileDiffData %s from %s to %s (FileDiff %s)'
                            % (self.diff_hash.pk,
                               self.diff_hash.insert_count,
                               insert_count,
                               self.pk))

        if (delete_count is not None and
            raw_delete_count is not None and
            self.diff_hash.delete_count is not None and
            self.diff_hash.delete_count != delete_count):
            # Allow overriding, but warn. This really shouldn't be called.
            logging.warning('Attempting to override delete count on '
                            'RawFileDiffData %s from %s to %s (FileDiff %s)'
                            % (self.diff_hash.pk,
                               self.diff_hash.delete_count,
                               delete_count,
                               self.pk))

        if raw_insert_count is not None or raw_delete_count is not None:
            # New raw counts have been provided. These apply to the actual
            # diff file itself, and will be common across all diffs sharing
            # the diff_hash instance. Set it there.
            if raw_insert_count is not None:
                self.diff_hash.insert_count = raw_insert_count
                self.extra_data['raw_insert_count'] = raw_insert_count
                updated = True

            if raw_delete_count is not None:
                self.diff_hash.delete_count = raw_delete_count
                self.extra_data['raw_delete_count'] = raw_delete_count
                updated = True

            self.diff_hash.save()

        for key, cur_value in (('insert_count', insert_count),
                               ('delete_count', delete_count),
                               ('replace_count', replace_count),
                               ('equal_count', equal_count),
                               ('total_line_count', total_line_count)):
            if cur_value is not None and cur_value != self.extra_data.get(key):
                self.extra_data[key] = cur_value
                updated = True

        if updated and self.pk:
            self.save(update_fields=['extra_data'])

    def get_ancestors(self, minimal, filediffs=None, update=True):
        """Return the ancestors of this FileDiff.

        This will update the ancestors of this :py:class:`FileDiff` and all its
        ancestors if they are not already cached.

        Args:
            minimal (bool):
                Whether or not the minimal set of ancestors are returned.

                The minimal set of ancestors does not include ancestors where
                the file was deleted. In other words, if a file is deleted and
                then re-created, the deletion will not appear in the re-created
                file's ancestor list.

            filediffs (iterable of FileDiff, optional):
                An optional list of FileDiffs to check for ancestors so that a
                query does not have to be performed.

            update (bool, optional):
                Whether or not to cache the results in the database.

                If ``True`` and the results have not already been cached, this
                FileDiff and its ancestors will all be updated.

        Returns:
            list of FileDiff:
            The ancestor :py:class:`FileDiffs <FileDiff>`, in application
            order.
        """
        if self.commit_id is None:
            return []

        if (self.extra_data is None or
            self._ANCESTORS_KEY not in self.extra_data):
            if filediffs is None:
                filediffs = list(FileDiff.objects.filter(
                    diffset_id=self.diffset_id))

            compliment_ids, minimal_ids = self._compute_ancestors(filediffs,
                                                                  update)
        else:
            compliment_ids, minimal_ids = self.extra_data[self._ANCESTORS_KEY]

            if filediffs is None:
                filediffs = FileDiff.objects.filter(
                    pk__in=compliment_ids + minimal_ids)

        by_id = {
            filediff.pk: filediff
            for filediff in filediffs
        }

        if minimal:
            ids = minimal_ids
        else:
            ids = chain(compliment_ids, minimal_ids)

        return [by_id[pk] for pk in ids]

    def get_repository(self):
        """Return the repository this diff applies to.

        Version Added:
            4.0

        Returns:
            reviewboard.scmtools.models.Repository:
            The repository used for any operations for this FileDiff.
        """
        return self.diffset.repository

    def get_base_filediff(self, base_commit, ancestors=None):
        """Return the base FileDiff within a commit range.

        This looks through the FileDiff's ancestors, looking for the most
        recent one that equals or precedes ``base_commit``.

        Args:
            base_commit (reviewboard.diffviewer.models.diffcommit.DiffCommit):
                The newest commit that the resulting base FileDiff can be
                associated with.

            ancestors (list of FileDiff, optional):
                A pre-fetched list of FileDiff ancestors. If not provided, a
                list will be fetched.

        Returns:
            FileDiff:
            The base FileDiff, if one could be found. ``None`` will be
            returned if no base could be found.
        """
        if base_commit and self.commit_id:
            if ancestors is None:
                ancestors = self.get_ancestors(minimal=False) or []

            for ancestor in reversed(ancestors):
                if ancestor.commit_id <= base_commit.pk:
                    return ancestor

        return None

    def _compute_ancestors(self, filediffs, update):
        """Compute the ancestors of this FileDiff.

        Args:
            filediffs (iterable of FileDiff):
                The list of FileDiffs to check for ancestors.

            update (bool):
                Whether or not to cache the results.

        Returns:
            list of FileDiff:
            The ancestor FileDiffs in application order.
        """
        by_dest_file = {}
        by_id = {}

        for filediff in filediffs:
            by_detail = by_dest_file.setdefault(filediff.dest_file, {})
            by_commit = by_detail.setdefault(filediff.dest_detail, {})
            by_commit[filediff.commit_id] = filediff

            by_id[filediff.pk] = filediff

        current = self
        ancestor_ids = []
        should_update = {self.pk}

        while True:
            # If the ancestors have already been computed for the direct
            # ancestor, we can stop there and re-use those results.
            try:
                rest = current.extra_data[self._ANCESTORS_KEY]
            except (KeyError, TypeError):
                should_update.add(current.pk)
            else:
                # We reverse below, so we have to add these in reverse order.
                ancestor_ids.extend(chain(reversed(rest[1]),
                                          reversed(rest[0])))
                break

            if current.is_new:
                # If the FileDiff is new there may have been a previous
                # FileDiff with the same name that was deleted.
                try:
                    by_detail = by_dest_file[current.source_file]
                    prev_set = (
                        filediff
                        for by_commit in six.itervalues(by_detail)
                        for filediff in six.itervalues(by_commit)
                        if filediff.deleted
                    )
                except KeyError:
                    break
            else:
                # Otherwise we need to walk the graph to find the previous
                # FileDiff.
                try:
                    by_detail = by_dest_file[current.source_file]
                    prev_set = six.itervalues(
                        by_detail[current.source_revision])
                except KeyError:
                    # There is no previous FileDiff created by the commit series.
                    break

            # The only information we know is the previous revision and name,
            # of which there might be multiple matches. We need to find the
            # most recent FileDiff that matches that criteria that belongs to a
            # commit that comes before the current FileDiff's commit in
            # application order.
            try:
                prev = max(
                    (
                        filediff
                        for filediff in prev_set
                        if filediff.commit_id < current.commit_id
                    ),
                    key=lambda filediff: filediff.commit_id)
            except ValueError:
                # max() raises ValueError if it is given an empty iterable.
                # This means there is no previous FileDiff created by the
                # commit series.
                break

            ancestor_ids.append(prev.pk)
            current = prev

        # We computed the list of ancestors in reverse order (i.e., most recent
        # to least recent) above.
        ancestor_ids.reverse()

        compliment_ids, minimal_ids = self._split_ancestors(by_id,
                                                            ancestor_ids)

        if update:
            for i, pk in enumerate(ancestor_ids):
                if pk in should_update:
                    filediff = by_id[pk]

                    if filediff.extra_data is None:
                        filediff.extra_data = {}

                    # We need to split the history at the point of the last
                    # deletion. That way we will have the minimal set of
                    # ancestors, which we can use to compute the diff for this
                    # FileDiff, and the maximal set of ancestors, which we can
                    # use to compute cumulative diffs.
                    filediff.extra_data[self._ANCESTORS_KEY] = \
                        list(self._split_ancestors(by_id, ancestor_ids[:i]))
                    filediff.save(update_fields=('extra_data',))

            self.extra_data[self._ANCESTORS_KEY] = [compliment_ids,
                                                    minimal_ids]
            self.save(update_fields=('extra_data',))

        return compliment_ids, minimal_ids

    def _split_ancestors(self, by_id, ancestor_ids):
        """Split the ancestor IDs into pre-delete and post-delete sets.

        Args:
            by_id (dict):
                A mapping of primary keys to :py:class:`FileDiffs
                <reviewboard.diffviewer.models.filediff.FileDiff>`.

            ancestor_ids (list of int):
                The ancestors to split.

        Returns:
            tuple:
            A 2-tuple of:

            * The compliment of the minimal ancestors (py:class:`list` of
              :py:class:`int`).
            * The list of minimal ancestors (py:class:`list` of
              :py:class:`int`).
        """
        i = 0

        # We traverse the list backwards to find the last deleted FileDiff.
        # Everything after that is in the set of minimal ancestors.
        for i in range(len(ancestor_ids) - 1, -1, -1):
            filediff = by_id[ancestor_ids[i]]

            if filediff.deleted:
                i += 1
                break

        return ancestor_ids[:i], ancestor_ids[i:]

    def _needs_diff_migration(self):
        return self.diff_hash_id is None

    def _needs_parent_diff_migration(self):
        return (self.parent_diff_hash_id is None and
                (self.parent_diff64 or self.legacy_parent_diff_hash_id))

    def _migrate_diff_data(self, recalculate_counts=True):
        """Migrates diff data associated with a FileDiff to RawFileDiffData.

        If the diff data is stored directly on the FileDiff, it will be
        removed and stored on a RawFileDiffData instead.

        If the diff data is stored on an associated LegacyFileDiffData,
        that will be converted into a RawFileDiffData. The LegacyFileDiffData
        will then be removed, if nothing else is using it.

        Args:
            recalculate_line_counts (bool, optional):
                Whether or not line counts should be recalculated during the
                migration.
        """
        needs_save = False
        diff_hash_is_new = False
        parent_diff_hash_is_new = False
        fix_refs = False
        legacy_pks = []
        needs_diff_migration = self._needs_diff_migration()
        needs_parent_diff_migration = self._needs_parent_diff_migration()

        if needs_diff_migration:
            recalculate_diff_counts = recalculate_counts
            needs_save = True

            if self.legacy_diff_hash_id:
                logging.debug('Migrating LegacyFileDiffData %s to '
                              'RawFileDiffData for diff in FileDiff %s',
                              self.legacy_diff_hash_id, self.pk)

                try:
                    legacy_data = self.legacy_diff_hash.binary
                except LegacyFileDiffData.DoesNotExist:
                    # Another process migrated this before we could.
                    # We'll need to fix the references.
                    fix_refs = True
                    recalculate_diff_counts = False
                else:
                    diff_hash_is_new = self._set_diff(legacy_data)
                    legacy_pks.append(self.legacy_diff_hash_id)
                    self.legacy_diff_hash = None
            else:
                logging.debug('Migrating FileDiff %s diff data to '
                              'RawFileDiffData',
                              self.pk)

                diff_hash_is_new = self._set_diff(self.diff64)

            if recalculate_diff_counts:
                self._recalculate_line_counts(self.diff_hash)

        if needs_parent_diff_migration:
            recalculate_parent_diff_counts = recalculate_counts
            needs_save = True

            if self.legacy_parent_diff_hash_id:
                logging.debug('Migrating LegacyFileDiffData %s to '
                              'RawFileDiffData for parent diff in FileDiff %s',
                              self.legacy_parent_diff_hash_id, self.pk)

                try:
                    legacy_parent_data = self.legacy_parent_diff_hash.binary
                except LegacyFileDiffData.DoesNotExist:
                    # Another process migrated this before we could.
                    # We'll need to fix the references.
                    fix_refs = True
                    recalculate_parent_diff_counts = False
                else:
                    parent_diff_hash_is_new = \
                        self._set_parent_diff(legacy_parent_data)
                    legacy_pks.append(self.legacy_parent_diff_hash_id)
                    self.legacy_parent_diff_hash = None
            else:
                logging.debug('Migrating FileDiff %s parent diff data to '
                              'RawFileDiffData',
                              self.pk)

                parent_diff_hash_is_new = \
                    self._set_parent_diff(self.parent_diff64)

            if recalculate_parent_diff_counts:
                self._recalculate_line_counts(self.parent_diff_hash)

        if fix_refs:
            # Another server/process/thread got to this before we could.
            # We need to pull the latest refs and make sure they're set here.
            diff_hash, parent_diff_hash = (
                FileDiff.objects.filter(pk=self.pk)
                .values_list('diff_hash_id', 'parent_diff_hash_id')[0]
            )

            if needs_diff_migration:
                if diff_hash:
                    self.diff_hash_id = diff_hash
                    self.legacy_diff_hash = None
                    self.diff64 = ''
                else:
                    logging.error('Unable to migrate diff for FileDiff %s: '
                                  'LegacyFileDiffData "%s" is missing, and '
                                  'database entry does not have a new '
                                  'diff_hash! Data may be missing.',
                                  self.pk, self.legacy_diff_hash_id)

            if needs_parent_diff_migration:
                if parent_diff_hash:
                    self.parent_diff_hash_id = parent_diff_hash
                    self.legacy_parent_diff_hash = None
                    self.parent_diff64 = ''
                else:
                    logging.error('Unable to migrate parent diff for '
                                  'FileDiff %s: LegacyFileDiffData "%s" is '
                                  'missing, and database entry does not have '
                                  'a new parent_diff_hash! Data may be '
                                  'missing.',
                                  self.pk, self.legacy_parent_diff_hash_id)

        if needs_save:
            if self.pk:
                self.save(update_fields=[
                    'diff64', 'parent_diff64', 'diff_hash', 'parent_diff_hash',
                    'legacy_diff_hash', 'legacy_parent_diff_hash',
                ])
            else:
                self.save()

        if legacy_pks:
            # Delete any LegacyFileDiffData objects no longer associated
            # with any FileDiffs.
            LegacyFileDiffData.objects \
                .filter(pk__in=legacy_pks) \
                .exclude(Q(filediffs__pk__gt=0) |
                         Q(parent_filediffs__pk__gt=0)) \
                .delete()

        return diff_hash_is_new, parent_diff_hash_is_new

    def _recalculate_line_counts(self, diff_hash):
        """Recalculate line counts for the raw data.

        Args:
            diff_hash (reviewboard.diffviewer.models.raw_file_diff_data.
                       RawFileDiffData):
                The raw data to recalculate line counts for.
        """
        diff_hash.recalculate_line_counts(self.get_repository().get_scmtool())

    def __str__(self):
        """Return a human-readable representation of the model.

        Returns:
            unicode:
            A human-readable representation of the model.
        """
        return "%s (%s) -> %s (%s)" % (self.source_file, self.source_revision,
                                       self.dest_file, self.dest_detail)

    class Meta:
        app_label = 'diffviewer'
        db_table = 'diffviewer_filediff'
        verbose_name = _('File Diff')
        verbose_name_plural = _('File Diffs')
