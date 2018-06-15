"""HTTP Digest authentication backend."""

from __future__ import unicode_literals

import hashlib
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import HTTPBasicSettingsForm


class HTTPDigestBackend(BaseAuthBackend):
    """Authenticate against a user in a digest password file."""

    backend_id = 'digest'
    name = _('HTTP Digest Authentication')
    settings_form = HTTPBasicSettingsForm
    login_instructions = \
        _('Use your standard username and password.')

    def authenticate(self, username, password, **kwargs):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        username = username.strip()

        digest_text = '%s:%s:%s' % (username, settings.DIGEST_REALM, password)
        digest_password = hashlib.md5(digest_text).hexdigest()

        try:
            with open(settings.DIGEST_FILE_LOCATION, 'r') as passwd_file:
                for line_no, line in enumerate(passwd_file):
                    try:
                        user, realm, passwd = line.strip().split(':')

                        if user == username and passwd == digest_password:
                            return self.get_or_create_user(username, None)
                        else:
                            continue
                    except ValueError as e:
                        logging.error('Error parsing HTTP Digest password '
                                      'file at line %d: %s',
                                      line_no, e, exc_info=True)
                        break

        except IOError as e:
            logging.error('Could not open the HTTP Digest password file: %s',
                          e, exc_info=True)

        return None

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username, password='')
            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()
            user.save()

        return user
