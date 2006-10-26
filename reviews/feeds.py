from django.contrib.syndication.feeds import Feed
from django.core.exceptions import ObjectDoesNotExist
from django.utils.feedgenerator import Atom1Feed
from reviewboard.reviews.models import ReviewRequest

class BaseReviewFeed(Feed):
    title_template = "feeds/reviews_title.html"
    description_template = "feeds/reviews_description.html"

    def item_author_link(self, item):
        return item.submitter.get_absolute_url()

    def item_author_name(self, item):
        return item.submitter.username

    def item_author_email(self, item):
        return item.submitter.username + "@vmware.com" # XXX

    def item_pubdate(self, item):
        return item.last_updated


# RSS Feeds
class RssReviewsFeed(BaseReviewFeed):
    title = "Review Requests"
    link = "/reviews/"
    description = "All pending review requests."

    def items(self):
        return ReviewRequest.objects.order_by('-last_updated')[:20]


class RssSubmittersFeed(BaseReviewFeed):
    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist

        return ReviewRequest.objects.get(submitter__username__exact=bits[0])

    def title(self, submitter):
        return "Review Requests by %s" % submitter

    def link(self, submitter):
        return submitter.get_absolute_url()

    def description(self, submitter):
        return "Pending review requests by %s" % submitter

    def items(self, submitter):
        return ReviewRequest.objects.filter(submitter=submitter).\
            order_by('-last_updated')[:20]


# Atom feeds
class AtomReviewsFeed(RssReviewsFeed):
    feed_type = Atom1Feed

class AtomSubmittersFeed(RssSubmittersFeed):
    feed_type = Atom1Feed
