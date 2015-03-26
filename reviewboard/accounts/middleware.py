from __future__ import unicode_literals

import pytz
from django.utils import timezone

from reviewboard.accounts.models import Profile


class TimezoneMiddleware(object):
    """Middleware that activates the user's local timezone."""

    def process_request(self, request):
        """Activate the user's selected timezone for this request."""
        if request.user.is_authenticated():
            try:
                user = request.user.get_profile()
                timezone.activate(pytz.timezone(user.timezone))
            except (Profile.DoesNotExist, pytz.UnknownTimeZoneError):
                pass
