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
        help_text=_('An optional Local Site to limit this application to.<br>'
                    'If specified, only users with access to the Local Site '
                    'will be able to use the application.'),
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

    def clean(self):
        """Validate the application.

        We do the validation for this in :py:meth:`ApplicationForm.clean()
        <reviewboard.oauth.forms.ApplicationForm.clean` so that we can have
        errors for ``authorization_grant_type`` and ``redirect_uris`` conflicts
        show up on the appropriate field. The parent class does the same
        validation, but as a result it will have form-wide errors instead of
        per-field errors for the above two fields when they are in conflict.
        Therefore we avoid that validation by making this a no-op.
        """
        pass

    def is_accessible_by(self, user, local_site=None):
        """Return whether or not the user has access to this Application.

        A user has access if one of the following conditions is met:

        * The user owns the Application.
        * The user is an administrator.
        * The user is a Local Site administrator on the Local Site the
          Application is assigned to.

        Args:
            user (django.contrib.auth.models.User):
                The user in question.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site the user would access this Application under.

        Returns:
            bool:
            Whether or not the given user has access to information about
            this Application.
        """
        return (user.is_authenticated() and
                (self.user == user or
                 user.is_superuser or
                 (self.local_site_id is not None and
                  local_site is not None and
                  self.local_site_id == local_site.pk and
                  local_site.is_mutable_by(user))))

    def is_mutable_by(self, user, local_site=None):
        """Return whether or not the user can modify this Application.

        A user has access if one of the following conditions is met:

        * The user owns the Application.
        * The user is an administrator.
        * The user is a Local Site administrator on the Local Site the
          Application is assigned to.

        Args:
            user (django.contrib.auth.models.User):
                The user in question.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site the user would modify this Application under.

        Returns:
            bool:
            Whether or not the given user can modify this Application.
        """
        return self.is_accessible_by(user, local_site=local_site)

    class Meta:
        db_table = 'reviewboard_oauth_application'
        verbose_name = _('OAuth Application')
        verbose_name_plural = _('OAuth Applications')
