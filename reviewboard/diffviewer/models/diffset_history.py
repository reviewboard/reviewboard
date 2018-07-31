"""DiffSetHistory model definition."""

from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class DiffSetHistory(models.Model):
    """A collection of diffsets.

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
        """Return a human-readable representation of the model.

        Returns:
            unicode:
            A human-readable representation of the model.
        """
        return 'Diff Set History (%s revisions)' % self.diffsets.count()

    class Meta:
        app_label = 'diffviewer'
        db_table = 'diffviewer_diffsethistory'
        verbose_name = _('Diff Set History')
        verbose_name_plural = _('Diff Set Histories')
