"""NIS authentication backend."""

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import NISSettingsForm


class NISBackend(BaseAuthBackend):
    """Authenticate against a user on an NIS server."""

    backend_id = 'nis'
    name = _('NIS')
    settings_form = NISSettingsForm
    login_instructions = \
        _('Use your standard NIS username and password.')

    def authenticate(self, request, username, password, **kwargs):
        """Authenticate the user.

        This will attempt to authenticate the user against NIS. If the
        username and password are valid, a user will be returned, and added
        to the database if it doesn't already exist.

        Version Changed:
            4.0:
            The ``request`` argument is now mandatory as the first positional
            argument, as per requirements in Django.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the caller. This may be ``None``.

            username (unicode):
                The username to authenticate.

            password (unicode):
                The password to authenticate.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user, or ``None`` if the user could not be
            authenticated.
        """
        import crypt
        import nis

        username = username.strip()

        try:
            passwd = self._nis_get_passwd(username)
        except nis.error:
            # The user does not exist, or there was an error communicating
            # with NIS.
            return None

        original_crypted = passwd[1]
        new_crypted = crypt.crypt(password, original_crypted)

        if original_crypted == new_crypted:
            return self.get_or_create_user(username=username,
                                           request=request,
                                           passwd=passwd)

        return None

    def get_or_create_user(self, username, request=None, passwd=None):
        """Return an existing user, or create one if it does not exist.

        Args:
            username (unicode):
                The username of the user.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            passwd (tuple, optional):
                The parsed NIS passwd entry for the user.

        Returns:
            django.contrib.auth.models.User:
            The existing or newly-created user, or ``None`` if an error was
            encountered.
        """
        import nis

        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if not passwd:
                try:
                    passwd = self._nis_get_passwd(username)
                except nis.error:
                    # The user does not exist, or there was an error
                    # communicating with NIS.
                    return None

            names = passwd[4].split(',')[0].split(' ', 1)
            first_name = names[0]
            last_name = None

            if len(names) > 1:
                last_name = names[1]

            email = '%s@%s' % (username, settings.NIS_EMAIL_DOMAIN)

            user = User(username=username,
                        password='',
                        first_name=first_name,
                        last_name=last_name or '',
                        email=email)
            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()
            user.save()

        return user

    def _nis_get_passwd(self, username):
        """Return a passwd entry for a user.

        Args:
            username (unicode):
                The username to fetch.

        Returns:
            tuple:
            The parsed passwd entry.

        Raises:
            nis.error:
                The user could not be found, or there was an error performing
                the lookup.
        """
        import nis

        return nis.match(username, 'passwd').split(':')
