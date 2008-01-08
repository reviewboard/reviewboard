from django.core.management.base import NoArgsCommand
from django.db.models import Q

from reviews.models import ReviewRequest, Review, Screenshot

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        orphaned_screenshots = \
            Screenshot.objects.filter(review_request__isnull=True,
                                      inactive_review_request__isnull=True,
                                      screenshotcomment__isnull=False)
        for screenshot in orphaned_screenshots:
            for comment in screenshot.screenshotcomment_set.all():
                review_request = comment.review_set.get().review_request
                review_request.screenshots.add(screenshot)
                review_request.save()
