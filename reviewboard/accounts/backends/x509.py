"""X.509 authentication backend."""

from __future__ import unicode_literals

import logging
import re
import sre_constants

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import X509SettingsForm


class X509Backend(BaseAuthBackend):
    """Authenticate a user from a X.509 client certificate.

    The certificate is passed in by the browser. This backend relies on the
    X509AuthMiddleware to extract a username field from the client certificate.
    """

    backend_id = 'x509'
    name = _('X.509 Public Key')
    settings_form = X509SettingsForm
    supports_change_password = True

    def authenticate(self, request, x509_field='', **kwargs):
        """Authenticate the user.

        This will extract the username from the provided certificate and return
        the appropriate User object.

        Version Changed:
            4.0:
            The ``request`` argument is now mandatory as the first positional
            argument, as per requirements in Django.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the caller. This may be ``None``.

            x509_field (unicode, optional):
                The value of the field containing the username.

            **kwargs (dict, unused):
                Additional keyword arguments supplied by the caller.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user, or ``None`` if the user could not be
            authenticated for any reason.
        """
        username = self.clean_username(x509_field)
        return self.get_or_create_user(username=username,
                                       request=request)

    def clean_username(self, username):
        """Validate the 'username' field.

        This checks to make sure that the contents of the username field are
        valid for X509 authentication.
        """
        username = username.strip()

        if settings.X509_USERNAME_REGEX:
            try:
                m = re.match(settings.X509_USERNAME_REGEX, username)
                if m:
                    username = m.group(1)
                else:
                    logging.warning("X509Backend: username '%s' didn't match "
                                    "regex.", username)
            except sre_constants.error as e:
                logging.error("X509Backend: Invalid regex specified: %s",
                              e, exc_info=1)

        return username

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        user = None
        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # TODO Add the ability to get the first and last names in a
            #      configurable manner; not all X.509 certificates will have
            #      the same format.
            if getattr(settings, 'X509_AUTOCREATE_USERS', False):
                user = User(username=username, password='')
                user.is_staff = False
                user.is_superuser = False
                user.set_unusable_password()
                user.save()

        return user
