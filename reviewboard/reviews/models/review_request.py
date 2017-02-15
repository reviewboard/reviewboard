from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Count, Q
from django.utils import six, timezone
from django.utils.translation import ugettext_lazy as _
from djblets.cache.backend import make_cache_key
from djblets.db.fields import CounterField, ModificationTimestampField
from djblets.db.query import get_object_or_none

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


def fetch_issue_counts(review_request, extra_query=None):
    """Fetches all issue counts for a review request.

    This queries all opened issues across all public comments on a
    review request and returns them.
    """
    issue_counts = {
        BaseComment.OPEN: 0,
        BaseComment.RESOLVED: 0,
        BaseComment.DROPPED: 0
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
        'screenshot_comments__pk',
        'screenshot_comments__issue_opened',
        'screenshot_comments__issue_status')

    if issue_statuses:
        comment_fields = {
            'comments': set(),
            'file_attachment_comments': set(),
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

        logging.debug('Calculated issue counts for review request ID %s '
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

    review_request.save(update_fields=[
        'issue_open_count',
        'issue_resolved_count',
        'issue_dropped_count'
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
                                        blank=True, null=True,
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

    local_site = models.ForeignKey(LocalSite, blank=True, null=True,
                                   related_name='review_requests')
    local_id = models.IntegerField('site-local ID', blank=True, null=True)

    # Set this up with the ReviewRequestManager
    objects = ReviewRequestManager()

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

    def get_participants(self):
        """Returns a list of users who have discussed this review request."""
        # See the comment in Review.get_participants for this list
        # comprehension.
        return [u for review in self.reviews.all()
                for u in review.participants]

    participants = property(get_participants)

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
                logging.warning('Review Request pk=%d (display_id=%d) is not '
                                'accessible by user %s because it has not yet '
                                'been published.',
                                self.pk, self.display_id, user,
                                request=request)

            return False

        if self.repository and not self.repository.is_accessible_by(user):
            if not silent:
                logging.warning('Review Request pk=%d (display_id=%d) is not '
                                'accessible by user %s because its repository '
                                'is not accessible by that user.',
                                self.pk, self.display_id, user,
                                request=request)

            return False

        if local_site and not local_site.is_accessible_by(user):
            if not silent:
                logging.warning('Review Request pk=%d (display_id=%d) is not '
                                'accessible by user %s because its local_site '
                                'is not accessible by that user.',
                                self.pk, self.display_id, user,
                                request=request)

            return False

        if (user.is_authenticated() and
            self.target_people.filter(pk=user.pk).count() > 0):
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
            logging.warning('Review Request pk=%d (display_id=%d) is not '
                            'accessible by user %s because they are not '
                            'directly listed as a reviewer, and none of '
                            'the target groups are accessible by that user.',
                            self.pk, self.display_id, user, request=request)

        return False

    def is_mutable_by(self, user):
        """Returns whether the user can modify this review request."""
        return (self.submitter == user or
                user.has_perm('reviews.can_edit_reviewrequest',
                              self.local_site))

    def is_status_mutable_by(self, user):
        """Returns whether the user can modify this review request's status."""
        return (self.submitter == user or
                user.has_perm('reviews.can_change_status', self.local_site))

    def is_deletable_by(self, user):
        """Returns whether the user can delete this review request."""
        return user.has_perm('reviews.delete_reviewrequest')

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

    def get_last_activity(self, diffsets=None, reviews=None):
        """Returns the last public activity information on the review request.

        This will return the last object updated, along with the timestamp
        of that object. It can be used to judge whether something on a
        review request has been made public more recently.
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

        return timestamp, updated_object

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

        scmtool = self.repository.get_scmtool()
        if (scmtool.supports_pending_changesets and
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
                    .annotate(file_count=Count('files'))
                    .prefetch_related('files'))

        return self._diffsets

    def get_latest_diffset(self):
        """Returns the latest diffset for this review request."""
        try:
            return DiffSet.objects.filter(
                history=self.diffset_history_id).latest()
        except DiffSet.DoesNotExist:
            return None

    def get_close_description(self):
        """Returns a tuple (description, is_rich_text) for the close text.

        This is a helper which is used to gather the data which is rendered in
        the close description boxes on various pages.
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

        return (close_description, is_rich_text)

    def get_blocks(self):
        """Returns the list of review request this one blocks.

        The returned value will be cached for future lookups.
        """
        if not hasattr(self, '_blocks'):
            self._blocks = list(self.blocks.all())

        return self._blocks

    def save(self, update_counts=False, **kwargs):
        if update_counts or self.id is None:
            self._update_counts()

        if self.status != self.PENDING_REVIEW:
            # If this is not a pending review request now, delete any
            # and all ReviewRequestVisit objects.
            self.visits.all().delete()

        super(ReviewRequest, self).save(**kwargs)

    def delete(self, **kwargs):
        from reviewboard.accounts.models import Profile, LocalSiteProfile

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=self.submitter)

        if profile_is_new:
            profile.save()

        local_site = self.local_site
        site_profile, site_profile_is_new = \
            LocalSiteProfile.objects.get_or_create(user=self.submitter,
                                                   profile=profile,
                                                   local_site=local_site)

        site_profile.decrement_total_outgoing_request_count()

        if self.status == self.PENDING_REVIEW:
            site_profile.decrement_pending_outgoing_request_count()

            if self.public:
                self._decrement_reviewer_counts()

        super(ReviewRequest, self).delete(**kwargs)

    def can_publish(self):
        return not self.public or get_object_or_none(self.draft) is not None

    def close(self, type, user=None, description=None, rich_text=False):
        """Closes the review request.

        The type must be one of SUBMITTED or DISCARDED.
        """
        if (user and not self.is_mutable_by(user) and
            not user.has_perm("reviews.can_change_status", self.local_site)):
            raise PermissionError

        if type not in [self.SUBMITTED, self.DISCARDED]:
            raise AttributeError("%s is not a valid close type" % type)

        review_request_closing.send(sender=self.__class__,
                                    user=user,
                                    review_request=self,
                                    type=type,
                                    description=description,
                                    rich_text=rich_text)

        draft = get_object_or_none(self.draft)

        if self.status != type:
            if (draft is not None and
                not self.public and type == self.DISCARDED):
                # Copy over the draft information if this is a private discard.
                draft.copy_fields_to_request(self)

            # TODO: Use the user's default for rich_text.
            changedesc = ChangeDescription(public=True,
                                           text=description or "",
                                           rich_text=rich_text or False)

            status_field = get_review_request_field('status')(self)
            status_field.record_change_entry(changedesc, self.status, type)
            changedesc.save()

            self.changedescs.add(changedesc)

            if type == self.SUBMITTED:
                if not self.public:
                    raise PublishError("The draft must be public first.")
            else:
                self.commit_id = None

            self.status = type
            self.save(update_counts=True)

            review_request_closed.send(sender=self.__class__, user=user,
                                       review_request=self,
                                       type=type,
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

            changedesc = ChangeDescription()
            status_field = get_review_request_field('status')(self)
            status_field.record_change_entry(changedesc, old_status,
                                             self.PENDING_REVIEW)

            if old_status == self.DISCARDED:
                # A draft is needed if reopening a discarded review request.
                self.public = False
                changedesc.save()
                draft = ReviewRequestDraft.create(self)
                draft.changedesc = changedesc
                draft.save()
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

    def publish(self, user, trivial=False):
        """Publishes the current draft attached to this review request.

        The review request will be mark as public, and signals will be
        emitted for any listeners.
        """
        if not self.is_mutable_by(user):
            raise PermissionError

        draft = get_object_or_none(self.draft)

        review_request_publishing.send(sender=self.__class__, user=user,
                                       review_request_draft=draft)

        # Decrement the counts on everything. we lose them.
        # We'll increment the resulting set during ReviewRequest.save.
        # This should be done before the draft is published.
        # Once the draft is published, the target people
        # and groups will be updated with new values.
        # Decrement should not happen while publishing
        # a new request or a discarded request
        if self.public:
            self._decrement_reviewer_counts()

        if draft is not None:
            # This will in turn save the review request, so we'll be done.
            try:
                changes = draft.publish(self, send_notification=False)
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

        if not self.public and self.changedescs.count() == 0:
            # This is a brand new review request that we're publishing
            # for the first time. Set the creation timestamp to now.
            self.time_added = timezone.now()

        self.public = True
        self.save(update_counts=True)

        review_request_published.send(sender=self.__class__, user=user,
                                      review_request=self, trivial=trivial,
                                      changedesc=changes)

    def _update_counts(self):
        from reviewboard.accounts.models import Profile, LocalSiteProfile

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=self.submitter)

        if profile_is_new:
            profile.save()

        local_site = self.local_site
        site_profile, site_profile_is_new = \
            LocalSiteProfile.objects.get_or_create(
                user=self.submitter,
                profile=profile,
                local_site=local_site)

        if site_profile_is_new:
            site_profile.save()

        if self.id is None:
            # This hasn't been created yet. Bump up the outgoing request
            # count for the user.
            site_profile.increment_total_outgoing_request_count()
            old_status = None
            old_public = False
        else:
            # We need to see if the status has changed, so that means
            # finding out what's in the database.
            r = ReviewRequest.objects.get(pk=self.id)
            old_status = r.status
            old_public = r.public

        if self.status == self.PENDING_REVIEW:
            if old_status != self.status:
                site_profile.increment_pending_outgoing_request_count()

            if self.public and self.id is not None:
                self._increment_reviewer_counts()
        elif old_status == self.PENDING_REVIEW:
            if old_status != self.status:
                site_profile.decrement_pending_outgoing_request_count()

            if old_public:
                self._decrement_reviewer_counts()

    def _increment_reviewer_counts(self):
        from reviewboard.accounts.models import LocalSiteProfile

        groups = self.target_groups.all()
        people = self.target_people.all()

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
        from reviewboard.accounts.models import LocalSiteProfile

        groups = self.target_groups.all()
        people = self.target_people.all()

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
                logging.error('Error when running ReviewRequestApprovalHook.'
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
        ordering = ['-last_updated', 'submitter', 'summary']
        unique_together = (('commit_id', 'repository'),
                           ('changenum', 'repository'),
                           ('local_site', 'local_id'))
        permissions = (
            ("can_change_status", "Can change status"),
            ("can_submit_as_another_user", "Can submit as another user"),
            ("can_edit_reviewrequest", "Can edit review request"),
        )
        verbose_name = _('review request')
        verbose_name_plural = _('review requests')
