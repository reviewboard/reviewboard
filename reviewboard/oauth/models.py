"""Models for OAuth2 applications."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
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

    enabled = models.BooleanField(
        verbose_name=_('Enabled'),
        help_text=_('Whether or not this application can be used to '
                    'authenticate with Review Board.'),
        default=True,
    )

    original_user = models.ForeignKey(
        verbose_name=_('Original User'),
        to=User,
        blank=True,
        null=True,
        help_text=_('The original owner of this application.')
    )

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

    @property
    def is_disabled_for_security(self):
        """Whether or not this application is disabled for security reasons.

        This will be ``True`` when the :py:attr:`original_owner` no longer
        has access to the :py:attr:`local_site` this application is associated
        with.
        """
        return not self.enabled and self.original_user_id is not None

    class Meta:
        db_table = 'reviewboard_oauth_application'
        verbose_name = _('OAuth Application')
        verbose_name_plural = _('OAuth Applications')
