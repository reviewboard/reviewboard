"""DiffSet model definiton."""

from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import six, timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext, ugettext_lazy as _
from djblets.db.fields import JSONField, RelationCounterField

from reviewboard.diffviewer.filediff_creator import create_filediffs
from reviewboard.diffviewer.diffutils import get_total_line_counts
from reviewboard.diffviewer.managers import DiffSetManager
from reviewboard.scmtools.models import Repository


@python_2_unicode_compatible
class DiffSet(models.Model):
    """A revisioned collection of FileDiffs."""

    _FINALIZED_COMMIT_SERIES_KEY = '__finalized_commit_series'

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

    commit_count = RelationCounterField('commits')

    extra_data = JSONField(null=True)

    objects = DiffSetManager()

    @property
    def is_commit_series_finalized(self):
        """Whether the commit series represented by this DiffSet is finalized.

        When a commit series is finalized, no more :py:class:`DiffCommits
        <reviewboard.diffviewer.models.diffcommit.DiffCommit>` can be added to
        it.
        """
        return (self.extra_data and
                self.extra_data.get(self._FINALIZED_COMMIT_SERIES_KEY, False))

    def finalize_commit_series(self, cumulative_diff, validation_info,
                               parent_diff=None, request=None, validate=True,
                               save=False):
        """Finalize the commit series represented by this DiffSet.

        Args:
            cumulative_diff (bytes):
                The cumulative diff of the entire commit series.

            validation_info (dict):
                The parsed validation information.

            parent_diff (bytes, optional):
                The parent diff of the cumulative diff, if any.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client, if any.

            validate (bool, optional):
                Whether or not the cumulative diff (and optional parent diff)
                should be validated, up to and including file existence checks.

            save (bool, optional):
                Whether to save the model after finalization. Defaults to
                ``False``.

                If ``True``, only the :py:attr:`extra_data` field will be
                updated.

                If ``False``, the caller must save this model.

        Returns:
            list of reviewboard.diffviewer.models.filediff.FileDiff:
            The list of created FileDiffs.

        Raises:
            django.core.exceptions.ValidationError:
                The commit series failed validation.
        """
        if validate:
            if self.is_commit_series_finalized:
                raise ValidationError(
                    ugettext('This diff is already finalized.'),
                    code='invalid')

            if not self.files.exists():
                raise ValidationError(
                    ugettext('Cannot finalize an empty commit series.'),
                    code='invalid')

            commits = {
                commit.commit_id: commit
                for commit in self.commits.all()
            }

            missing_commit_ids = set()

            for commit_id, info in six.iteritems(validation_info):
                if (commit_id not in commits or
                    commits[commit_id].parent_id != info['parent_id']):
                    missing_commit_ids.add(commit_id)

            if missing_commit_ids:
                raise ValidationError(
                    ugettext('The following commits are specified in '
                             'validation_info but do not exist: %s')
                    % ', '.join(missing_commit_ids),
                    code='validation_info')

            for commit_id, commit in six.iteritems(commits):
                if (commit_id not in validation_info or
                    validation_info[commit_id]['parent_id'] !=
                        commit.parent_id):
                    missing_commit_ids.add(commit_id)

            if missing_commit_ids:
                raise ValidationError(
                    ugettext('The following commits exist but are not '
                             'present in validation_info: %s')
                    % ', '.join(missing_commit_ids),
                    code='validation_info')

        filediffs = create_filediffs(
            get_file_exists=self.repository.get_file_exists,
            diff_file_contents=cumulative_diff,
            parent_diff_file_contents=parent_diff,
            repository=self.repository,
            request=request,
            basedir=self.basedir,
            base_commit_id=self.base_commit_id,
            diffset=self,
            check_existence=validate)

        if self.extra_data is None:
            self.extra_data = {}

        self.extra_data[self._FINALIZED_COMMIT_SERIES_KEY] = True

        if save:
            self.save(update_fields=('extra_data',))

        return filediffs

    def get_total_line_counts(self):
        """Return the total line counts of all child FileDiffs.

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

            Each entry maps to the sum of that line count type for all child
            :py:class:`FileDiffs
            <reviewboard.diffviewer.models.filediff.FileDiff>`.
        """
        return get_total_line_counts(self.files.all())

    @property
    def per_commit_files(self):
        """The files limited to per-commit diffs.

        This will cache the results for future lookups. If the set of all files
        has already been fetched with :py:meth:`~django.db.models.query.
        QuerySet.prefetch_related`, no queries will be performed.
        """
        if not hasattr(self, '_per_commit_files'):
            # This is a giant hack because Django 1.6.x does not support
            # Prefetch() statements. In Django 1.8+ we can replace any use of:
            #
            #     # Django == 1.6
            #     ds = DiffSet.objects.prefetch_related('files')
            #     for d in ds:
            #         # Do something with d.per_commit_files
            #
            # with:
            #
            #     # Django >= 1.8
            #     ds = DiffSet.objects.prefetch_related(
            #         Prefetch('files',
            #                  queryset=File.objects.filter(
            #                      commit_id__isnull=False),
            #                  to_attr='per_commit_files')
            #     for d in ds:
            #         # Do something with d.per_commit_files
            if (hasattr(self, '_prefetched_objects_cache') and
                'files' in self._prefetched_objects_cache):
                self._per_commit_files = [
                    f
                    for f in self.files.all()
                    if f.commit_id is not None
                ]
            else:
                self._per_commit_files = list(self.files.filter(
                    commit_id__isnull=False))

        return self._per_commit_files

    @property
    def cumulative_files(self):
        """The files limited to the cumulative diff.

        This will cache the results for future lookups. If the set of all files
        has been already been fetched with :py:meth:`~django.db.models.query.
        QuerySet.prefetch_related`, no queries will be incurred.
        """
        # See per_commit_files for why we are doing this hack.
        if not hasattr(self, '_cumulative_files'):
            if (hasattr(self, '_prefetched_objects_cache') and
                'files' in self._prefetched_objects_cache):
                self._cumulative_files = [
                    f
                    for f in self.files.all()
                    if f.commit_id is None
                ]
            else:
                self._cumulative_files = list(self.files.filter(
                    commit_id__isnull=True))

        return self._cumulative_files

    def update_revision_from_history(self, diffset_history):
        """Update the revision of this diffset based on a diffset history.

        This will determine the appropriate revision to use for the diffset,
        based on how many other diffsets there are in the history. If there
        aren't any, the revision will be set to 1.

        Args:
            diffset_history (reviewboard.diffviewer.models.diffset_history.
                             DiffSetHistory):
                The diffset history used to compute the new revision.

        Raises:
            ValueError:
                The revision already has a valid value set, and cannot be
                updated.
        """
        if self.revision not in (0, None):
            raise ValueError('The diffset already has a valid revision set.')

        # Default this to revision 1. We'll use this if the DiffSetHistory
        # isn't saved yet (which may happen when creating a new review request)
        # or if there aren't yet any diffsets.
        self.revision = 1

        if diffset_history.pk:
            try:
                latest_diffset = \
                    diffset_history.diffsets.only('revision').latest()
                self.revision = latest_diffset.revision + 1
            except DiffSet.DoesNotExist:
                # Stay at revision 1.
                pass

    def save(self, **kwargs):
        """Save this diffset.

        This will set an initial revision of 1 if this is the first diffset
        in the history, and will set it to on more than the most recent
        diffset otherwise.

        Args:
            **kwargs (dict):
                Extra arguments for the save call.
        """
        if self.history is not None:
            if self.revision == 0:
                self.update_revision_from_history(self.history)

            self.history.last_diff_updated = self.timestamp
            self.history.save()

        super(DiffSet, self).save(**kwargs)

    def __str__(self):
        """Return a human-readable representation of the DiffSet.

        Returns:
            unicode:
            A human-readable representation of the DiffSet.
        """
        return "[%s] %s r%s" % (self.id, self.name, self.revision)

    class Meta:
        app_label = 'diffviewer'
        db_table = 'diffviewer_diffset'
        get_latest_by = 'revision'
        ordering = ['revision', 'timestamp']
        verbose_name = _('Diff Set')
        verbose_name_plural = _('Diff Sets')
