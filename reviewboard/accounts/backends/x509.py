"""X.509 authentication backend."""

from __future__ import annotations

import logging
import re
from typing import Optional, TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import X509SettingsForm

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)


class X509Backend(BaseAuthBackend):
    """Authenticate a user from a X.509 client certificate.

    The certificate is passed in by the browser. This backend relies on the
    X509AuthMiddleware to extract a username field from the client certificate.
    """

    backend_id = 'x509'
    name = _('X.509 Public Key')
    settings_form = X509SettingsForm
    supports_change_password = True

    def authenticate(
        self,
        request: Optional[HttpRequest] = None,
        *,
        x509_field: str = '',
        **kwargs,
    ) -> Optional[User]:
        """Authenticate the user.

        This will extract the username from the provided certificate and return
        the appropriate User object.

        Version Changed:
            6.0:
            * ``request`` is now optional.
            * ``username`` and ``password`` are technically optional, to
              aid in consistency for type hints, but will result in a ``None``
              result.

        Version Changed:
            4.0:
            The ``request`` argument is now mandatory as the first positional
            argument, as per requirements in Django.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the caller. This may be ``None``.

            x509_field (str, optional):
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

    def clean_username(
        self,
        username: str,
    ) -> str:
        """Validate the 'username' field.

        This checks to make sure that the contents of the username field are
        valid for X509 authentication.

        Args:
            username (str):
                The username to validate.

        Returns:
            str:
            The resulting username.
        """
        username = username.strip()

        x509_username_regex = getattr(settings, 'X509_USERNAME_REGEX', None)

        if x509_username_regex:
            try:
                m = re.match(x509_username_regex, username)

                if m:
                    username = m.group(1)
                else:
                    logger.warning("X509Backend: username '%s' didn't match "
                                   "regex.", username)
            except re.error as e:
                logger.error('X509Backend: Invalid regex specified: %s',
                             e, exc_info=True)

        return username

    def get_or_create_user(
        self,
        username: str,
        request: Optional[HttpRequest] = None,
    ) -> Optional[User]:
        """Return an existing user or create one if it doesn't exist.

        This does not authenticate the user.

        If the user does not exist in the database, but does in the backend,
        its information will be stored in the database for later lookup.

        Args:
            username (str):
                The username to fetch or create.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, or ``None`` if one could not be found.
        """
        user: Optional[User] = None
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
