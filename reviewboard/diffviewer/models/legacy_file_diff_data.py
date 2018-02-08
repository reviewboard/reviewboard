"""LegacyFileDiffData model defitnition."""

from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import Base64Field, JSONField


class LegacyFileDiffData(models.Model):
    """Deprecated, legacy class for base64-encoded diff data.

    This is no longer populated, and exists solely to store legacy data
    that has not been migrated to :py:class:`RawFileDiffData`.
    """

    binary_hash = models.CharField(_('hash'), max_length=40, primary_key=True)
    binary = Base64Field(_('base64'))

    extra_data = JSONField(null=True)

    class Meta:
        app_label = 'diffviewer'
        db_table = 'diffviewer_filediffdata'
        verbose_name = _('Legacy File Diff Data')
        verbose_name_plural = _('Legacy File Diff Data Blobs')
