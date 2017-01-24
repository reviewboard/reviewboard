from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import CounterField, JSONField
from djblets.db.query import get_object_or_none

from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.managers import ReviewManager
from reviewboard.reviews.models.base_comment import BaseComment
from reviewboard.reviews.models.diff_comment import Comment
from reviewboard.reviews.models.file_attachment_comment import \
    FileAttachmentComment
from reviewboard.reviews.models.review_request import (ReviewRequest,
                                                       fetch_issue_counts)
from reviewboard.reviews.models.screenshot_comment import ScreenshotComment
from reviewboard.reviews.signals import (reply_publishing, reply_published,
                                         review_publishing, review_published)


@python_2_unicode_compatible
class Review(models.Model):
    """A review of a review request."""

    SHIP_IT_TEXT = 'Ship It!'

    review_request = models.ForeignKey(ReviewRequest,
                                       related_name="reviews",
                                       verbose_name=_("review request"))
    user = models.ForeignKey(User, verbose_name=_("user"),
                             related_name="reviews")
    timestamp = models.DateTimeField(_('timestamp'), default=timezone.now)
    public = models.BooleanField(_("public"), default=False)
    ship_it = models.BooleanField(
        _("ship it"),
        default=False,
        help_text=_("Indicates whether the reviewer thinks this code is "
                    "ready to ship."))
    base_reply_to = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        related_name="replies",
        verbose_name=_("Base reply to"),
        help_text=_("The top-most review in the discussion thread for "
                    "this review reply."))
    email_message_id = models.CharField(_("e-mail message ID"), max_length=255,
                                        blank=True, null=True)
    time_emailed = models.DateTimeField(_("time e-mailed"), null=True,
                                        default=None, blank=True)

    body_top = models.TextField(
        _("body (top)"),
        blank=True,
        help_text=_("The review text shown above the diff and screenshot "
                    "comments."))
    body_top_rich_text = models.BooleanField(
        _("body (top) in rich text"),
        default=False)

    body_bottom = models.TextField(
        _("body (bottom)"),
        blank=True,
        help_text=_("The review text shown below the diff and screenshot "
                    "comments."))
    body_bottom_rich_text = models.BooleanField(
        _("body (bottom) in rich text"),
        default=False)

    body_top_reply_to = models.ForeignKey(
        "self", blank=True, null=True,
        related_name="body_top_replies",
        verbose_name=_("body (top) reply to"),
        help_text=_("The review that the body (top) field is in reply to."))
    body_bottom_reply_to = models.ForeignKey(
        "self", blank=True, null=True,
        related_name="body_bottom_replies",
        verbose_name=_("body (bottom) reply to"),
        help_text=_("The review that the body (bottom) field is in reply to."))

    comments = models.ManyToManyField(Comment, verbose_name=_("comments"),
                                      related_name="review", blank=True)
    screenshot_comments = models.ManyToManyField(
        ScreenshotComment,
        verbose_name=_("screenshot comments"),
        related_name="review",
        blank=True)
    file_attachment_comments = models.ManyToManyField(
        FileAttachmentComment,
        verbose_name=_("file attachment comments"),
        related_name="review",
        blank=True)

    extra_data = JSONField(null=True)

    # Deprecated and no longer used for new reviews as of 2.0.9.
    rich_text = models.BooleanField(_("rich text"), default=False)

    # XXX Deprecated. This will be removed in a future release.
    reviewed_diffset = models.ForeignKey(
        DiffSet, verbose_name="Reviewed Diff",
        blank=True, null=True,
        help_text=_("This field is unused and will be removed in a future "
                    "version."))

    # Set this up with a ReviewManager to help prevent race conditions and
    # to fix duplicate reviews.
    objects = ReviewManager()

    @cached_property
    def ship_it_only(self):
        """Return if the review only contains a "Ship It!".

        Returns:
            bool: ``True`` if the review is only a "Ship It!" and ``False``
            otherwise.
        """
        return (self.ship_it and
                (not self.body_top or
                 self.body_top == Review.SHIP_IT_TEXT) and
                not (self.body_bottom or
                     self.comments.exists() or
                     self.file_attachment_comments.exists() or
                     self.screenshot_comments.exists()))

    def get_participants(self):
        """Returns a list of participants in a review's discussion."""
        # This list comprehension gives us every user in every reply,
        # recursively.  It looks strange and perhaps backwards, but
        # works. We do it this way because get_participants gives us a
        # list back, which we can't stick in as the result for a
        # standard list comprehension. We could opt for a simple for
        # loop and concetenate the list, but this is more fun.
        return [self.user] + \
               [u for reply in self.replies.all()
                for u in reply.participants]

    participants = property(get_participants)

    def is_accessible_by(self, user):
        """Returns whether the user can access this review."""
        return ((self.public or self.user == user or user.is_superuser) and
                self.review_request.is_accessible_by(user))

    def is_mutable_by(self, user):
        """Returns whether the user can modify this review."""
        return ((not self.public and
                 (self.user == user or user.is_superuser)) and
                self.review_request.is_accessible_by(user))

    def __str__(self):
        return "Review of '%s'" % self.review_request

    def is_reply(self):
        """Returns whether or not this review is a reply to another review."""
        return self.base_reply_to_id is not None
    is_reply.boolean = True

    def public_replies(self):
        """Returns a list of public replies to this review."""
        return self.replies.filter(public=True)

    def public_body_top_replies(self, user=None):
        """Returns a list of public replies to this review's body top."""
        if hasattr(self, '_body_top_replies'):
            return self._body_top_replies
        else:
            q = Q(public=True)

            if user:
                q = q | Q(user=user)

            return self.body_top_replies.filter(q)

    def public_body_bottom_replies(self, user=None):
        """Returns a list of public replies to this review's body bottom."""
        if hasattr(self, '_body_bottom_replies'):
            return self._body_bottom_replies
        else:
            q = Q(public=True)

            if user:
                q = q | Q(user=user)

            return self.body_bottom_replies.filter(q)

    def get_pending_reply(self, user):
        """Returns the pending reply owned by the specified user."""
        if user.is_authenticated():
            return get_object_or_none(Review,
                                      user=user,
                                      public=False,
                                      base_reply_to=self)

        return None

    def save(self, **kwargs):
        self.timestamp = timezone.now()

        super(Review, self).save()

    def publish(self, user=None):
        """Publishes this review.

        This will make the review public and update the timestamps of all
        contained comments.
        """
        if not user:
            user = self.user

        self.public = True

        if self.is_reply():
            reply_publishing.send(sender=self.__class__, user=user, reply=self)
        else:
            review_publishing.send(sender=self.__class__, user=user,
                                   review=self)

        self.save()

        self.comments.update(timestamp=self.timestamp)
        self.screenshot_comments.update(timestamp=self.timestamp)
        self.file_attachment_comments.update(timestamp=self.timestamp)

        # Update the last_updated timestamp and the last review activity
        # timestamp on the review request.
        self.review_request.last_review_activity_timestamp = self.timestamp
        self.review_request.save(
            update_fields=['last_review_activity_timestamp', 'last_updated'])

        if self.is_reply():
            reply_published.send(sender=self.__class__,
                                 user=user, reply=self)
        else:
            issue_counts = fetch_issue_counts(self.review_request,
                                              Q(pk=self.pk))

            # Since we're publishing the review, all filed issues should be
            # open.
            assert issue_counts[BaseComment.RESOLVED] == 0
            assert issue_counts[BaseComment.DROPPED] == 0

            if self.ship_it:
                ship_it_value = 1
            else:
                ship_it_value = 0

            # Atomically update the issue count and Ship It count.
            CounterField.increment_many(
                self.review_request,
                {
                    'issue_open_count': issue_counts[BaseComment.OPEN],
                    'issue_dropped_count': 0,
                    'issue_resolved_count': 0,
                    'shipit_count': ship_it_value,
                })

            review_published.send(sender=self.__class__,
                                  user=user, review=self)

    def delete(self):
        """Deletes this review.

        This will enforce that all contained comments are also deleted.
        """
        self.comments.all().delete()
        self.screenshot_comments.all().delete()
        self.file_attachment_comments.all().delete()

        super(Review, self).delete()

    def get_absolute_url(self):
        return "%s#review%s" % (self.review_request.get_absolute_url(),
                                self.pk)

    def get_all_comments(self, **kwargs):
        """Return a list of all contained comments of all types."""
        return (list(self.comments.filter(**kwargs)) +
                list(self.screenshot_comments.filter(**kwargs)) +
                list(self.file_attachment_comments.filter(**kwargs)))

    class Meta:
        app_label = 'reviews'
        ordering = ['timestamp']
        get_latest_by = 'timestamp'
        verbose_name = _('review')
        verbose_name_plural = _('reviews')
