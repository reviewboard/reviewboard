from __future__ import unicode_literals

import bz2
import itertools
import logging

from dateutil.tz import tzoffset
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import six, timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import Base64Field, JSONField, RelationCounterField

from reviewboard.diffviewer.errors import DiffParserError
from reviewboard.diffviewer.graphutils import find_shortest_distances
from reviewboard.diffviewer.managers import (DiffCommitManager,
                                             DiffSetManager,
                                             FileDiffManager,
                                             RawFileDiffDataManager)
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.models import Repository


class LegacyFileDiffData(models.Model):
    """Deprecated, legacy class for base64-encoded diff data.

    This is no longer populated, and exists solely to store legacy data
    that has not been migrated to RawFileDiffData.
    """
    binary_hash = models.CharField(_("hash"), max_length=40, primary_key=True)
    binary = Base64Field(_("base64"))

    extra_data = JSONField(null=True)

    class Meta:
        db_table = 'diffviewer_filediffdata'


class RawFileDiffData(models.Model):
    """Stores raw diff data as binary content in the database.

    This is the class used in Review Board 2.5+ to store diff content.
    Unlike in previous versions, the content is not base64-encoded. Instead,
    it is stored either as bzip2-compressed data (if the resulting
    compressed data is smaller than the raw data), or as the raw data itself.
    """
    COMPRESSION_BZIP2 = 'B'

    COMPRESSION_CHOICES = (
        (COMPRESSION_BZIP2, _('BZip2-compressed')),
    )

    binary_hash = models.CharField(_("hash"), max_length=40, unique=True)
    binary = models.BinaryField()
    compression = models.CharField(max_length=1, choices=COMPRESSION_CHOICES,
                                   null=True, blank=True)
    extra_data = JSONField(null=True)

    objects = RawFileDiffDataManager()

    @property
    def content(self):
        """Returns the content of the diff.

        The content will be uncompressed (if necessary) and returned as the
        raw set of bytes originally uploaded.
        """
        if self.compression == self.COMPRESSION_BZIP2:
            return bz2.decompress(self.binary)
        elif self.compression is None:
            return bytes(self.binary)
        else:
            raise NotImplementedError(
                'Unsupported compression method %s for RawFileDiffData %s'
                % (self.compression, self.pk))

    @property
    def insert_count(self):
        return self.extra_data.get('insert_count')

    @insert_count.setter
    def insert_count(self, value):
        self.extra_data['insert_count'] = value

    @property
    def delete_count(self):
        return self.extra_data.get('delete_count')

    @delete_count.setter
    def delete_count(self, value):
        self.extra_data['delete_count'] = value

    def recalculate_line_counts(self, tool):
        """Recalculates the insert_count and delete_count values.

        This will attempt to re-parse the stored diff and fetch the
        line counts through the parser.
        """
        logging.debug('Recalculating insert/delete line counts on '
                      'RawFileDiffData %s' % self.pk)

        try:
            files = tool.get_parser(self.content).parse()

            if len(files) != 1:
                raise DiffParserError(
                    'Got wrong number of files (%d)' % len(files))
        except DiffParserError as e:
            logging.error('Failed to correctly parse stored diff data in '
                          'RawFileDiffData ID %s when trying to get '
                          'insert/delete line counts: %s',
                          self.pk, e)
        else:
            file_info = files[0]
            self.insert_count = file_info.insert_count
            self.delete_count = file_info.delete_count

            if self.pk:
                self.save(update_fields=['extra_data'])


