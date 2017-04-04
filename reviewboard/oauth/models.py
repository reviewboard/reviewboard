"""Models for OAuth2 applications."""

from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField
from oauth2_provider.models import AbstractApplication

from reviewboard.site.models import LocalSite


class Application(AbstractApplication):
    """An OAuth2 application.

    This model is specialized so that it can be limited to a
    :py:class:`~reviewboard.site.models.LocalSite`.
    """

    local_site = models.ForeignKey(
        verbose_name=_('Local Site'),
        to=LocalSite,
        related_name='oauth_applications',
        blank=True,
        null=True,
        help_text=_('An optional LocalSite to limit this application to.'),
    )

    extra_data = JSONField(
        _('Extra Data'),
        null=True,
        default=dict,
    )

    class Meta:
        db_table = 'reviewboard_oauth_application'
        verbose_name = _('OAuth Application')
        verbose_name_plural = _('OAuth Applications')
