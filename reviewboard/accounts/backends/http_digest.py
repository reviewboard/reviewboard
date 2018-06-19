"""HTTP Digest authentication backend."""

from __future__ import unicode_literals

import hashlib
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import HTTPBasicSettingsForm


logger = logging.getLogger(__name__)


class HTTPDigestBackend(BaseAuthBackend):
    """Authenticate against a user in a digest password file.

    This is controlled by the following Django settings:

    .. setting:: DIGEST_FILE_LOCATION

    ``DIGEST_FILE_LOCATION``:
        The local file path on the server containing an HTTP password
        (:file:`htpasswd`) file.

        This is ``auth_digest_file_location`` in the site configuration.


    .. setting:: DIGEST_REALM

    ``DIGEST_REALM``:
        The HTTP realm users will be authenticated into.

        This is ``auth_digest_realm`` in the site configuration.
    """

    backend_id = 'digest'
    name = _('HTTP Digest Authentication')
    settings_form = HTTPBasicSettingsForm
    login_instructions = _('Use your standard username and password.')

    def authenticate(self, username, password, **kwargs):
        """Authenticate a user against the HTTP password file.

        Args:
            username (unicode):
                The username to authenticate.

            password (unicode):
                The user's password.

            **kwargs (dict, unused):
                Additional keyword arguments passed by the caller.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user. If authentication fails for any reason,
            this will return ``None``.
        """
        username = username.strip()

        filename = settings.DIGEST_FILE_LOCATION
        digest_text = '%s:%s:%s' % (username, settings.DIGEST_REALM, password)
        digest_password = hashlib.md5(digest_text).hexdigest()

        try:
            with open(filename, 'r') as fp:
                for line_no, line in enumerate(fp):
                    try:
                        user, realm, passwd = line.strip().split(':')

                        if user == username and passwd == digest_password:
                            return self.get_or_create_user(username=username)
                    except ValueError as e:
                        logger.exception('Error parsing HTTP Digest password '
                                         'file "%s" at line %d: %s',
                                         filename, line_no, e)
                        break
        except IOError as e:
            logger.exception('Could not open the HTTP Digest password '
                             'file "%s": %s',
                             filename, e)

        return None

    def get_or_create_user(self, username, request=None):
        """Return an existing user or create one if it doesn't exist.

        This does not authenticate the user.

        If the user does not exist in the database, but does in the HTTP
        password file, its information will be stored in the database for later
        lookup.

        Args:
            username (unicode):
                The name of the user to look up or create.

            request (django.http.HttpRequest, unused):
                The HTTP request from the client. This is unused.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, or ``None`` if one could not be found.
        """
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username)

        return user
