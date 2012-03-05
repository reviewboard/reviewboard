import pytz
from django.utils import timezone

from reviewboard.accounts.models import Profile


class TimezoneMiddleware(object):
    """Middleware that activates the user's local timezone"""
    def process_request(self, request):
        if request.user.is_authenticated():
            try:
                user = Profile.objects.get(user=request.user)
                timezone.activate(pytz.timezone(user.timezone))
            except Profile.DoesNotExist:
                pass
