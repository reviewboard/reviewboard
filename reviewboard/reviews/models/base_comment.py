from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import CounterField, JSONField
from djblets.db.managers import ConcurrencyManager

from reviewboard.admin.read_only import is_site_read_only_for


@python_2_unicode_compatible
class BaseComment(models.Model):
    """The base class for all comment types."""

    OPEN = 'O'
    RESOLVED = 'R'
    DROPPED = 'D'
    VERIFYING_RESOLVED = 'A'
    VERIFYING_DROPPED = 'B'

    ISSUE_STATUSES = (
        (OPEN, _('Open')),
        (RESOLVED, _('Resolved')),
        (DROPPED, _('Dropped')),
        (VERIFYING_RESOLVED, _('Waiting for verification to resolve')),
        (VERIFYING_DROPPED, _('Waiting for verification to drop')),
    )

    ISSUE_STATUS_TO_STRING = {
        OPEN: 'open',
        RESOLVED: 'resolved',
        DROPPED: 'dropped',
        VERIFYING_RESOLVED: 'verifying-resolved',
        VERIFYING_DROPPED: 'verifying-dropped',
    }

    ISSUE_STRING_TO_STATUS = {
        'open': OPEN,
        'resolved': RESOLVED,
        'dropped': DROPPED,
        'verifying-resolved': VERIFYING_RESOLVED,
        'verifying-dropped': VERIFYING_DROPPED,
    }

    issue_opened = models.BooleanField(_('Issue Opened'), default=False)
    issue_status = models.CharField(_('Issue Status'),
                                    max_length=1,
                                    choices=ISSUE_STATUSES,
                                    blank=True,
                                    null=True,
                                    db_index=True)

    reply_to = models.ForeignKey('self', blank=True, null=True,
                                 related_name='replies',
                                 verbose_name=_('Reply To'))
    timestamp = models.DateTimeField(_('Timestamp'), default=timezone.now)
    text = models.TextField(_('Comment Text'))
    rich_text = models.BooleanField(_('Rich Text'), default=False)

    extra_data = JSONField(null=True)

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

    @staticmethod
    def issue_status_to_string(status):
        """Return a string representation of the status field.

        Args:
            status (unicode):
                The value of the ``issue_status`` field.

        Returns:
            unicode:
            A string representation of the status used for the API and other
            interfaces.
        """
        try:
            return BaseComment.ISSUE_STATUS_TO_STRING[status]
        except KeyError:
            return ''

    @staticmethod
    def issue_string_to_status(status):
        """Return a DB representation of the given status string.

        Args:
            status (unicode):
                The status string to convert.

        Returns:
            unicode:
            A value suitable for storing in the ``issue_status`` field.
        """
        try:
            return BaseComment.ISSUE_STRING_TO_STATUS[status]
        except KeyError:
            raise Exception('Invalid issue status "%s"' % status)

    def _get_require_verification(self):
        return self.extra_data.get('require_verification', False)

    def _set_require_verification(self, value):
        if not isinstance(value, bool):
            raise ValueError('require_verification must be a bool')

        self.extra_data['require_verification'] = value

    require_verification = property(
        _get_require_verification, _set_require_verification,
        doc='Whether this comment requires verification before closing.')

    def __init__(self, *args, **kwargs):
        """Initialize the comment.

        Args:
            *args (tuple):
                Positional arguments to pass through to the model
                initialization.

            **kwargs (dict):
                Keyword arguments to pass through to the model
                initialization.
        """
        super(BaseComment, self).__init__(*args, **kwargs)

        self._loaded_issue_status = self.issue_status

    def get_review_request(self):
        """Return this comment's review request.

        Returns:
            reviewboard.reviews.models.review_request.ReviewRequest:
            The review request that this comment was made on.
        """
        if hasattr(self, '_review_request'):
            return self._review_request
        else:
            return self.get_review().review_request

    def get_review(self):
        """Return this comment's review.

        Returns:
            reviewboard.reviews.models.review.Review:
            The review containing this comment.
        """
        if hasattr(self, '_review'):
            return self._review
        else:
            return self.review.get()

    def get_review_url(self):
        """Return the URL to view this comment.

        Returns:
            unicode:
            The absolute URL to view this comment in the web UI.
        """
        return '%s#%s%d' % (self.get_review_request().get_absolute_url(),
                            self.anchor_prefix, self.id)

    def is_reply(self):
        """Return whether this comment is a reply to another comment.

        Returns:
            bool:
            True if the comment is a reply.
        """
        return self.reply_to_id is not None
    is_reply.boolean = True

    def is_accessible_by(self, user):
        """Return whether the user can access this comment.

        Args:
            user (django.contrib.auth.models.User):
                The user being checked.

        Returns:
            bool:
            True if the given user can access this comment.
        """
        return self.get_review().is_accessible_by(user)

    def is_mutable_by(self, user):
        """Return whether the user can modify this comment.

        Args:
            user (django.contrib.auth.models.User):
                The user being checked.

        Returns:
            bool:
            True if the given user can modify this comment.
        """
        return self.get_review().is_mutable_by(user)

    def public_replies(self, user=None):
        """Return the public replies to this comment.

        Args:
            user (django.contrib.auth.models.User, optional):
                A user to filter by, if desired. If specified, only replies
                authored by this user will be returned.

        Returns:
            list of reviewboard.reviews.models.base_comment.BaseComment:
            The public replies to this comment.
        """
        if hasattr(self, '_replies'):
            return self._replies

        if user and user.is_authenticated():
            return self.replies.filter(Q(review__public=True) |
                                       Q(review__user=user))
        else:
            return self.replies.filter(review__public=True)

    def can_change_issue_status(self, user):
        """Return whether the user can change the issue status.

        Currently, this is allowed for:
        - The user who owns the review request.
        - The user who opened the issue (posted the comment).

        Args:
            user (django.contrib.auth.models.User):
                The user being checked.

        Returns:
            bool:
            True if the given user is allowed to change the issue status.
        """
        if not (user and user.is_authenticated()):
            return False

        return ((self.get_review_request().is_mutable_by(user) or
                 user.pk == self.get_review().user_id) and
                not is_site_read_only_for(user))

    def can_verify_issue_status(self, user):
        """Return whether the user can verify the issue status.

        Currently this is allowed for:

        - The user who opened the issue.
        - Administrators.

        Args:
            user (django.contrib.auth.models.User):
                The user being checked.

        Returns:
            bool:
            True if the given user is allowed to verify the issue status.
        """
        if not (user and user.is_authenticated()):
            return False

        review = self.get_review()
        local_site = review.review_request.local_site

        return (user.is_superuser or
                user.pk == review.user_id or
                (local_site and local_site.is_mutable_by(user)))

    def save(self, **kwargs):
        """Save the comment.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the method (unused).
        """
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

                    if old_field != new_field:
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
        """Return a string representation of the comment.

        Returns:
            unicode:
            A string representation of the comment.
        """
        return self.text

    class Meta:
        abstract = True
        app_label = 'reviews'
        ordering = ['timestamp']
