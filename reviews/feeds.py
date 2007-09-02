from django.contrib.auth.models import User
from django.contrib.syndication.feeds import Feed
from django.core.exceptions import ObjectDoesNotExist
from django.utils.feedgenerator import Atom1Feed

from reviewboard.reviews.models import Group

class BaseReviewFeed(Feed):
    title_template = "feeds/reviews_title.html"
    description_template = "feeds/reviews_description.html"

    def item_author_link(self, item):
        return item.submitter.get_absolute_url()

    def item_author_name(self, item):
        return item.submitter.username

    def item_author_email(self, item):
        return item.submitter.email

    def item_pubdate(self, item):
        return item.last_updated


# RSS Feeds
class RssReviewsFeed(BaseReviewFeed):
    title = "Review Requests"
    link = "/r/all/"
    description = "All pending review requests."

    def items(self):
        return ReviewRequest.objects.public()[:20]


class RssSubmitterReviewsFeed(BaseReviewFeed):
    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist

        return User.objects.get(username=bits[0])

    def title(self, submitter):
        return u"Review requests to %s" % submitter

    def link(self, submitter):
        return submitter.get_absolute_url()

    def description(self, submitter):
        return u"Pending review requests to %s" % submitter

    def items(self, submitter):
        return ReviewRequest.objects.to_user_directly(submitter.username).\
            order_by('-last_updated')[:20]


class RssGroupReviewsFeed(BaseReviewFeed):
    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist

        return Group.objects.get(name=bits[0])

    def title(self, group):
        return u"Review requests to group %s" % group

    def link(self, group):
        return group.get_absolute_url()

    def description(self, group):
        return u"Pending review requests to %s" % group

    def items(self, group):
        return ReviewRequest.objects.to_group(group).\
            order_by('-last_updated')[:20]


# Atom feeds
class AtomReviewsFeed(RssReviewsFeed):
    feed_type = Atom1Feed

class AtomSubmitterReviewsFeed(RssSubmitterReviewsFeed):
    feed_type = Atom1Feed

class AtomGroupReviewsFeed(RssGroupReviewsFeed):
    feed_type = Atom1Feed
