"""DiffSet model definiton."""

from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField, RelationCounterField

from reviewboard.diffviewer.diffutils import get_total_line_counts
from reviewboard.diffviewer.managers import DiffSetManager
from reviewboard.scmtools.models import Repository


@python_2_unicode_compatible
class DiffSet(models.Model):
    """A revisioned collection of FileDiffs."""

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
