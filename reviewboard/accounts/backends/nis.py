"""NIS authentication backend."""

from __future__ import unicode_literals

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

    def authenticate(self, username, password, **kwargs):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        import crypt
        import nis

        username = username.strip()

        try:
            passwd = nis.match(username, 'passwd').split(':')
            original_crypted = passwd[1]
            new_crypted = crypt.crypt(password, original_crypted)

            if original_crypted == new_crypted:
                return self.get_or_create_user(username, None, passwd)
        except nis.error:
            # FIXME I'm not sure under what situations this would fail (maybe
            # if their NIS server is down), but it'd be nice to inform the
            # user.
            pass

        return None

    def get_or_create_user(self, username, request, passwd=None):
        """Get an existing user, or create one if it does not exist."""
        import nis

        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                if not passwd:
                    passwd = nis.match(username, 'passwd').split(':')

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
            except nis.error:
                pass
        return user
