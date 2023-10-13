"""Model for a review request draft."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from django.contrib.auth.models import User
from django.db import models
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from djblets.db.fields import ModificationTimestampField, RelationCounterField
from djblets.db.managers import ConcurrencyManager

from reviewboard.attachments.models import FileAttachment
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.errors import NotModifiedError, PublishError
from reviewboard.reviews.fields import get_review_request_fields
from reviewboard.reviews.models.group import Group
from reviewboard.reviews.models.base_review_request_details import \
    BaseReviewRequestDetails
from reviewboard.reviews.models.review_request import ReviewRequest
from reviewboard.reviews.models.screenshot import Screenshot
from reviewboard.reviews.signals import review_request_published
from reviewboard.scmtools.errors import InvalidChangeNumberError

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager
    from reviewboard.attachments.models import FileAttachmentSequence
    from reviewboard.reviews.models.review_request import (
        FileAttachmentState,
        ReviewRequestFileAttachmentsData)
    from reviewboard.scmtools.core import ChangeSet


class ReviewRequestDraft(BaseReviewRequestDetails):
    """A draft of a review request.

    When a review request is being modified, a special draft copy of it is
    created containing all the details of the review request. This copy can
    be modified and eventually saved or discarded. When saved, the new
    details are copied back over to the originating ReviewRequest.
    """
    summary = models.CharField(
        _('summary'),
        max_length=BaseReviewRequestDetails.MAX_SUMMARY_LENGTH)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('owner'),
        null=True,
        related_name='draft')
    review_request = models.ForeignKey(
        ReviewRequest,
        on_delete=models.CASCADE,
        related_name='draft',
        verbose_name=_('review request'),
        unique=True)
    last_updated = ModificationTimestampField(
        _('last updated'))
    diffset = models.ForeignKey(
        DiffSet,
        on_delete=models.CASCADE,
        verbose_name=_('diff set'),
        blank=True,
        null=True,
        related_name='review_request_draft')
    changedesc = models.ForeignKey(
        ChangeDescription,
        on_delete=models.CASCADE,
        verbose_name=_('change description'),
        blank=True,
        null=True)
    target_groups = models.ManyToManyField(
        Group,
        related_name='drafts',
        verbose_name=_('target groups'),
        blank=True)
    target_people = models.ManyToManyField(
        User,
        verbose_name=_('target people'),
        related_name='directed_drafts',
        blank=True)
    screenshots = models.ManyToManyField(
        Screenshot,
        related_name='drafts',
        verbose_name=_('screenshots'),
        blank=True)
    inactive_screenshots = models.ManyToManyField(
        Screenshot,
        verbose_name=_('inactive screenshots'),
        related_name='inactive_drafts',
        blank=True)

    file_attachments = models.ManyToManyField(
        FileAttachment,
        related_name='drafts',
        verbose_name=_('file attachments'),
        blank=True)
    inactive_file_attachments = models.ManyToManyField(
        FileAttachment,
        verbose_name=_('inactive files'),
        related_name='inactive_drafts',
        blank=True)

    submitter = property(lambda self: self.owner or
                         self.review_request.owner)
    repository = property(lambda self: self.review_request.repository)
    local_site = property(lambda self: self.review_request.local_site)

    depends_on = models.ManyToManyField('ReviewRequest',
                                        blank=True,
                                        verbose_name=_('Dependencies'),
                                        related_name='draft_blocks')

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

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

    commit = property(lambda self: self.commit_id,
                      lambda self, value: setattr(self, 'commit_id', value))

    def get_latest_diffset(self):
        """Returns the diffset for this draft."""
        return self.diffset

    def is_accessible_by(self, user):
        """Returns whether or not the user can access this draft."""
        return self.is_mutable_by(user)

    def is_mutable_by(self, user):
        """Returns whether or not the user can modify this draft."""
        return self.review_request.is_mutable_by(user)

    def get_file_attachments_data(
        self,
        *,
        active_attachments: Optional[FileAttachmentSequence] = None,
        inactive_attachments: Optional[FileAttachmentSequence] = None,
        draft_active_attachments: Optional[FileAttachmentSequence] = None,
        draft_inactive_attachments: Optional[FileAttachmentSequence] = None,
        **kwargs,
    ) -> ReviewRequestFileAttachmentsData:
        """Return data about a review request and its draft's file attachments.

        This returns sets of the active and inactive file attachment IDs
        that are attached to the review request or its draft. This data is
        used in :py:meth:`ReviewRequest.get_file_attachment_state()
        <reviewboard.reviews.models.review_request.ReviewRequest
        .get_file_attachment_state>`.

        The active and inactive file attachments on the review request and its
        draft may be passed in to avoid fetching them again if they've already
        been fetched elsewhere.

        The returned data will be cached for future lookups.

        Version Added:
            6.0

        Args:
            active_attachments (list, optional):
                The list of active file attachments on the review request.

            inactive_attachments (list, optional):
                The list of inactive file attachments on the review request.

            draft_active_attachments (list, optional):
                The list of active file attachments on the review request
                draft.

            draft_inactive_attachments (list, optional):
                The list of inactive file attachments on the review request
                draft.

        Returns:
            ReviewRequestFileAttachmentsData:
                The data about the file attachments on a review request and
                its draft.
        """
        return self.get_review_request().get_file_attachments_data(
            active_attachments=active_attachments,
            inactive_attachments=inactive_attachments,
            draft_active_attachments=draft_active_attachments,
            draft_inactive_attachments=draft_inactive_attachments)

    def get_file_attachment_state(
        self,
        file_attachment: FileAttachment,
    ) -> FileAttachmentState:
        """Get the state of a file attachment attached to this review request.

        Version Added:
            6.0

        Args:
            file_attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment whose state will be returned.

        Returns:
            FileAttachmentState:
            The file attachment state.
        """
        return self.get_review_request().get_file_attachment_state(
            file_attachment)

    @staticmethod
    def create(review_request, changedesc=None):
        """Create a draft based on a review request.

        This will copy over all the details of the review request that
        we care about. If a draft already exists for the review request,
        the draft will be returned.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request to fetch or create the draft from.

            changedesc (reviewboard.changedescs.models.ChangeDescription):
                A custom change description to set on the draft. This will
                always be set, overriding any previous one if already set.

        Returns:
            ReviewRequestDraft:
            The resulting draft.
        """
        draft, draft_is_new = \
            ReviewRequestDraft.objects.get_or_create(
                review_request=review_request,
                defaults={
                    'changedesc': changedesc,
                    'extra_data': review_request.extra_data or {},
                    'summary': review_request.summary,
                    'description': review_request.description,
                    'testing_done': review_request.testing_done,
                    'bugs_closed': review_request.bugs_closed,
                    'branch': review_request.branch,
                    'description_rich_text':
                        review_request.description_rich_text,
                    'testing_done_rich_text':
                        review_request.testing_done_rich_text,
                    'rich_text': review_request.rich_text,
                    'commit_id': review_request.commit_id,
                })

        if (changedesc is None and
            draft.changedesc_id is None and
            review_request.public):
            changedesc = ChangeDescription.objects.create()

        if changedesc is not None and draft.changedesc_id != changedesc.pk:
            old_changedesc_id = draft.changedesc_id
            draft.changedesc = changedesc
            draft.save(update_fields=('changedesc',))

            if old_changedesc_id is not None:
                ChangeDescription.objects.filter(pk=old_changedesc_id).delete()

        if draft_is_new:
            rels_to_update = [
                ('depends_on', 'to_reviewrequest_id', 'from_reviewrequest_id'),
                ('target_groups', 'group_id', 'reviewrequest_id'),
                ('target_people', 'user_id', 'reviewrequest_id'),
            ]

            if review_request.screenshots_count > 0:
                review_request.screenshots.update(draft_caption=F('caption'))
                rels_to_update.append(('screenshots', 'screenshot_id',
                                       'reviewrequest_id'))

            if review_request.inactive_screenshots_count > 0:
                review_request.inactive_screenshots.update(
                    draft_caption=F('caption'))
                rels_to_update.append(('inactive_screenshots', 'screenshot_id',
                                       'reviewrequest_id'))

            if review_request.file_attachments_count > 0:
                review_request.file_attachments.update(
                    draft_caption=F('caption'))
                rels_to_update.append(('file_attachments', 'fileattachment_id',
                                       'reviewrequest_id'))

            if review_request.inactive_file_attachments_count > 0:
                review_request.inactive_file_attachments.update(
                    draft_caption=F('caption'))
                rels_to_update.append(('inactive_file_attachments',
                                       'fileattachment_id',
                                       'reviewrequest_id'))

            for rel_field, id_field, lookup_field, in rels_to_update:
                # We don't need to query the entirety of each object, and
                # we'd like to avoid any JOINs. So, we'll be using the
                # M2M 'through' tables to perform lookups of the related
                # models' IDs.
                items = list(
                    getattr(review_request, rel_field).through.objects
                    .filter(**{lookup_field: review_request.pk})
                    .values_list(id_field, flat=True)
                )

                if items:
                    # Note that we're using add() instead of directly
                    # assigning the value. This lets us avoid a query that
                    # Django would perform to determine if it needed to clear
                    # out any existing values. Since we know this draft is
                    # new, there's no point in doing that.
                    getattr(draft, rel_field).add(*items)

        return draft

    def publish(
        self,
        review_request: Optional[ReviewRequest] = None,
        user: Optional[User] = None,
        trivial: bool = False,
        send_notification: bool = True,
        validate_fields: bool = True,
        timestamp: Optional[datetime] = None,
    ) -> ChangeDescription:
        """Publish this draft.

        This is an internal method. Programmatic publishes should use
        :py:meth:`reviewboard.reviews.models.review_request.ReviewRequest.publish`
        instead.

        This updates and returns the draft's ChangeDescription, which
        contains the changed fields. This is used by the e-mail template
        to tell people what's new and interesting.

        The keys that may be saved in ``fields_changed`` in the
        ChangeDescription are:

        *  ``submitter``
        *  ``summary``
        *  ``description``
        *  ``testing_done``
        *  ``bugs_closed``
        *  ``depends_on``
        *  ``branch``
        *  ``target_groups``
        *  ``target_people``
        *  ``screenshots``
        *  ``screenshot_captions``
        *  ``diff``
        *  Any custom field IDs

        Each field in 'fields_changed' represents a changed field. This will
        save fields in the standard formats as defined by the
        'ChangeDescription' documentation, with the exception of the
        'screenshot_captions' and 'diff' fields.

        For the 'screenshot_captions' field, the value will be a dictionary
        of screenshot ID/dict pairs with the following fields:

        * ``old``: The old value of the field
        * ``new``: The new value of the field

        For the ``diff`` field, there is only ever an ``added`` field,
        containing the ID of the new diffset.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest, optional):
                The review request associated with this diff. If not provided,
                it will be looked up.

            user (django.contrib.auth.models.User, optional):
                The user publishing the draft. If not provided, this defaults
                to the review request submitter.

            trivial (bool, optional):
                Whether or not this is a trivial publish.

                Trivial publishes do not result in e-mail notifications.

            send_notification (bool, optional):
                Whether or not this will emit the
                :py:data:`reviewboard.reviews.signals.review_request_published`
                signal.

                This parameter is intended for internal use **only**.

            validate_fields (bool, optional):
                Whether or not the fields should be validated.

                This should only be ``False`` in the case of programmatic
                publishes, e.g., from close as submitted hooks.

            timestamp (datetime.datetime, optional):
                The datetime that should be used for all timestamps for objects
                published
                (:py:class:`~reviewboard.diffviewer.models.diff_set.DiffSet`,
                :py:class:`~reviewboard.changedescs.models.ChangeDescription`)
                over the course of the method.

        Returns:
            reviewboard.changedescs.models.ChangeDescription:
            The change description that results from this publish (if any).

            If this is an initial publish, there will be no change description
            (and this function will return ``None``).
        """
        if timestamp is None:
            timestamp = timezone.now()

        if not review_request:
            review_request = self.review_request

        assert review_request is not None

        if not self.changedesc and review_request.public:
            self.changedesc = ChangeDescription()

        changedesc = self.changedesc

        if not user:
            if changedesc:
                user = changedesc.get_user(self)
            else:
                user = review_request.submitter

        self.copy_fields_to_request(review_request)

        diffset = self.diffset

        # If no changes were made, raise exception and do not save
        if changedesc and not changedesc.has_modified_fields():
            raise NotModifiedError()

        if validate_fields:
            if not (self.target_groups.exists() or
                    self.target_people.exists()):
                raise PublishError(
                    gettext('There must be at least one reviewer before this '
                            'review request can be published.'))

            if not review_request.summary.strip():
                raise PublishError(
                    gettext('The draft must have a summary.'))

            if not review_request.description.strip():
                raise PublishError(
                    gettext('The draft must have a description.'))

            if (review_request.created_with_history and
                diffset and
                diffset.commit_count == 0):
                raise PublishError(
                    gettext('There are no commits attached to the diff.'))

        if diffset:
            if (review_request.created_with_history and not
                diffset.is_commit_series_finalized):
                raise PublishError(gettext(
                    'This commit series is not finalized.'))

            diffset.history = review_request.diffset_history
            diffset.timestamp = timestamp
            diffset.save(update_fields=('history', 'timestamp'))

        if changedesc:
            changedesc.user = user
            changedesc.timestamp = timestamp
            changedesc.public = True
            changedesc.save()
            review_request.changedescs.add(changedesc)

        review_request.description_rich_text = self.description_rich_text
        review_request.testing_done_rich_text = self.testing_done_rich_text
        review_request.rich_text = self.rich_text
        review_request.save()

        if send_notification:
            review_request_published.send(sender=type(review_request),
                                          user=user,
                                          review_request=review_request,
                                          trivial=trivial,
                                          changedesc=changedesc)

        return self.changedesc

    def update_from_commit_id(self, commit_id):
        """Update the data from a server-side changeset.

        If the commit ID refers to a pending changeset on an SCM which stores
        such things server-side (like Perforce), the details like the summary
        and description will be updated with the latest information.

        If the change number is the commit ID of a change which exists on the
        server, the summary and description will be set from the commit's
        message, and the diff will be fetched from the SCM.

        Args:
            commit_id (unicode):
                The commit ID or changeset ID that the draft will update
                from.

        Returns:
            list of unicode:
            The list of draft fields that have been updated from the commit.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                The hosting service backing the repository encountered an
                error.

            reviewboard.scmtools.errors.InvalidChangeNumberError:
                The commit ID could not be found in the repository.

            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            NotImplementedError:
                The repository does not support fetching information from
                commit IDs.
        """
        changeset = None

        if self.repository.supports_pending_changesets:
            scmtool = self.repository.get_scmtool()
            changeset = scmtool.get_changeset(commit_id, allow_empty=True)

        if changeset and changeset.pending:
            return self.update_from_pending_change(commit_id, changeset)
        elif self.repository.supports_post_commit:
            return self.update_from_committed_change(commit_id)
        else:
            if changeset:
                raise InvalidChangeNumberError()
            else:
                raise NotImplementedError()

    def update_from_pending_change(
        self,
        commit_id: str,
        changeset: ChangeSet,
    ) -> List[str]:
        """Update the data from a server-side pending changeset.

        This will fetch the metadata from the server and update the fields on
        the draft.

        Version Changed:
            6.0:
            Added support for setting ``extra_data``.

        Args:
            commit_id (str):
                The changeset ID that the draft will update from.

            changeset (reviewboard.scmtools.core.ChangeSet):
                The changeset information to update from.

        Returns:
            list of str:
            The list of draft fields that have been updated from the change.

        Raises:
            reviewboard.scmtools.errors.InvalidChangeNumberError:
                A changeset could not be found.
        """
        if not changeset:
            raise InvalidChangeNumberError()

        # If the SCM supports changesets, they should always include a number,
        # summary and description, parsed from the changeset description. Some
        # specialized systems may support the other fields, but we don't want
        # to clobber the user-entered values if they don't.
        self.commit = commit_id
        description = changeset.description
        testing_done = changeset.testing_done

        self.summary = changeset.summary
        self.description = description
        self.description_rich_text = False

        modified_fields = [
            'commit_id', 'summary', 'description', 'description_rich_text',
        ]

        if testing_done:
            self.testing_done = testing_done
            self.testing_done_rich_text = False
            modified_fields += ['testing_done', 'testing_done_rich_text']

        if changeset.branch:
            self.branch = changeset.branch
            modified_fields.append('branch')

        if changeset.bugs_closed:
            self.bugs_closed = ','.join(changeset.bugs_closed)
            modified_fields.append('bugs_closed')

        if changeset.extra_data:
            if self.extra_data is None:
                self.extra_data = {}

            self.extra_data.update(changeset.extra_data)
            modified_fields.append('extra_data')

        return modified_fields

    def update_from_committed_change(self, commit_id):
        """Update from a committed change present on the server.

        Fetches the commit message and diff from the repository and sets the
        relevant fields.

        Args:
            commit_id (unicode):
                The commit ID to update from.

        Returns:
            list of unicode:
            The list of draft fields that have been updated from the commit
            message.
        """
        commit = self.repository.get_change(commit_id)
        summary, message = commit.split_message()
        message = message.strip()

        self.commit = commit_id
        self.summary = summary.strip()

        self.description = message
        self.description_rich_text = False

        self.diffset = DiffSet.objects.create_from_data(
            repository=self.repository,
            diff_file_name='diff',
            diff_file_contents=commit.diff,
            parent_diff_file_name=None,
            parent_diff_file_contents=None,
            diffset_history=None,
            basedir='/',
            request=None,
            base_commit_id=commit.parent,
            check_existence=False)

        # Compute a suitable revision for the diffset.
        self.diffset.update_revision_from_history(
            self.review_request.diffset_history)
        self.diffset.save(update_fields=('revision',))

        return [
            'commit_id',
            'description',
            'description_rich_text',
            'diffset',
            'summary',
        ]

    def copy_fields_to_request(
        self,
        review_request: ReviewRequest,
    ) -> None:
        """Copy draft fields to the review request.

        This will loop through all fields on the review request, copying any
        changes from the draft to the review request, in preparation for a
        publish.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request to copy the fields to.
        """
        changedesc = self.changedesc

        for field_cls in get_review_request_fields():
            field = field_cls(review_request)

            if field.can_record_change_entry:
                old_value = field.load_value(review_request)
                new_value = field.load_value(self)

                if field.has_value_changed(old_value, new_value):
                    field.propagate_data(self)

                    if changedesc:
                        field.record_change_entry(changedesc,
                                                  old_value, new_value)

        # Screenshots and file attachments are a bit special. The list of
        # associated items can change, but so can captions within each.
        #
        # Fortunately, both of these types of models have near-identical
        # signatures, so we can reuse the same code for both.
        self._copy_attachments_to_review_request(
            changedesc=changedesc,
            changedesc_captions_field='screenshot_captions',
            changedesc_items_field='screenshots',
            changedesc_item_name_field='caption',
            review_request_models_active=review_request.screenshots,
            review_request_models_active_count=(
                review_request.screenshots_count),
            review_request_models_inactive=(
                review_request.inactive_screenshots),
            review_request_models_inactive_count=(
                review_request.inactive_screenshots_count),
            draft_models_active=self.screenshots,
            draft_models_active_count=self.screenshots_count,
            draft_models_inactive=self.inactive_screenshots,
            draft_models_inactive_count=self.inactive_screenshots_count)

        self._copy_attachments_to_review_request(
            changedesc=changedesc,
            changedesc_captions_field='file_captions',
            changedesc_items_field='files',
            changedesc_item_name_field='display_name',
            review_request_models_active=review_request.file_attachments,
            review_request_models_active_count=(
                review_request.file_attachments_count),
            review_request_models_inactive=(
                review_request.inactive_file_attachments),
            review_request_models_inactive_count=(
                review_request.inactive_file_attachments_count),
            draft_models_active=self.file_attachments,
            draft_models_active_count=self.file_attachments_count,
            draft_models_inactive=self.inactive_file_attachments,
            draft_models_inactive_count=self.inactive_file_attachments_count)

    def _copy_attachments_to_review_request(
        self,
        *,
        changedesc: Optional[ChangeDescription],
        changedesc_captions_field: str,
        changedesc_items_field: str,
        changedesc_item_name_field: str,
        review_request_models_active: RelatedManager,
        review_request_models_active_count: int,
        review_request_models_inactive: RelatedManager,
        review_request_models_inactive_count: int,
        draft_models_active: RelatedManager,
        draft_models_active_count: int,
        draft_models_inactive: RelatedManager,
        draft_models_inactive_count: int,
    ) -> None:
        """Copy over screenshots or file attachments to a review request.

        This takes care to copy over any screenshots/file attachments (as
        provided by the caller) from this draft to a review request. In the
        process, any changes to captions will be recorded in the change
        description.

        The logic attempts to minimize the number of database queries
        necessary to perform these updates.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description to update.

            changedesc_items_field (str):
                The field to set in the change description for any item
                changes.

            changedesc_captions_field (str):
                The field to set in the change description for any caption
                chagnes.

            changedesc_item_name_field (str):
                The name of the field representing the name of an item.

            review_request_models_active (django.db.models.manager.
                                          RelatedManager):
                The manager for the relation managing active items on the
                draft.

            review_request_models_active_count (int):
                The number of active items on the draft.

            review_request_models_inactive (django.db.models.manager.
                                            RelatedManager):
                The manager for the relation managing inactive items on the
                draft.

            review_request_models_inactive_count (int):
                The number of inactive items on the draft.

            draft_models_active (django.db.models.manager. RelatedManager):
                The manager for the relation managing active items on the
                draft.

            draft_models_active_count (int):
                The number of active items on the draft.

            draft_models_inactive (django.db.models.manager. RelatedManager):
                The manager for the relation managing inactive items on the
                draft.

            draft_models_inactive_count (int):
                The number of inactive items on the draft.
        """
        if (review_request_models_active_count > 0 or
            draft_models_active_count > 0):
            old_ids = set(
                review_request_models_active.values_list('pk', flat=True)
            )
            new_items = list(
                draft_models_active
                .only('pk', 'caption', 'draft_caption')
            )
            caption_changes = {}

            # Update the captions for each item. We won't be considering any
            # that were removed from the review request.
            for item in new_items:
                if item.caption != item.draft_caption:
                    if item.pk in old_ids:
                        caption_changes[item.pk] = {
                            'old': (item.caption,),
                            'new': (item.draft_caption,),
                        }

                    item.caption = item.draft_caption
                    item.save(update_fields=['caption'])

            if caption_changes and changedesc:
                changedesc.fields_changed[changedesc_captions_field] = \
                    caption_changes

            # If the list of IDs have changed, record the old/new items in the
            # change description, and then reset the list on the review request
            # to match the draft.
            new_ids = {
                item.pk
                for item in new_items
            }

            if new_ids.symmetric_difference(old_ids):
                if changedesc:
                    changedesc.record_field_change(
                        field=changedesc_items_field,
                        old_value=review_request_models_active.all(),
                        new_value=draft_models_active.all(),
                        name_field=changedesc_item_name_field)

                # Note that we explicitly want to clear this to preserve the
                # insertion order.
                review_request_models_active.set(draft_models_active.all(),
                                                 clear=True)

        if (review_request_models_inactive_count > 0 or
            draft_models_inactive_count > 0):
            # There's no change description entry required for this field.
            # We can just copy them.
            review_request_models_inactive.set(draft_models_inactive.all())

    def get_review_request(self):
        """Returns the associated review request."""
        return self.review_request

    class Meta:
        app_label = 'reviews'
        db_table = 'reviews_reviewrequestdraft'
        ordering = ['-last_updated']
        verbose_name = _('Review Request Draft')
        verbose_name_plural = _('Review Request Drafts')
