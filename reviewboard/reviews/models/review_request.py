from __future__ import unicode_literals

import logging
import warnings

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Count, Q
from django.utils import six, timezone
from django.utils.translation import ugettext_lazy as _
from djblets.cache.backend import make_cache_key
from djblets.db.fields import (CounterField, ModificationTimestampField,
                               RelationCounterField)
from djblets.db.query import get_object_or_none
from djblets.deprecation import deprecated_arg_value

from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory
from reviewboard.reviews.errors import (PermissionError,
                                        PublishError)
from reviewboard.reviews.fields import get_review_request_field
from reviewboard.reviews.managers import ReviewRequestManager
from reviewboard.reviews.models.base_comment import BaseComment
from reviewboard.reviews.models.base_review_request_details import \
    BaseReviewRequestDetails
from reviewboard.reviews.models.group import Group
from reviewboard.reviews.models.screenshot import Screenshot
from reviewboard.reviews.signals import (review_request_closed,
                                         review_request_closing,
                                         review_request_published,
                                         review_request_publishing,
                                         review_request_reopened,
                                         review_request_reopening)
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


logger = logging.getLogger(__name__)


def fetch_issue_counts(review_request, extra_query=None):
    """Fetches all issue counts for a review request.

    This queries all opened issues across all public comments on a
    review request and returns them.
    """
    issue_counts = {
        BaseComment.OPEN: 0,
        BaseComment.RESOLVED: 0,
        BaseComment.DROPPED: 0,
        BaseComment.VERIFYING_RESOLVED: 0,
        BaseComment.VERIFYING_DROPPED: 0,
    }

    q = Q(public=True) & Q(base_reply_to__isnull=True)

    if extra_query:
        q = q & extra_query

    issue_statuses = review_request.reviews.filter(q).values(
        'comments__pk',
        'comments__issue_opened',
        'comments__issue_status',
        'file_attachment_comments__pk',
        'file_attachment_comments__issue_opened',
        'file_attachment_comments__issue_status',
        'general_comments__pk',
        'general_comments__issue_opened',
        'general_comments__issue_status',
        'screenshot_comments__pk',
        'screenshot_comments__issue_opened',
        'screenshot_comments__issue_status')

    if issue_statuses:
        comment_fields = {
            'comments': set(),
            'file_attachment_comments': set(),
            'general_comments': set(),
            'screenshot_comments': set(),
        }

        for issue_fields in issue_statuses:
            for key, comments in six.iteritems(comment_fields):
                issue_opened = issue_fields[key + '__issue_opened']
                comment_pk = issue_fields[key + '__pk']

                if issue_opened and comment_pk not in comments:
                    comments.add(comment_pk)
                    issue_status = issue_fields[key + '__issue_status']

                    if issue_status:
                        issue_counts[issue_status] += 1

        logger.debug('Calculated issue counts for review request ID %s '
                     'across %s review(s): Resulting counts = %r; '
                     'DB values = %r; Field IDs = %r',
                     review_request.pk, len(issue_statuses), issue_counts,
                     issue_statuses, comment_fields)

    return issue_counts


def _initialize_issue_counts(review_request):
    """Initializes the issue counter fields for a review request.

    This will fetch all the issue counts and populate the counter fields.

    Due to the way that CounterField works, this will only be called once
    per review request, instead of once per field, due to all the fields
    being set at once. This will also take care of the actual saving of
    fields, rather than leaving that up to CounterField, in order to save
    all at once,
    """
    if review_request.pk is None:
        return 0

    issue_counts = fetch_issue_counts(review_request)

    review_request.issue_open_count = issue_counts[BaseComment.OPEN]
    review_request.issue_resolved_count = issue_counts[BaseComment.RESOLVED]
    review_request.issue_dropped_count = issue_counts[BaseComment.DROPPED]
    review_request.issue_verifying_count = (
        issue_counts[BaseComment.VERIFYING_RESOLVED] +
        issue_counts[BaseComment.VERIFYING_DROPPED])

    review_request.save(update_fields=[
        'issue_open_count',
        'issue_resolved_count',
        'issue_dropped_count',
        'issue_verifying_count',
    ])

    # Tell CounterField not to set or save any values.
    return None


