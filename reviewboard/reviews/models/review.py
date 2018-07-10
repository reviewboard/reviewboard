from __future__ import unicode_literals

import logging

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
from reviewboard.reviews.errors import RevokeShipItError
from reviewboard.reviews.managers import ReviewManager
from reviewboard.reviews.models.base_comment import BaseComment
from reviewboard.reviews.models.diff_comment import Comment
from reviewboard.reviews.models.file_attachment_comment import \
    FileAttachmentComment
from reviewboard.reviews.models.general_comment import GeneralComment
from reviewboard.reviews.models.review_request import (ReviewRequest,
                                                       fetch_issue_counts)
from reviewboard.reviews.models.screenshot_comment import ScreenshotComment
from reviewboard.reviews.signals import (reply_publishing, reply_published,
                                         review_publishing, review_published,
                                         review_ship_it_revoking,
                                         review_ship_it_revoked)


@python_2_unicode_compatible
class Review(models.Model):
    """A review of a review request."""

    # Constants used in e-mails when a review contains a Ship It designation.
    # These are explicitly not marked for localization to prevent taking the
    # submitting user's local into account when generating the e-mail.
    SHIP_IT_TEXT = 'Ship It!'
    REVOKED_SHIP_IT_TEXT = '~~Ship It!~~'
    FIX_IT_THEN_SHIP_IT_TEXT = 'Fix it, then Ship it!'

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
    general_comments = models.ManyToManyField(
        GeneralComment,
        verbose_name=_('general comments'),
        related_name='review',
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
                     self.has_comments(only_issues=False)))

    def can_user_revoke_ship_it(self, user):
        """Return whether a given user can revoke a Ship It.

        Args:
            user (django.contrib.auth.models.User):
                The user to check permissions for.

        Returns:
            bool:
            ``True`` if the user has permissions to revoke a Ship It.
            ``False`` if they don't.
        """
        return (user.is_authenticated() and
                self.public and
                (user.pk == self.user_id or
                 user.is_superuser or
                 (self.review_request.local_site and
                  self.review_request.local_site.admins.filter(
                      pk=user.pk).exists())) and
                self.review_request.is_accessible_by(user))

    def revoke_ship_it(self, user):
        """Revoke the Ship It status on this review.

        The Ship It status will be removed, and the
        :py:data:`ReviewRequest.shipit_count
        <reviewboard.reviews.models.review_request.ReviewRequest.shipit_count>`
        counter will be decremented.

        If the :py:attr:`body_top` text is equal to :py:attr:`SHIP_IT_TEXT`,
        then it will replaced with :py:attr:`REVOKED_SHIP_IT_TEXT`.

        Callers are responsible for checking whether the user has permission
        to revoke Ship Its by using :py:meth:`can_user_revoke_ship_it`.

        Raises:
            reviewboard.reviews.errors.RevokeShipItError:
                The Ship It could not be revoked. Details will be in the
                error message.
        """
        if not self.ship_it:
            raise RevokeShipItError('This review is not marked Ship It!')

        # This may raise a RevokeShipItError.
        try:
            review_ship_it_revoking.send(sender=self.__class__,
                                         user=user,
                                         review=self)
        except RevokeShipItError:
            raise
        except Exception as e:
            logging.exception('Unexpected error notifying listeners before '
                              'revoking a Ship It for review ID=%d: %s',
                              self.pk, e)
            raise RevokeShipItError(e)

        if self.extra_data is None:
            self.extra_data = {}

        self.extra_data['revoked_ship_it'] = True
        self.ship_it = False

        update_fields = ['extra_data', 'ship_it']

        if self.body_top == self.SHIP_IT_TEXT:
            self.body_top = self.REVOKED_SHIP_IT_TEXT
            self.body_top_rich_text = True
            update_fields += ['body_top', 'body_top_rich_text']

        self.save(update_fields=update_fields)

        self.review_request.decrement_shipit_count()
        self.review_request.last_review_activity_timestamp = timezone.now()
        self.review_request.save(
            update_fields=['last_review_activity_timestamp'])

        try:
            review_ship_it_revoked.send(sender=self.__class__,
                                        user=user,
                                        review=self)
        except Exception as e:
            logging.exception('Unexpected error notifying listeners after '
                              'revoking a Ship It for review ID=%d: %s',
                              self.pk, e)

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

    def is_new_for_user(self, user, last_visited):
        """Return whether this review is new for a user.

        The review is considered new if their last visited time is older than
        the review's published timestamp and the user is not the one who
        created the review.

        Args:
            user (django.contrib.auth.models.User):
                The user accessing the review.

            last_visited (datetime.datetime):
                The last time the user accessed a page where the review would
                be shown.

        Returns:
            bool:
            ``True`` if the review is new to this user. ``False`` if it's older
            than the last visited time or the user created it.
        """
        return user.pk != self.user_id and last_visited < self.timestamp

    def public_replies(self):
        """Returns a list of public replies to this review."""
        return self.replies.filter(public=True)

    def public_body_top_replies(self, user=None):
        """Returns a list of public replies to this review's body top."""
        if hasattr(self, '_body_top_replies'):
            return self._body_top_replies
        else:
            q = Q(public=True)

            if user and user.is_authenticated():
                q = q | Q(user=user)

            return self.body_top_replies.filter(q).order_by('timestamp')

    def public_body_bottom_replies(self, user=None):
        """Returns a list of public replies to this review's body bottom."""
        if hasattr(self, '_body_bottom_replies'):
            return self._body_bottom_replies
        else:
            q = Q(public=True)

            if user and user.is_authenticated():
                q = q | Q(user=user)

            return self.body_bottom_replies.filter(q).order_by('timestamp')

    def get_pending_reply(self, user):
        """Returns the pending reply owned by the specified user."""
        if user.is_authenticated():
            return get_object_or_none(Review,
                                      user=user,
                                      public=False,
                                      base_reply_to=self)

        return None

    def save(self, **kwargs):
        if ('update_fields' not in kwargs or
            'timestamp' in kwargs['update_fields']):
            self.timestamp = timezone.now()

        super(Review, self).save(**kwargs)

    def publish(self, user=None, trivial=False, to_owner_only=False,
                request=None):
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
        self.general_comments.update(timestamp=self.timestamp)

        # Update the last_updated timestamp and the last review activity
        # timestamp on the review request.
        self.review_request.last_review_activity_timestamp = self.timestamp
        self.review_request.last_updated = self.timestamp
        self.review_request.save(update_fields=(
            'last_review_activity_timestamp', 'last_updated'))

        if self.is_reply():
            reply_published.send(sender=self.__class__,
                                 user=user, reply=self, trivial=trivial)
        else:
            issue_counts = fetch_issue_counts(self.review_request,
                                              Q(pk=self.pk))

            # Since we're publishing the review, all filed issues should be
            # open.
            assert issue_counts[BaseComment.RESOLVED] == 0
            assert issue_counts[BaseComment.DROPPED] == 0
            assert issue_counts[BaseComment.VERIFYING_RESOLVED] == 0
            assert issue_counts[BaseComment.VERIFYING_DROPPED] == 0

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
                    'issue_verifying_count': 0,
                    'shipit_count': ship_it_value,
                })

            review_published.send(sender=self.__class__,
                                  user=user, review=self,
                                  to_owner_only=to_owner_only,
                                  request=request)

    def delete(self):
        """Deletes this review.

        This will enforce that all contained comments are also deleted.
        """
        self.comments.all().delete()
        self.screenshot_comments.all().delete()
        self.file_attachment_comments.all().delete()
        self.general_comments.all().delete()

        super(Review, self).delete()

    def get_absolute_url(self):
        return "%s#review%s" % (self.review_request.get_absolute_url(),
                                self.pk)

    def get_all_comments(self, **kwargs):
        """Return a list of all contained comments of all types."""
        return (list(self.comments.filter(**kwargs)) +
                list(self.screenshot_comments.filter(**kwargs)) +
                list(self.file_attachment_comments.filter(**kwargs)) +
                list(self.general_comments.filter(**kwargs)))

    def has_comments(self, only_issues=False):
        """Return whether the review contains any comments/issues.

        Args:
            only_issues (bool, optional):
                Whether or not to check for comments where ``issue_opened`` is
                ``True``. ``True`` to check for issues, or ``False`` to check
                for comments only. Defaults to ``False``.

        Returns:
            bool:
            ``True`` if the review contains any comments/issues and
            ``False`` otherwise.
        """
        qs = [
            self.comments,
            self.file_attachment_comments,
            self.screenshot_comments,
            self.general_comments,
        ]

        if only_issues:
            qs = [
                q.filter(issue_opened=True)
                for q in qs
            ]

        return any(q.exists() for q in qs)

    class Meta:
        app_label = 'reviews'
        db_table = 'reviews_review'
        ordering = ['timestamp']
        get_latest_by = 'timestamp'
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')
