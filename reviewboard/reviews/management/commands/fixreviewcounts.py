from django.core.management.base import NoArgsCommand

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.reviews.models import Group


class Command(NoArgsCommand):
    help="Fixes all incorrect review request-related counters."

    def handle_noargs(self, **options):
        LocalSiteProfile.objects.update(
            direct_incoming_request_count=None,
            total_incoming_request_count=None,
            pending_outgoing_request_count=None,
            total_outgoing_request_count=None,
            starred_public_request_count=None)
        Group.objects.update(incoming_request_count=None)