class ReviewRequest(BaseReviewRequestDetails):
    """A review request.

    This is one of the primary models in Review Board. Most everything
    is associated with a review request.

    The ReviewRequest model contains detailed information on a review
    request. Some fields are user-modifiable, while some are used for
    internal state.
    """

    _CREATED_WITH_HISTORY_EXTRA_DATA_KEY = '__created_with_history'

    PENDING_REVIEW = "P"
    SUBMITTED = "S"
    DISCARDED = "D"

    STATUSES = (
        (PENDING_REVIEW, _('Pending Review')),
        (SUBMITTED, _('Submitted')),
        (DISCARDED, _('Discarded')),
    )

    ISSUE_COUNTER_FIELDS = {
        BaseComment.OPEN: 'issue_open_count',
        BaseComment.RESOLVED: 'issue_resolved_count',
        BaseComment.DROPPED: 'issue_dropped_count',
        BaseComment.VERIFYING_RESOLVED: 'issue_verifying_count',
        BaseComment.VERIFYING_DROPPED: 'issue_verifying_count',
    }

    summary = models.CharField(
        _("summary"),
        max_length=BaseReviewRequestDetails.MAX_SUMMARY_LENGTH)

    submitter = models.ForeignKey(User, verbose_name=_("submitter"),
                                  related_name="review_requests")
    time_added = models.DateTimeField(_("time added"), default=timezone.now)
    last_updated = ModificationTimestampField(_("last updated"))
    status = models.CharField(_("status"), max_length=1, choices=STATUSES,
                              db_index=True)
    public = models.BooleanField(_("public"), default=False)
    changenum = models.PositiveIntegerField(_("change number"), blank=True,
                                            null=True, db_index=True)
    repository = models.ForeignKey(Repository,
                                   related_name="review_requests",
                                   verbose_name=_("repository"),
                                   null=True,
                                   blank=True)
    email_message_id = models.CharField(_("e-mail message ID"), max_length=255,
                                        blank=True, null=True)
    time_emailed = models.DateTimeField(_("time e-mailed"), null=True,
                                        default=None, blank=True)

    diffset_history = models.ForeignKey(DiffSetHistory,
                                        related_name="review_request",
                                        verbose_name=_('diff set history'),
                                        blank=True)
    target_groups = models.ManyToManyField(
        Group,
        related_name="review_requests",
        verbose_name=_("target groups"),
        blank=True)
    target_people = models.ManyToManyField(
        User,
        verbose_name=_("target people"),
        related_name="directed_review_requests",
        blank=True)
    screenshots = models.ManyToManyField(
        Screenshot,
        related_name="review_request",
        verbose_name=_("screenshots"),
        blank=True)
    inactive_screenshots = models.ManyToManyField(
        Screenshot,
        verbose_name=_("inactive screenshots"),
        help_text=_("A list of screenshots that used to be but are no "
                    "longer associated with this review request."),
        related_name="inactive_review_request",
        blank=True)

    file_attachments = models.ManyToManyField(
        FileAttachment,
        related_name="review_request",
        verbose_name=_("file attachments"),
        blank=True)
    inactive_file_attachments = models.ManyToManyField(
        FileAttachment,
        verbose_name=_("inactive file attachments"),
        help_text=_("A list of file attachments that used to be but are no "
                    "longer associated with this review request."),
        related_name="inactive_review_request",
        blank=True)
    file_attachment_histories = models.ManyToManyField(
        FileAttachmentHistory,
        related_name='review_request',
        verbose_name=_('file attachment histories'),
        blank=True)

    changedescs = models.ManyToManyField(
        ChangeDescription,
        verbose_name=_("change descriptions"),
        related_name="review_request",
        blank=True)

    depends_on = models.ManyToManyField('ReviewRequest',
                                        blank=True,
                                        verbose_name=_('Dependencies'),
                                        related_name='blocks')

    # Review-related information

    # The timestamp representing the last public activity of a review.
    # This includes publishing reviews and manipulating issues.
    last_review_activity_timestamp = models.DateTimeField(
        _("last review activity timestamp"),
        db_column='last_review_timestamp',
        null=True,
        default=None,
        blank=True)
    shipit_count = CounterField(_("ship-it count"), default=0)

    issue_open_count = CounterField(
        _('open issue count'),
        initializer=_initialize_issue_counts)

    issue_resolved_count = CounterField(
        _('resolved issue count'),
        initializer=_initialize_issue_counts)

    issue_dropped_count = CounterField(
        _('dropped issue count'),
        initializer=_initialize_issue_counts)

    issue_verifying_count = CounterField(
        _('verifying issue count'),
        initializer=_initialize_issue_counts)

    screenshots_count = RelationCounterField(
        'screenshots',
        verbose_name=_('screenshots count'))

    inactive_screenshots_count = RelationCounterField(
        'inactive_screenshots',
        verbose_name=_('inactive screenshots count'))

    file_attachments_count = RelationCounterField(
        'file_attachments',
        verbose_name=_('file attachments count'))

    inactive_file_attachments_count = RelationCounterField(
        'inactive_file_attachments',
        verbose_name=_('inactive file attachments count'))

    local_site = models.ForeignKey(LocalSite, blank=True, null=True,
                                   related_name='review_requests')
    local_id = models.IntegerField('site-local ID', blank=True, null=True)

    # Set this up with the ReviewRequestManager
    objects = ReviewRequestManager()

    @staticmethod
    def status_to_string(status):
        """Return a string representation of a review request status.

        Args:
            status (unicode):
                A single-character string representing the status.

        Returns:
            unicode:
            A longer string representation of the status suitable for use in
            the API.
        """
        if status == ReviewRequest.PENDING_REVIEW:
            return 'pending'
        elif status == ReviewRequest.SUBMITTED:
            return 'submitted'
        elif status == ReviewRequest.DISCARDED:
            return 'discarded'
        elif status is None:
            return 'all'
        else:
            raise ValueError('Invalid status "%s"' % status)

    @staticmethod
    def string_to_status(status):
        """Return a review request status from an API string.

        Args:
            status (unicode):
                A string from the API representing the status.

        Returns:
            unicode:
            A single-character string representing the status, suitable for
            storage in the ``status`` field.
        """
        if status == 'pending':
            return ReviewRequest.PENDING_REVIEW
        elif status == 'submitted':
            return ReviewRequest.SUBMITTED
        elif status == 'discarded':
            return ReviewRequest.DISCARDED
        elif status == 'all':
            return None
        else:
            raise ValueError('Invalid status string "%s"' % status)

    def get_commit(self):
        if self.commit_id is not None:
            return self.commit_id
        elif self.changenum is not None:
            self.commit_id = six.text_type(self.changenum)

            # Update the state in the database, but don't save this
            # model, or we can end up with some state (if we haven't
            # properly loaded everything yet). This affects docs.db
            # generation, and may cause problems in the wild.
            ReviewRequest.objects.filter(pk=self.pk).update(
                commit_id=six.text_type(self.changenum))

            return self.commit_id

        return None

    def set_commit(self, commit_id):
        try:
            self.changenum = int(commit_id)
        except (TypeError, ValueError):
            pass

        self.commit_id = commit_id

    commit = property(get_commit, set_commit)

    @property
    def approved(self):
        """Returns whether or not a review request is approved by reviewers.

        On a default installation, a review request is approved if it has
        at least one Ship It!, and doesn't have any open issues.

        Extensions may customize approval by providing their own
        ReviewRequestApprovalHook.
        """
        if not hasattr(self, '_approved'):
            self._calculate_approval()

        return self._approved

    @property
    def approval_failure(self):
        """Returns the error indicating why a review request isn't approved.

        If ``approved`` is ``False``, this will provide the text describing
        why it wasn't approved.

        Extensions may customize approval by providing their own
        ReviewRequestApprovalHook.
        """
        if not hasattr(self, '_approval_failure'):
            self._calculate_approval()

        return self._approval_failure

    @property
    def owner(self):
        """The owner of a review request.

        This is an alias for :py:attr:`submitter`. It provides compatibilty
        with :py:attr:`ReviewRequestDraft.owner
        <reviewboard.reviews.models.review_request_draft.ReviewRequestDraft.owner>`,
        for functions working with either method, and for review request
        fields, but it cannot be used for queries.
        """
        return self.submitter

    @owner.setter
    def owner(self, new_owner):
        self.submitter = new_owner

    @property
    def created_with_history(self):
        """Whether or not this review request was created with commit support.

        This property can only be changed before the review request is created
        (i.e., before :py:meth:`save` is called and it has a primary key
        assigned).
        """
        return (self.extra_data is not None and
                self.extra_data.get(self._CREATED_WITH_HISTORY_EXTRA_DATA_KEY,
                                    False))

    @created_with_history.setter
    def created_with_history(self, value):
        """Set whether this review request was created with commit support.

        This can only be used during review request creation (i.e., before
        :py:meth:`save` is called).

        Raises:
            ValueError:
                The review request has already been created.
        """
        if self.pk:
            raise ValueError('created_with_history cannot be changed once '
                             'the review request has been created.')

        if self.extra_data is None:
            self.extra_data = {}

        self.extra_data[self._CREATED_WITH_HISTORY_EXTRA_DATA_KEY] = value

    @property
    def review_participants(self):
        """Return the participants in reviews on the review request.

        This will contain the users who published any reviews or replies on the
        review request. The list will be in username sort order and will not
        contain duplicates.

        This will only contain the owner of the review request if they've filed
        a review or reply.

        Returns:
            set of django.contrib.auth.models.User:
            The users who filed reviews or replies.
        """
        user_ids = list(
            self.reviews
            .filter(public=True)
            .values_list('user_id', flat=True)
        )
        users = set()

        if user_ids:
            users.update(User.objects.filter(pk__in=user_ids))

        return users

    def get_new_reviews(self, user):
        """Returns all new reviews since last viewing this review request.

        This will factor in the time the user last visited the review request,
        and find any reviews that have been added or updated since.
        """
        if user.is_authenticated():
            # If this ReviewRequest was queried using with_counts=True,
            # then we should know the new review count and can use this to
            # decide whether we have anything at all to show.
            if hasattr(self, "new_review_count") and self.new_review_count > 0:
                query = self.visits.filter(user=user)

                try:
                    visit = query[0]

                    return self.reviews.filter(
                        public=True,
                        timestamp__gt=visit.timestamp).exclude(user=user)
                except IndexError:
                    # This visit doesn't exist, so bail.
                    pass

        return self.reviews.get_empty_query_set()

    def get_display_id(self):
        """Returns the ID that should be exposed to the user."""
        if self.local_site_id:
            return self.local_id
        else:
            return self.id

    display_id = property(get_display_id)

    def get_public_reviews(self):
        """Returns all public top-level reviews for this review request."""
        return self.reviews.filter(public=True, base_reply_to__isnull=True)

    def is_accessible_by(self, user, local_site=None, request=None,
                         silent=False):
        """Returns whether or not the user can read this review request.

        This performs several checks to ensure that the user has access.
        This user has access if:

        * The review request is public or the user can modify it (either
          by being an owner or having special permissions).

        * The repository is public or the user has access to it (either by
          being explicitly on the allowed users list, or by being a member
          of a review group on that list).

        * The user is listed as a requested reviewer or the user has access
          to one or more groups listed as requested reviewers (either by
          being a member of an invite-only group, or the group being public).
        """
        # Users always have access to their own review requests.
        if self.submitter == user:
            return True

        if not self.public and not self.is_mutable_by(user):
            if not silent:
                logger.warning('Review Request pk=%d (display_id=%d) is not '
                               'accessible by user %s because it has not yet '
                               'been published.',
                               self.pk, self.display_id, user,
                               request=request)

            return False

        if self.repository and not self.repository.is_accessible_by(user):
            if not silent:
                logger.warning('Review Request pk=%d (display_id=%d) is not '
                               'accessible by user %s because its repository '
                               'is not accessible by that user.',
                               self.pk, self.display_id, user,
                               request=request)

            return False

        if local_site and not local_site.is_accessible_by(user):
            if not silent:
                logger.warning('Review Request pk=%d (display_id=%d) is not '
                               'accessible by user %s because its local_site '
                               'is not accessible by that user.',
                               self.pk, self.display_id, user,
                               request=request)

            return False

        if (user.is_authenticated() and
            self.target_people.filter(pk=user.pk).exists()):
            return True

        groups = list(self.target_groups.all())

        if not groups:
            return True

        # We specifically iterate over these instead of making it part
        # of the query in order to keep the logic in Group, and to allow
        # for future expansion (extensions, more advanced policy)
        #
        # We're looking for at least one group that the user has access
        # to. If they can access any of the groups, then they have access
        # to the review request.
        for group in groups:
            if group.is_accessible_by(user, silent=silent):
                return True

        if not silent:
            logger.warning('Review Request pk=%d (display_id=%d) is not '
                           'accessible by user %s because they are not '
                           'directly listed as a reviewer, and none of '
                           'the target groups are accessible by that user.',
                           self.pk, self.display_id, user, request=request)

        return False

    def is_mutable_by(self, user):
        """Return whether the user can modify this review request.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            Whether the user can modify this review request.
        """
        return ((self.submitter == user or
                 user.has_perm('reviews.can_edit_reviewrequest',
                               self.local_site)) and
                not is_site_read_only_for(user))

    def is_status_mutable_by(self, user):
        """Return whether the user can modify this review request's status.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            Whether the user can modify this review request's status.
        """
        return ((self.submitter == user or
                 user.has_perm('reviews.can_change_status',
                               self.local_site)) and
                not is_site_read_only_for(user))

    def is_deletable_by(self, user):
        """Return whether the user can delete this review request.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            Whether the user can delete this review request.
        """
        return (user.has_perm('reviews.delete_reviewrequest') and
                not is_site_read_only_for(user))

    def get_draft(self, user=None):
        """Returns the draft of the review request.

        If a user is specified, than the draft will be returned only if owned
        by the user. Otherwise, None will be returned.
        """
        if not user:
            return get_object_or_none(self.draft)
        elif user.is_authenticated():
            return get_object_or_none(self.draft,
                                      review_request__submitter=user)

        return None

    def get_pending_review(self, user):
        """Returns the pending review owned by the specified user, if any.

        This will return an actual review, not a reply to a review.
        """
        from reviewboard.reviews.models.review import Review

        return Review.objects.get_pending_review(self, user)

    def get_last_activity_info(self, diffsets=None, reviews=None):
        """Return the last public activity information on the review request.

        Args:
            diffsets (list of reviewboard.diffviewer.models.DiffSet, optional):
                The list of diffsets to compare for latest activity.

                If not provided, this will be populated with the last diffset.

            reviews (list of reviewboard.reviews.models.Review, optional):
                The list of reviews to compare for latest activity.

                If not provided, this will be populated with the latest review.

        Returns:
            dict:
            A dictionary with the following keys:

            ``timestamp``:
                The :py:class:`~datetime.datetime` that the object was updated.

            ``updated_object``:
                The object that was updated. This will be one of the following:

                * The :py:class:`~reviewboard.reviews.models.ReviewRequest`
                  itself.
                * A :py:class:`~reviewboard.reviews.models.Review`.
                * A :py:class:`~reviewboard.diffviewer.models.DiffSet`.

            ``changedesc``:
                The latest
                :py:class:`~reviewboard.changedescs.models.ChangeDescription`,
                if any.
        """
        timestamp = self.last_updated
        updated_object = self

        # Check if the diff was updated along with this.
        if not diffsets and self.repository_id:
            latest_diffset = self.get_latest_diffset()
            diffsets = []

            if latest_diffset:
                diffsets.append(latest_diffset)

        if diffsets:
            for diffset in diffsets:
                if diffset.timestamp >= timestamp:
                    timestamp = diffset.timestamp
                    updated_object = diffset

        # Check for the latest review or reply.
        if not reviews:
            try:
                reviews = [self.reviews.filter(public=True).latest()]
            except ObjectDoesNotExist:
                reviews = []

        for review in reviews:
            if review.public and review.timestamp >= timestamp:
                timestamp = review.timestamp
                updated_object = review

        changedesc = None

        if updated_object is self or isinstance(updated_object, DiffSet):
            try:
                changedesc = self.changedescs.latest()
            except ChangeDescription.DoesNotExist:
                pass

        return {
            'changedesc': changedesc,
            'timestamp': timestamp,
            'updated_object': updated_object,
        }

    def changeset_is_pending(self, commit_id):
        """Returns whether the associated changeset is pending commit.

        For repositories that support it, this will return whether the
        associated changeset is pending commit. This requires server-side
        knowledge of the change.
        """
        cache_key = make_cache_key(
            'commit-id-is-pending-%d-%s' % (self.pk, commit_id))

        cached_values = cache.get(cache_key)
        if cached_values:
            return cached_values

        is_pending = False

        if (self.repository.supports_pending_changesets and
            commit_id is not None):
            changeset = scmtool.get_changeset(commit_id, allow_empty=True)

            if changeset:
                is_pending = changeset.pending

                new_commit_id = six.text_type(changeset.changenum)

                if commit_id != new_commit_id:
                    self.commit_id = new_commit_id
                    self.save(update_fields=['commit_id'])
                    commit_id = new_commit_id

                    draft = self.get_draft()
                    if draft:
                        draft.commit_id = new_commit_id
                        draft.save(update_fields=['commit_id'])

                # If the changeset is pending, we cache for only one minute to
                # speed things up a little bit when navigating through
                # different pages. If the changeset is no longer pending, cache
                # for the full default time.
                if is_pending:
                    cache.set(cache_key, (is_pending, commit_id), 60)
                else:
                    cache.set(cache_key, (is_pending, commit_id))

        return is_pending, commit_id

    def get_absolute_url(self):
        if self.local_site:
            local_site_name = self.local_site.name
        else:
            local_site_name = None

        return local_site_reverse(
            'review-request-detail',
            local_site_name=local_site_name,
            kwargs={'review_request_id': self.display_id})

    def get_diffsets(self):
        """Returns a list of all diffsets on this review request.

        This will also fetch all associated FileDiffs, as well as a count
        of the number of files (stored in DiffSet.file_count).
        """
        if not self.repository_id:
            return []

        if not hasattr(self, '_diffsets'):
            self._diffsets = list(
                DiffSet.objects
                .filter(history__pk=self.diffset_history_id)
                .prefetch_related('files'))

        return self._diffsets

    def get_latest_diffset(self):
        """Returns the latest diffset for this review request."""
        try:
            return DiffSet.objects.filter(
                history=self.diffset_history_id).latest()
        except DiffSet.DoesNotExist:
            return None

    def get_close_info(self):
        """Return metadata of the most recent closing of a review request.

        This is a helper which is used to gather the data which is rendered in
        the close description boxes on various pages.

        Returns:
            dict:
            A dictionary with the following keys:

            ``'close_description'`` (:py:class:`unicode`):
                Description of review request upon closing.

            ``'is_rich_text'`` (:py:class:`bool`):
                Boolean whether description is rich text.

            ``'timestamp'`` (:py:class:`datetime.datetime`):
                Time of review requests last closing.
        """
        # We're fetching all entries instead of just public ones because
        # another query may have already prefetched the list of
        # changedescs. In this case, a new filter() would result in more
        # queries.
        #
        # Realistically, there will only ever be at most a single
        # non-public change description (the current draft), so we
        # wouldn't be saving much of anything with a filter.
        changedescs = list(self.changedescs.all())
        latest_changedesc = None
        timestamp = None

        for changedesc in changedescs:
            if changedesc.public:
                latest_changedesc = changedesc
                break

        close_description = ''
        is_rich_text = False

        if latest_changedesc and 'status' in latest_changedesc.fields_changed:
            status = latest_changedesc.fields_changed['status']['new'][0]

            if status in (ReviewRequest.DISCARDED, ReviewRequest.SUBMITTED):
                close_description = latest_changedesc.text
                is_rich_text = latest_changedesc.rich_text
                timestamp = latest_changedesc.timestamp

        return {
            'close_description': close_description,
            'is_rich_text': is_rich_text,
            'timestamp': timestamp
        }

    def get_blocks(self):
        """Returns the list of review request this one blocks.

        The returned value will be cached for future lookups.
        """
        if not hasattr(self, '_blocks'):
            self._blocks = list(self.blocks.all())

        return self._blocks

    def save(self, update_counts=False, old_submitter=None, **kwargs):
        if update_counts or self.id is None:
            self._update_counts(old_submitter)

        if self.status != self.PENDING_REVIEW:
            # If this is not a pending review request now, delete any
            # and all ReviewRequestVisit objects.
            self.visits.all().delete()

        super(ReviewRequest, self).save(**kwargs)

    def delete(self, **kwargs):
        site_profile = self.submitter.get_site_profile(self.local_site)
        site_profile.decrement_total_outgoing_request_count()

        if self.status == self.PENDING_REVIEW:
            site_profile.decrement_pending_outgoing_request_count()

            if self.public:
                self._decrement_reviewer_counts()

        super(ReviewRequest, self).delete(**kwargs)

    def can_publish(self):
        return not self.public or get_object_or_none(self.draft) is not None

    def can_add_default_reviewers(self):
        """Return whether default reviewers can be added to the review request.

        Default reviewers can only be added if the review request supports
        repositories and doesn't yet have any published diffs.

        Returns:
            bool:
            ``True`` if new default reviewers can be added. ``False`` if they
            cannot.
        """
        if not self.repository_id or not self.diffset_history_id:
            return False

        return not (
            DiffSet.objects
            .filter(history=self.diffset_history_id)
            .exists()
        )

    def close(self, close_type=None, user=None, description=None,
              rich_text=False, **kwargs):
        """Closes the review request.

        Args:
            close_type (unicode):
                How the close occurs. This should be one of
                :py:attr:`SUBMITTED` or :py:attr:`DISCARDED`.

            user (django.contrib.auth.models.User):
                The user who is closing the review request.

            description (unicode):
                An optional description that indicates why the review request
                was closed.

            rich_text (bool):
                Indicates whether or not that the description is rich text.

        Raises:
            ValueError:
                The provided close type is not a valid value.

            PermissionError:
                The user does not have permission to close the review request.

            TypeError:
                Keyword arguments were supplied to the function.

        .. versionchanged:: 3.0
           The ``type`` argument is deprecated: ``close_type`` should be used
           instead.

           This method raises :py:exc:`ValueError` instead of
           :py:exc:`AttributeError` when the ``close_type`` has an incorrect
           value.
        """
        if close_type is None:
            try:
                close_type = kwargs.pop('type')
            except KeyError:
                raise AttributeError('close_type must be provided')

            warnings.warn(
                'The "type" argument was deprecated in Review Board 3.0 and '
                'will be removed in a future version. Use "close_type" '
                'instead.'
            )

        if kwargs:
            raise TypeError('close() does not accept keyword arguments.')

        if (user and not self.is_mutable_by(user) and
            not user.has_perm("reviews.can_change_status", self.local_site)):
            raise PermissionError

        if close_type not in [self.SUBMITTED, self.DISCARDED]:
            raise ValueError("%s is not a valid close type" % type)

        review_request_closing.send(
            sender=type(self),
            user=user,
            review_request=self,
            close_type=close_type,
            description=description,
            rich_text=rich_text)

        draft = get_object_or_none(self.draft)

        if self.status != close_type:
            if (draft is not None and
                not self.public and close_type == self.DISCARDED):
                # Copy over the draft information if this is a private discard.
                draft.copy_fields_to_request(self)

            # TODO: Use the user's default for rich_text.
            changedesc = ChangeDescription(public=True,
                                           text=description or "",
                                           rich_text=rich_text or False,
                                           user=user or self.submitter)

            status_field = get_review_request_field('status')(self)
            status_field.record_change_entry(changedesc, self.status,
                                             close_type)
            changedesc.save()

            self.changedescs.add(changedesc)

            if close_type == self.SUBMITTED:
                if not self.public:
                    raise PublishError("The draft must be public first.")
            else:
                self.commit_id = None

            self.status = close_type
            self.save(update_counts=True)

            review_request_closed.send(
                sender=type(self),
                user=user,
                review_request=self,
                close_type=close_type,
                description=description,
                rich_text=rich_text)
        else:
            # Update submission description.
            changedesc = self.changedescs.filter(public=True).latest()
            changedesc.timestamp = timezone.now()
            changedesc.text = description or ""
            changedesc.rich_text = rich_text
            changedesc.save()

            # Needed to renew last-update.
            self.save()

        # Delete the associated draft review request.
        if draft is not None:
            draft.delete()

    def reopen(self, user=None):
        """Reopens the review request for review."""
        from reviewboard.reviews.models.review_request_draft import \
            ReviewRequestDraft

        if (user and not self.is_mutable_by(user) and
            not user.has_perm("reviews.can_change_status", self.local_site)):
            raise PermissionError

        old_status = self.status
        old_public = self.public

        if old_status != self.PENDING_REVIEW:
            # The reopening signal is only fired when actually making a status
            # change since the main consumers (extensions) probably only care
            # about changes.
            review_request_reopening.send(sender=self.__class__,
                                          user=user,
                                          review_request=self)

            changedesc = ChangeDescription(user=user or self.submitter)
            status_field = get_review_request_field('status')(self)
            status_field.record_change_entry(changedesc, old_status,
                                             self.PENDING_REVIEW)

            if old_status == self.DISCARDED:
                # A draft is needed if reopening a discarded review request.
                self.public = False
                changedesc.save()
                ReviewRequestDraft.create(self, changedesc=changedesc)
            else:
                changedesc.public = True
                changedesc.save()
                self.changedescs.add(changedesc)

            self.status = self.PENDING_REVIEW
            self.save(update_counts=True)

        review_request_reopened.send(sender=self.__class__, user=user,
                                     review_request=self,
                                     old_status=old_status,
                                     old_public=old_public)

    def publish(self, user, trivial=False, validate_fields=True):
        """Publishes the current draft attached to this review request.

        The review request will be mark as public, and signals will be
        emitted for any listeners.
        """
        if not self.is_mutable_by(user):
            raise PermissionError

        draft = get_object_or_none(self.draft)
        old_submitter = self.submitter

        if (draft is not None and
            draft.owner is not None and
            old_submitter != draft.owner):
            # The owner will be changing, and there was an edge case (present
            # through Review Board 3.0.14) where, if the new owner didn't
            # have a LocalSiteProfile, we'd end up with bad incoming counts.
            #
            # The reason is that the creation of a new LocalSiteProfile in
            # that function resulted in counters that were populated by a
            # post-publish state, but before counters were incremented or
            # decremented. This caused a redundant increment/decrement at
            # times.
            #
            # We attempted in _update_counts() to deal with this for the
            # outgoing counts, carefully checking if it's a new profile,
            # but couldn't easily work around the varied states for incoming
            # counts. The simplest solution is to ensure a populated profile
            # before we begin messing with any counts (below) and before
            # publishing new state.
            #
            # Note that we only need to fetch the profile for what will be
            # the current owner after the publish has completed. That's why
            # we're fetching the draft owner here, or the old submitter in
            # the `else:` below, but not both.
            draft.owner.get_site_profile(self.local_site)
        else:
            # For good measure, we're going to also query this for the original
            # owner, if the owner has not changed. This prevents the same
            # sorts of problems from occurring in the event that a review
            # request has been created and published for a new user through
            # some means like the API or a script without that user having
            # a profile.
            old_submitter.get_site_profile(self.local_site)

        review_request_publishing.send(sender=self.__class__, user=user,
                                       review_request_draft=draft)

        # Decrement the counts on everything. We'll increment the resulting
        # set during _update_counts() (called from ReviewRequest.save()).
        # This must be done before the draft is published, or we'll end up
        # with bad counts.
        #
        # Once the draft is published, the target people and groups will be
        # updated with new values.
        if self.public:
            self._decrement_reviewer_counts()

        # Calculate the timestamp once and use it for all things that are
        # considered as happening now. If we do not do this, there will be
        # millisecond timestamp differences between review requests and their
        # changedescs, diffsets, and reviews.
        #
        # Keeping them in sync means that get_last_activity() can work as
        # intended. Otherwise, the review request will always have the most
        # recent timestamp since it gets saved last.
        timestamp = timezone.now()

        if draft is not None:
            # This will in turn save the review request, so we'll be done.
            try:
                changes = draft.publish(self,
                                        send_notification=False,
                                        user=user,
                                        validate_fields=validate_fields,
                                        timestamp=timestamp)
            except Exception:
                # The draft failed to publish, for one reason or another.
                # Check if we need to re-increment those counters we
                # previously decremented.
                if self.public:
                    self._increment_reviewer_counts()

                raise

            draft.delete()
        else:
            changes = None

        if not self.public and not self.changedescs.exists():
            # This is a brand new review request that we're publishing
            # for the first time. Set the creation timestamp to now.
            self.time_added = timestamp

        self.public = True
        self.last_updated = timestamp
        self.save(update_counts=True, old_submitter=old_submitter)

        review_request_published.send(sender=self.__class__, user=user,
                                      review_request=self, trivial=trivial,
                                      changedesc=changes)

    def determine_user_for_changedesc(self, changedesc):
        """Determine the user associated with the change description.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description.

        Returns:
            django.contrib.auth.models.User:
            The user associated with the change description.
        """
        if 'submitter' in changedesc.fields_changed:
            entry = changedesc.fields_changed['submitter']['old'][0]
            return User.objects.get(pk=entry[2])

        user_pk = None

        changes = (
            self.changedescs
            .filter(pk__lt=changedesc.pk)
            .order_by('-pk')
        )

        for changedesc in changes:
            if 'submitter' in changedesc.fields_changed:
                user_pk = changedesc.fields_changed['submitter']['new'][0][2]
                break

        if user_pk:
            return User.objects.get(pk=user_pk)

        return self.submitter

    def _update_counts(self, old_submitter):
        """Update the review request counters for affected users and groups.

        This will increment/decrement the outgoing counters on the
        :py:class:`~reviewboard.accounts.models.LocalSiteProfile` belonging
        to the review request owner, and the incoming counters on both
        review groups and profiles for users directly or indirectly assigned
        as reviewers.

        This is also careful to manage the outgoing counts for both old and
        new owners of a review request, if ownership has changed.

        Args:
            old_submitter (django.contrib.auth.models.User):
                The old submitter of a review request. This is impacted by
                the call to :py:meth:`save`, and is only expected to be set
                if saving during a :py:meth:`publish` operation. It will be
                ``None`` in other cases.
        """
        from reviewboard.accounts.models import LocalSiteProfile

        submitter_changed = (old_submitter is not None and
                             old_submitter != self.submitter)

        local_site = self.local_site
        site_profile = self.submitter.get_site_profile(local_site)

        if self.pk is None:
            # This is brand-new review request that hasn't yet been saved.
            # We won't have an existing review request to look up for the old
            # values (so we'll hard-code them), and we know the owner hasn't
            # changed. We can safely bump the outgoing review request count
            # for the owner.
            site_profile.increment_total_outgoing_request_count()
            old_status = None
            old_public = False
        else:
            # We're saving an existing review request. The status, public flag,
            # and owner may have changed, so check the original values in the
            # database and see.
            r = ReviewRequest.objects.only('status', 'public').get(pk=self.id)
            old_status = r.status
            old_public = r.public

            if submitter_changed:
                # The owner of the review request changed, so we'll need to
                # make sure to decrement the outgoing counts from the old
                # owner and increment for the new owner.
                #
                # The pending count is conditional based on the state of the
                # review request, but the total outgoing count is a permament
                # change. The old user is no longer responsible for this
                # review request and should never see it added to their count
                # again.
                site_profile.increment_total_outgoing_request_count()

                if self.status == self.PENDING_REVIEW:
                    site_profile.increment_pending_outgoing_request_count()

                try:
                    old_profile = old_submitter.get_site_profile(
                        local_site,
                        create_if_missing=False)
                    old_profile.decrement_total_outgoing_request_count()

                    if old_status == self.PENDING_REVIEW:
                        old_profile.decrement_pending_outgoing_request_count()
                except LocalSiteProfile.DoesNotExist:
                    # The old user didn't have a profile (they may no longer
                    # be on a Local Site, or the data may have been deleted).
                    # We can ignore this, since we won't need to alter any
                    # counters. If they ever get a profile, the initial values
                    # will be computed correctly.
                    pass

        if self.status == self.PENDING_REVIEW:
            if old_status != self.status and not submitter_changed:
                # The status of the review request has changed to Pending
                # Review, and we know we didn't take care of the value as
                # part of an ownership change. Increment the counter now.
                site_profile.increment_pending_outgoing_request_count()

            if self.public and self.id is not None:
                # This was either the first publish, or it's been reopened.
                # It's now ready for review. Increment the counters for
                # reviewers, so it shows up in their dashboards.
                self._increment_reviewer_counts()
        elif old_status == self.PENDING_REVIEW:
            if old_status != self.status and not submitter_changed:
                # The status of the review request has changed from Pending
                # Review (in other words, it's been closed), and we know we
                # didn't take care of the value as part of an ownership
                # change. Decrement the counter now.
                site_profile.decrement_pending_outgoing_request_count()

            if old_public:
                # We went from open to closed. Decrement the counters for
                # reviewers, so it's not showing up in their dashboards.
                self._decrement_reviewer_counts()

    def _increment_reviewer_counts(self):
        """Increment the counters for all reviewers.

        This will increment counters for all review groups and users that
        are marked as reviewers (directly or indirectly).
        """
        from reviewboard.accounts.models import LocalSiteProfile

        groups = self.target_groups.values_list('pk', flat=True)
        people = self.target_people.values_list('pk', flat=True)

        Group.incoming_request_count.increment(groups)
        LocalSiteProfile.direct_incoming_request_count.increment(
            LocalSiteProfile.objects.filter(user__in=people,
                                            local_site=self.local_site))
        LocalSiteProfile.total_incoming_request_count.increment(
            LocalSiteProfile.objects.filter(
                Q(local_site=self.local_site) &
                Q(Q(user__review_groups__in=groups) |
                  Q(user__in=people))))
        LocalSiteProfile.starred_public_request_count.increment(
            LocalSiteProfile.objects.filter(
                profile__starred_review_requests=self,
                local_site=self.local_site))

    def _decrement_reviewer_counts(self):
        """Decrement the counters for all reviewers.

        This will decrement counters for all review groups and users that
        are marked as reviewers (directly or indirectly).
        """
        from reviewboard.accounts.models import LocalSiteProfile

        groups = self.target_groups.values_list('pk', flat=True)
        people = self.target_people.values_list('pk', flat=True)

        Group.incoming_request_count.decrement(groups)
        LocalSiteProfile.direct_incoming_request_count.decrement(
            LocalSiteProfile.objects.filter(
                user__in=people,
                local_site=self.local_site))
        LocalSiteProfile.total_incoming_request_count.decrement(
            LocalSiteProfile.objects.filter(
                Q(local_site=self.local_site) &
                Q(Q(user__review_groups__in=groups) |
                  Q(user__in=people))))
        LocalSiteProfile.starred_public_request_count.decrement(
            LocalSiteProfile.objects.filter(
                profile__starred_review_requests=self,
                local_site=self.local_site))

    def _calculate_approval(self):
        """Calculates the approval information for the review request."""
        from reviewboard.extensions.hooks import ReviewRequestApprovalHook

        approved = True
        failure = None

        if self.shipit_count == 0:
            approved = False
            failure = 'The review request has not been marked "Ship It!"'
        elif self.issue_open_count > 0:
            approved = False
            failure = 'The review request has open issues.'
        elif self.issue_verifying_count > 0:
            approved = False
            failure = 'The review request has unverified issues.'

        for hook in ReviewRequestApprovalHook.hooks:
            try:
                result = hook.is_approved(self, approved, failure)

                if isinstance(result, tuple):
                    approved, failure = result
                elif isinstance(result, bool):
                    approved = result
                else:
                    raise ValueError('%r returned an invalid value %r from '
                                     'is_approved'
                                     % (hook, result))

                if approved:
                    failure = None
            except Exception as e:
                extension = hook.extension
                logger.error('Error when running ReviewRequestApprovalHook.'
                             'is_approved function in extension: "%s": %s',
                             extension.id, e, exc_info=1)

        self._approval_failure = failure
        self._approved = approved

    def get_review_request(self):
        """Returns this review request.

        This is provided so that consumers can be passed either a
        ReviewRequest or a ReviewRequestDraft and retrieve the actual
        ReviewRequest regardless of the object.
        """
        return self

    class Meta:
        app_label = 'reviews'
        db_table = 'reviews_reviewrequest'
        ordering = ['-last_updated', 'submitter', 'summary']
        unique_together = (('commit_id', 'repository'),
                           ('changenum', 'repository'),
                           ('local_site', 'local_id'))
        permissions = (
            ("can_change_status", "Can change status"),
            ("can_submit_as_another_user", "Can submit as another user"),
            ("can_edit_reviewrequest", "Can edit review request"),
        )
        verbose_name = _('Review Request')
        verbose_name_plural = _('Review Requests')
