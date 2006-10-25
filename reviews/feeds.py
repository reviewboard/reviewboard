from django.contrib.syndication.feeds import Feed
from reviewboard.reviews.models import ReviewRequest

class BaseReviewFeed(Feed):
    def item_author_link(self, item):
        return item.submitter.get_absolute_url()

    def item_author_name(self, item):
        return item.submitter.username

    def item_author_email(self, item):
        return item.submitter.username + "@vmware.com" # XXX

    def item_pubdate(self, item):
        return item.last_updated


class ReviewsFeed(BaseReviewFeed):
    title = "Review Requests"
    link = "/reviews/"
    description = "All pending review requests."

    def items(self):
        return ReviewRequest.objects.order_by('-last_updated')[:20]

