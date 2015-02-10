from __future__ import unicode_literals

import hashlib
import json
import logging

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Manager
from django.utils import six, timezone
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy as _

from reviewboard.webapi.errors import WebAPITokenGenerationError


class WebAPITokenManager(Manager):
    """Manages WebAPIToken models."""

    def generate_token(self, user, max_attempts=20, local_site=None,
                       note=None, policy=None):
        """Generates a WebAPIToken for a user.

        This will attempt to construct a unique WebAPIToken for a user.

        Since a collision is possible, it will try up to a certain number
        of times. If it cannot create a unique token, a
        WebAPITokenGenerationError will be raised.
        """
        prefix = settings.SECRET_KEY + six.text_type(user.pk) + user.password

        if isinstance(policy, dict):
            policy = json.dumps(policy)

        for attempt in range(max_attempts):
            sha = hashlib.sha1(prefix + six.text_type(attempt) +
                               timezone.now().isoformat())
            token = sha.hexdigest()

            try:
                return self.create(user=user,
                                   token=token,
                                   local_site=local_site,
                                   note=note,
                                   policy=policy)
            except IntegrityError:
                # We hit a collision with the token value. Try again.
                pass

        # We hit our limit. The database is too full of tokens.
        logging.error('Unable to generate unique API token for %s after '
                      '%d attempts',
                      user.username,
                      max_attempts)

        raise WebAPITokenGenerationError(
            _('Could not create a unique API token. Please try again.'))
