from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import CounterField, JSONField
from djblets.db.managers import ConcurrencyManager


@python_2_unicode_compatible
class BaseComment(models.Model):
    OPEN           = "O"
    RESOLVED       = "R"
    DROPPED        = "D"

    ISSUE_STATUSES = (
        (OPEN,      _('Open')),
        (RESOLVED,  _('Resolved')),
        (DROPPED,   _('Dropped')),
    )
    issue_opened = models.BooleanField(_("issue opened"), default=False)
    issue_status = models.CharField(_("issue status"),
                                    max_length=1,
                                    choices=ISSUE_STATUSES,
                                    blank=True,
                                    null=True,
                                    db_index=True)

    reply_to = models.ForeignKey("self", blank=True, null=True,
                                 related_name="replies",
                                 verbose_name=_("reply to"))
    timestamp = models.DateTimeField(_('timestamp'), default=timezone.now)
    text = models.TextField(_("comment text"))
    rich_text = models.BooleanField(_("rich text"), default=False)

    extra_data = JSONField(null=True)

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

    @staticmethod
    def issue_status_to_string(status):
        if status == "O":
            return "open"
        elif status == "R":
            return "resolved"
        elif status == "D":
            return "dropped"
        else:
            return ""

    @staticmethod
    def issue_string_to_status(status):
        if status == "open":
            return "O"
        elif status == "resolved":
            return "R"
        elif status == "dropped":
            return "D"
        else:
            raise Exception("Invalid issue status '%s'" % status)

    def __init__(self, *args, **kwargs):
        super(BaseComment, self).__init__(*args, **kwargs)

        self._loaded_issue_status = self.issue_status

    def get_review_request(self):
        if hasattr(self, '_review_request'):
            return self._review_request
        else:
            return self.get_review().review_request

    def get_review(self):
        if hasattr(self, '_review'):
            return self._review
        else:
            return self.review.get()

    def get_review_url(self):
        return "%s#%s%d" % \
            (self.get_review_request().get_absolute_url(),
             self.anchor_prefix, self.id)

    def is_reply(self):
        """Returns whether this comment is a reply to another comment."""
        return self.reply_to_id is not None
    is_reply.boolean = True

    def is_accessible_by(self, user):
        """Returns whether the user can access this comment."""
        return self.get_review().is_accessible_by(user)

    def is_mutable_by(self, user):
        """Returns whether the user can modify this comment."""
        return self.get_review().is_mutable_by(user)

    def public_replies(self, user=None):
        """
        Returns a list of public replies to this comment, optionally
        specifying the user replying.
        """
        if hasattr(self, '_replies'):
            return self._replies

        if user:
            return self.replies.filter(Q(review__public=True) |
                                       Q(review__user=user))
        else:
            return self.replies.filter(review__public=True)

    def can_change_issue_status(self, user):
        """Returns whether the user can change the issue status.

        Currently, this is allowed for:
        - The user who owns the review request.
        - The user who opened the issue (posted the comment).
        """
        if not (user and user.is_authenticated()):
            return False

        return (self.get_review_request().is_mutable_by(user) or
                user == self.get_review().user)

    def save(self, **kwargs):
        from reviewboard.reviews.models.review_request import ReviewRequest

        self.timestamp = timezone.now()

        super(BaseComment, self).save()

        try:
            # Update the review timestamp, but only if it's a draft.
            # Otherwise, resolving an issue will change the timestamp of
            # the review.
            review = self.get_review()

            if not review.public:
                review.timestamp = self.timestamp
                review.save()
            else:
                if (not self.is_reply() and
                    self.issue_opened and
                    self._loaded_issue_status != self.issue_status):
                    # The user has toggled the issue status of this comment,
                    # so update the issue counts for the review request.
                    old_field = ReviewRequest.ISSUE_COUNTER_FIELDS[
                        self._loaded_issue_status]
                    new_field = ReviewRequest.ISSUE_COUNTER_FIELDS[
                        self.issue_status]

                    CounterField.increment_many(
                        self.get_review_request(),
                        {
                            old_field: -1,
                            new_field: 1,
                        })

                q = ReviewRequest.objects.filter(pk=review.review_request_id)
                q.update(last_review_activity_timestamp=self.timestamp)
        except ObjectDoesNotExist:
            pass

    def __str__(self):
        return self.text

    class Meta:
        abstract = True
        app_label = 'reviews'
        ordering = ['timestamp']
