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


class UpdateLastLoginMiddleware(object):
    """Middleware that updates a user's last login time more frequently.

    This will update the user's stored login time if it's been more than 30
    minutes since they last made a request. This helps turn the login time into
    a recent activity time, providing a better sense of how often people are
    actively using Review Board.
    """

    #: The smallest period of time between login time updates.
    UPDATE_PERIOD_SECS = 30 * 60  # 30 minutes

    def process_request(self, request):
        """Process the request and update the login time.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.
        """
        user = request.user

        if user.is_authenticated():
            now = timezone.now()
            delta = now - request.user.last_login

            if delta.total_seconds() >= self.UPDATE_PERIOD_SECS:
                user.last_login = now
                user.save(update_fields=('last_login',))