@python_2_unicode_compatible
class FileDiff(models.Model):
    """
    A diff of a single file.

    This contains the patch and information needed to produce original and
    patched versions of a single file in a repository.
    """
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

    diffset = models.ForeignKey('DiffSet',
                                related_name='files',
                                verbose_name=_("diff set"))

    diff_commit = models.ForeignKey('DiffCommit',
                                    related_name='files',
                                    verbose_name=_('diff commit'),
                                    null=True)

    source_file = models.CharField(_("source file"), max_length=1024)
    dest_file = models.CharField(_("destination file"), max_length=1024)
    source_revision = models.CharField(_("source file revision"),
                                       max_length=512)
    dest_detail = models.CharField(_("destination file details"),
                                   max_length=512)
    binary = models.BooleanField(_("binary file"), default=False)
    status = models.CharField(_("status"), max_length=1, choices=STATUSES)

    diff64 = Base64Field(
        _("diff"),
        db_column="diff_base64",
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
        _("parent diff"),
        db_column="parent_diff_base64",
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
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(self.source_file)

    @property
    def dest_file_display(self):
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(self.dest_file)

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
    def is_new(self):
        return self.source_revision == PRE_CREATION

    def _get_diff(self):
        if self._needs_diff_migration():
            self._migrate_diff_data()

        return self.diff_hash.content

    def _set_diff(self, diff):
        # Add hash to table if it doesn't exist, and set diff_hash to this.
        self.diff_hash, is_new = \
            RawFileDiffData.objects.get_or_create_from_data(diff)
        self.diff64 = ""

        return is_new

    diff = property(_get_diff, _set_diff)

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
        self.parent_diff64 = ''

        return is_new

    parent_diff = property(_get_parent_diff, _set_parent_diff)

    @property
    def orig_sha1(self):
        return self.extra_data.get('orig_sha1')

    @property
    def patched_sha1(self):
        return self.extra_data.get('patched_sha1')

    def get_line_counts(self):
        """Returns the stored line counts for the diff.

        This will return all the types of line counts that can be set:

        * ``raw_insert_count``
        * ``raw_delete_count``
        * ``insert_count``
        * ``delete_count``
        * ``replace_count``
        * ``equal_count``
        * ``total_line_count``

        These are not all guaranteed to have values set, and may instead be
        None. Only ``raw_insert_count``, ``raw_delete_count``
        ``insert_count``, and ``delete_count`` are guaranteed to have values
        set.

        If there isn't a processed number of inserts or deletes stored,
        then ``insert_count`` and ``delete_count`` will be equal to the
        raw versions.
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
        """Sets the line counts on the FileDiff.

        There are many types of useful line counts that can be set.

        ``raw_insert_count`` and ``raw_delete_count`` correspond to the
        raw inserts and deletes in the actual patch, which will be set both
        in this FileDiff and in the associated RawFileDiffData.

        The other counts are stored exclusively in FileDiff, as they are
        more render-specific.
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
        """
        needs_save = False
        diff_hash_is_new = False
        parent_diff_hash_is_new = False
        legacy_pks = []

        if self._needs_diff_migration():
            needs_save = True

            if self.legacy_diff_hash_id:
                logging.debug('Migrating LegacyFileDiffData %s to '
                              'RawFileDiffData for diff in FileDiff %s',
                              self.legacy_diff_hash_id, self.pk)

                diff_hash_is_new = self._set_diff(self.legacy_diff_hash.binary)
                legacy_pks.append(self.legacy_diff_hash_id)
                self.legacy_diff_hash = None
            else:
                logging.debug('Migrating FileDiff %s diff data to '
                              'RawFileDiffData',
                              self.pk)

                diff_hash_is_new = self._set_diff(self.diff64)

            if recalculate_counts:
                self._recalculate_line_counts(self.diff_hash)

        if self._needs_parent_diff_migration():
            needs_save = True

            if self.legacy_parent_diff_hash_id:
                logging.debug('Migrating LegacyFileDiffData %s to '
                              'RawFileDiffData for parent diff in FileDiff %s',
                              self.legacy_parent_diff_hash_id, self.pk)

                parent_diff_hash_is_new = \
                    self._set_parent_diff(self.legacy_parent_diff_hash.binary)
                legacy_pks.append(self.legacy_parent_diff_hash_id)
                self.legacy_parent_diff_hash = None
            else:
                logging.debug('Migrating FileDiff %s parent diff data to '
                              'RawFileDiffData',
                              self.pk)

                parent_diff_hash_is_new = \
                    self._set_parent_diff(self.parent_diff64)

            if recalculate_counts:
                self._recalculate_line_counts(self.parent_diff_hash)

        if needs_save:
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
        """Recalculates the line counts on the specified RawFileDiffData.

        This requires that diff_hash is set. Otherwise, it will assert.
        """
        diff_hash.recalculate_line_counts(
            self.diffset.repository.get_scmtool())

    def __str__(self):
        return "%s (%s) -> %s (%s)" % (self.source_file, self.source_revision,
                                       self.dest_file, self.dest_detail)


class DiffLineCountsMixin(object):
    """A mixin that can find the total line counts of all child FileDiffs."""

    def get_total_line_counts(self):
        """Get the total line counts of all child FileDiffs."""
        counts = {}

        for filediff in self.files.all():
            for key, value in six.iteritems(filediff.get_line_counts()):
                if counts.get(key) is None:
                    counts[key] = value
                elif value is not None:
                    counts[key] += value

        return counts


@python_2_unicode_compatible
class DiffSet(DiffLineCountsMixin, models.Model):
    """
    A revisioned collection of FileDiffs.
    """
    name = models.CharField(_('name'), max_length=256)
    revision = models.IntegerField(_("revision"))
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now)
    basedir = models.CharField(_('base directory'), max_length=256,
                               blank=True, default='')
    history = models.ForeignKey('DiffSetHistory', null=True,
                                related_name="diffsets",
                                verbose_name=_("diff set history"))
    repository = models.ForeignKey(Repository, related_name="diffsets",
                                   verbose_name=_("repository"))
    diffcompat = models.IntegerField(
        _('differ compatibility version'),
        default=0,
        help_text=_("The diff generator compatibility version to use. "
                    "This can and should be ignored."))

    base_commit_id = models.CharField(
        _('commit ID'), max_length=64, blank=True, null=True, db_index=True,
        help_text=_('The ID/revision this change is built upon.'))

    extra_data = JSONField(null=True)

    objects = DiffSetManager()

    diff_commit_count = RelationCounterField('diff_commits')

    def save(self, **kwargs):
        """
        Saves this diffset.

        This will set an initial revision of 1 if this is the first diffset
        in the history, and will set it to on more than the most recent
        diffset otherwise.
        """
        if self.revision == 0 and self.history is not None:
            if self.history.diffsets.count() == 0:
                # Start on revision 1. It's more human-grokable.
                self.revision = 1
            else:
                self.revision = self.history.diffsets.latest().revision + 1

        if self.history:
            self.history.last_diff_updated = self.timestamp
            self.history.save()

        super(DiffSet, self).save()

    def build_commit_graph(self, *extra_commits):
        """Build the directed acyclic graph of the DiffSet's commit history.

        The returned DAG is represented as a dict. The keys of the dict are
        commit IDs and the values are the commit IDs of the parent commits of
        the corresponding commit (including merge parents).

        If the DiffSet has no child DiffCommits, the empty dict is returned.

        The :param:`extra_commits` parameter specifies extra commits that
        should be added to the DAG if they don't already exist in it. This is
        exclusively for the case of DiffCommit validation as the DiffCommit
        being validated will not appear in the DiffSet's set of DiffCommits.
        """
        dag = {}

        commits = self.diff_commits.prefetch_related('merge_parent_ids')

        for commit in itertools.chain(commits.all(), extra_commits):
            if commit.commit_id not in dag:
                dag[commit.commit_id] = [commit.parent_id]
                dag[commit.commit_id].extend(
                    commit.merge_parent_ids.values_list('commit_id',
                                                        flat=True))

        return dag

    def build_file_history_graph(self):
        """Build a directed acyclic graph of the file history in the DiffSet.

        The file history graph tracks a file's history through renames,
        deletions, and creations over the course of an entire commit history of
        a DiffSet.

        The return value is a dict which maps FileDiff primary keys to the
        primary key of a "parent" FileDiff. This parent FileDiff must be
        applied before the child FileDiff is. If a key's corresponding value is
        None, that means either the FileDiff is a new file with no previously
        deleted file by the same name or is a modification of a file in the
        repository.
        """
        def find_parent_deleted_filediff(filediff, files):
            """Return the parent deleted FileDiff in the list of FileDiffs.

            This function returns None is there is no such FileDiff.
            """
            for f in files:
                # This will only ever be called when filediff.is_new is True
                # so we have to go by filediff.dest_file because
                # filediff.source_file might be /dev/null or similar. We must
                # use f.source_file and not f.dest_file for the same reason.
                if f.deleted and f.source_file == filediff.dest_file:
                    return f

            return None

        commit_dag = self.build_commit_graph()
        commits = dict(
            (c.commit_id, c)
            for c in self.diff_commits.prefetch_related('files')
        )

        file_dag = {}

        # We create a mapping of a FileDiff's destination revision and file
        # name to FileDiffs. This allows us to check this mapping for the
        # existence of a parent FileDiff via a dict access instead of filtering
        # for it in a list.
        files_by_dest = {}

        for filediff in self.files.all():
            destination = (filediff.dest_detail, filediff.dest_file)
            files_by_dest.setdefault(destination, []).append(filediff)

        for filediff in itertools.chain(*six.itervalues(files_by_dest)):
            parent_filediff = None

            if filediff.is_new:
                # In this case we need to check the ancestors of the
                # current DiffCommit to see if there is a FileDiff that
                # results in this FileDiff's source_file being a deleted
                # file.

                # We must go though the ancestry of the DiffCommit
                # because it may be the case that a file with the same name
                # was deleted more than once.
                commit_id = filediff.diff_commit.commit_id

                while commit_id in commit_dag and parent_filediff is None:
                    # TODO: This currently only supports linear histories.
                    assert len(commit_dag[commit_id]) == 1
                    commit_id = commit_dag[commit_id][0]

                    if commit_id not in commit_dag:
                        break

                    parent_filediff = find_parent_deleted_filediff(
                        filediff, commits[commit_id].files.all())

                # If we do not find a parent FileDiff, then this file was
                # created in this DiffCommit and was not deleted previously.
                if parent_filediff is None:
                    continue
            else:
                try:
                    dest = (filediff.source_revision, filediff.source_file)
                    possible_parents = files_by_dest[dest]

                    if len(possible_parents) == 1:
                        parent_filediff = possible_parents[0]
                    elif possible_parents:
                        # We need to locate the FileDiff whose commit is the
                        # closest ancestor to the FileDiff's commit.
                        distances = find_shortest_distances(
                            filediff.diff_commit.commit_id,
                            commit_dag)

                        parent_commit_id = min(
                            (
                                commit_id
                                for commit_id in commits
                                if commit_id != filediff.diff_commit.commit_id
                            ),
                            key=lambda commit_id: distances[commit_id])

                        for possible_parent in possible_parents:
                            if (possible_parent.diff_commit.commit_id ==
                                parent_commit_id):
                                parent_filediff = possible_parent
                                break

                        assert parent_filediff is not None
                except KeyError:
                    # In this case the file is not new and relies on a
                    # source revision and file name that is not in our
                    # mapping. It will have to be retrieved from the
                    # repository.
                    continue

            file_dag[filediff.pk] = parent_filediff

        return file_dag

    def get_commit_interval(self, base_commit_id, tip_commit_id, dag=None):
        """Find all commits in the half-open interval (base, tip].

        This function returns a (possibly empty) queryset.
        """
        if dag is None:
            dag = self.build_commit_graph()

        commit_ids = set()
        commit_id = tip_commit_id

        while commit_id in dag:
            if commit_id == base_commit_id:
                break

            commit_ids.add(commit_id)

            # TODO: Graph search.
            assert len(dag[commit_id]) == 1
            commit_id = dag[commit_id][0]

        # The interval (base_commit, tip_commit] is not valid.
        if base_commit_id is not None and base_commit_id != commit_id:
            return DiffCommit.objects.none()

        return self.diff_commits.filter(commit_id__in=commit_ids)

    def __str__(self):
        return "[%s] %s r%s" % (self.id, self.name, self.revision)

    class Meta:
        get_latest_by = 'revision'
        ordering = ['revision', 'timestamp']


@python_2_unicode_compatible
class DiffSetHistory(models.Model):
    """
    A collection of diffsets.

    This gives us a way to store and keep track of multiple revisions of
    diffsets belonging to an object.
    """
    name = models.CharField(_('name'), max_length=256)
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now)
    last_diff_updated = models.DateTimeField(
        _("last updated"),
        blank=True,
        null=True,
        default=None)

    extra_data = JSONField(null=True)

    def __str__(self):
        return 'Diff Set History (%s revisions)' % self.diffsets.count()

    class Meta:
        verbose_name_plural = "Diff set histories"


@python_2_unicode_compatible
class DiffCommit(DiffLineCountsMixin, models.Model):
    """A representation of a commit from a version control system.

    A diff revision on a review request that represents a commit history will
    have one or more DiffCommits. Each one belongs to a Diffset and has zero or
    more associated FileDiffs (each of which will still also belong to the
    parent DiffSet).

    The information stored in a DiffCommit is intended to fully represent the
    state of one commit in that history. A list of DiffCommits can be used to
    re-create the original history of a series of commits posted to a review
    request.
    """
    #: A commit is either a merge or a change. These constants are used for
    #: storage in the database.
    COMMIT_CHANGE_TYPE = 'C'
    COMMIT_MERGE_TYPE = 'M'

    COMMIT_TYPES = (
        (COMMIT_CHANGE_TYPE, _('Change')),
        (COMMIT_MERGE_TYPE, _('Merge')),
    )

    #: The maximum length for a commit's ID.
    COMMIT_ID_LENGTH = 40

    #: Maximum length of a name.
    NAME_MAX_LENGTH = 256

    #: Maximum length of an email
    EMAIL_MAX_LENGTH = 256

    #: The regular expression for a commit's ID.
    COMMIT_ID_RE = r'[A-Za-z0-9]{1,40}'

    #: ISO 8601 date and time format with timezone
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S%z'

    #: A validator for commit ID fields that can also be used in forms.
    validate_commit_id = RegexValidator(COMMIT_ID_RE,
                                        _('Commit IDs must be alphanumeric.'))

    objects = DiffCommitManager()

    #: The name of the .diff file that is uploaded.
    name = models.CharField(_('name'), max_length=256)

    #: A commit belongs to a diffset, which may have many commits.
    diffset = models.ForeignKey(DiffSet, related_name='diff_commits')

    #: Not all SCM tools (e.g., quilt, monotone) have notions of an author
    #: and a committer.
    author_name = models.CharField(max_length=NAME_MAX_LENGTH)
    author_email = models.CharField(max_length=EMAIL_MAX_LENGTH)
    author_date_utc = models.DateTimeField()
    author_date_offset = models.IntegerField()

    committer_name = models.CharField(max_length=NAME_MAX_LENGTH, blank=True)
    committer_email = models.CharField(max_length=EMAIL_MAX_LENGTH, blank=True)
    committer_date_utc = models.DateTimeField(null=True)
    committer_date_offset = models.IntegerField(null=True)

    #: The commit's description.
    description = models.TextField()

    #: The commit's ID/revision.
    commit_id = models.CharField(max_length=COMMIT_ID_LENGTH,
                                 validators=[validate_commit_id])

    #: The parent commit's ID/revision.
    parent_id = models.CharField(max_length=COMMIT_ID_LENGTH,
                                 validators=[validate_commit_id])

    #: The type of the commit, either 'C' for change or 'M' for merge.
    commit_type = models.CharField(max_length=1, choices=COMMIT_TYPES)

    #: The extra data for this commit. This may include information for
    #: SCM tools to re-create commits.
    extra_data = JSONField(null=True)

    #: A timestamp used for generating HTTP caching headers.
    timestamp = models.DateTimeField(_('timestamp'), default=timezone.now)

    @property
    def author_date(self):
        """Get the author date with its original timezone information."""
        tz = tzoffset(None, self.author_date_offset)
        return self.author_date_utc.astimezone(tz)

    @author_date.setter
    def author_date(self, value):
        """Set the author date with timezone information."""
        self.author_date_utc = value  # Django implicitly converts it to UTC
        self.author_date_offset = self._normalize_offset(value.utcoffset())

    @property
    def committer_date(self):
        """Get the committer date with its original timezone information."""
        if self.committer_date_offset:
            tz = tzoffset(None, self.committer_date_offset)
            return self.committer_date_utc.astimezone(tz)

        return None

    @committer_date.setter
    def committer_date(self, value):
        """Set the committer date with timezone information."""
        self.committer_date_utc = value  # Django implicitly converts it to UTC

        if value is None:
            self.committer_date_offset = None
        else:
            self.committer_date_offset = self._normalize_offset(
                value.utcoffset())

    @cached_property
    def summary(self):
        """Return the summary of a DiffCommit.

        The summary is the first 80 characters of the first line of the
        DiffCommit's description field. If the first line is more than 80
        characters, it is truncated.
        """
        text = self.description

        if text:
            text = text.split('\n', 1)[0].strip()

            if len(text) > 80:
                text = text[:77] + '...'

        return text

    @cached_property
    def author(self):
        """Returns a nicely formatted author name and/or email string."""
        return self._pretty_print_name_and_email(self.author_name,
                                                 self.author_email)

    @cached_property
    def committer(self):
        """Returns a nicely formatted committer name and/or email string."""
        return self._pretty_print_name_and_email(self.committer_name,
                                                 self.commiter_email)

    def _pretty_print_name_and_email(self, name, email):
        """Returns a formatted string of a name and/or email address."""
        if name and email:
            return "%s <%s>" % (name, email)

        return name or email

    def __str__(self):
        """Represent this commit by its commit_id and summary."""
        short_description = self.summary

        if short_description:
            return '%s: %s' % (self.commit_id, short_description)
        else:
            return self.commit_id

    def _normalize_offset(self, value):
        """Normalize a timedelta to be a number of seconds."""
        return value.seconds + value.days * 24 * 3600

    class Meta:
        unique_together = ('diffset', 'commit_id')


@python_2_unicode_compatible
class MergeParent(models.Model):
    """A MergeParent represents a parent revision of a merge commit."""
    #: The commit ID for this parent.
    commit_id = models.CharField(max_length=DiffCommit.COMMIT_ID_LENGTH,
                                 validators=[DiffCommit.validate_commit_id])

    #: The child commit.
    child_commit = models.ForeignKey('DiffCommit',
                                     related_name='merge_parent_ids')

    #: The parent ordering, starting at 1.
    merge_ordinal = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.commit_id

    class Meta:
        unique_together = ('commit_id', 'child_commit', 'merge_ordinal')
