from __future__ import unicode_literals

import copy

from django.contrib.auth.models import User
from django.db import models
from django.db.models import F
from django.utils import timezone
from django.utils.translation import ugettext, ugettext_lazy as _
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


class ReviewRequestDraft(BaseReviewRequestDetails):
    """A draft of a review request.

    When a review request is being modified, a special draft copy of it is
    created containing all the details of the review request. This copy can
    be modified and eventually saved or discarded. When saved, the new
    details are copied back over to the originating ReviewRequest.
    """
    summary = models.CharField(
        _("summary"),
        max_length=BaseReviewRequestDetails.MAX_SUMMARY_LENGTH)

    owner = models.ForeignKey(
        User,
        verbose_name=_('owner'),
        null=True,
        related_name='draft')
    review_request = models.ForeignKey(
        ReviewRequest,
        related_name="draft",
        verbose_name=_("review request"),
        unique=True)
    last_updated = ModificationTimestampField(
        _("last updated"))
    diffset = models.ForeignKey(
        DiffSet,
        verbose_name=_('diff set'),
        blank=True,
        null=True,
        related_name='review_request_draft')
    changedesc = models.ForeignKey(
        ChangeDescription,
        verbose_name=_('change description'),
        blank=True,
        null=True)
    target_groups = models.ManyToManyField(
        Group,
        related_name="drafts",
        verbose_name=_("target groups"),
        blank=True)
    target_people = models.ManyToManyField(
        User,
        verbose_name=_("target people"),
        related_name="directed_drafts",
        blank=True)
    screenshots = models.ManyToManyField(
        Screenshot,
        related_name="drafts",
        verbose_name=_("screenshots"),
        blank=True)
    inactive_screenshots = models.ManyToManyField(
        Screenshot,
        verbose_name=_("inactive screenshots"),
        related_name="inactive_drafts",
        blank=True)

    file_attachments = models.ManyToManyField(
        FileAttachment,
        related_name="drafts",
        verbose_name=_("file attachments"),
        blank=True)
    inactive_file_attachments = models.ManyToManyField(
        FileAttachment,
        verbose_name=_("inactive files"),
        related_name="inactive_drafts",
        blank=True)

    submitter = property(lambda self: self.owner or
                         self.review_request.owner)
    repository = property(lambda self: self.review_request.repository)
    local_site = property(lambda self: self.review_request.local_site)

    depends_on = models.ManyToManyField('ReviewRequest',
                                        blank=True, null=True,
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

    @staticmethod
    def create(review_request):
        """Creates a draft based on a review request.

        This will copy over all the details of the review request that
        we care about. If a draft already exists for the review request,
        the draft will be returned.
        """
        draft, draft_is_new = \
            ReviewRequestDraft.objects.get_or_create(
                review_request=review_request,
                defaults={
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

        if draft.changedesc is None and review_request.public:
            draft.changedesc = ChangeDescription.objects.create()
        if draft_is_new:
            draft.target_groups = review_request.target_groups.all()
            draft.target_people = review_request.target_people.all()
            draft.depends_on = review_request.depends_on.all()
            draft.extra_data = copy.deepcopy(review_request.extra_data)
            draft.save()

            if review_request.screenshots_count > 0:
                review_request.screenshots.update(draft_caption=F('caption'))
                draft.screenshots = review_request.screenshots.all()

            if review_request.inactive_screenshots_count > 0:
                review_request.inactive_screenshots.update(
                    draft_caption=F('caption'))
                draft.inactive_screenshots = \
                    review_request.inactive_screenshots.all()

            if review_request.file_attachments_count > 0:
                review_request.file_attachments.update(
                    draft_caption=F('caption'))
                draft.file_attachments = review_request.file_attachments.all()

            if review_request.inactive_file_attachments_count > 0:
                review_request.inactive_file_attachments.update(
                    draft_caption=F('caption'))
                draft.inactive_file_attachments = \
                    review_request.inactive_file_attachments.all()

        return draft

    def publish(self, review_request=None, user=None, trivial=False,
                send_notification=True, validate_fields=True, timestamp=None):

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

        if not self.changedesc and review_request.public:
            self.changedesc = ChangeDescription()

        if not user:
            if self.changedesc:
                user = self.changedesc.get_user(self)
            else:
                user = review_request.submitter

        self.copy_fields_to_request(review_request)

        # If no changes were made, raise exception and do not save
        if self.changedesc and not self.changedesc.has_modified_fields():
            raise NotModifiedError()

        if validate_fields:
            if not (self.target_groups.exists() or
                    self.target_people.exists()):
                raise PublishError(
                    ugettext('There must be at least one reviewer before this '
                             'review request can be published.'))

            if not review_request.summary.strip():
                raise PublishError(
                    ugettext('The draft must have a summary.'))

            if not review_request.description.strip():
                raise PublishError(
                    ugettext('The draft must have a description.'))

        if self.diffset:
            self.diffset.history = review_request.diffset_history
            self.diffset.timestamp = timestamp
            self.diffset.save(update_fields=('history', 'timestamp'))

        if self.changedesc:
            self.changedesc.user = user
            self.changedesc.timestamp = timestamp
            self.changedesc.public = True
            self.changedesc.save()
            review_request.changedescs.add(self.changedesc)

        review_request.description_rich_text = self.description_rich_text
        review_request.testing_done_rich_text = self.testing_done_rich_text
        review_request.rich_text = self.rich_text
        review_request.save()

        if send_notification:
            review_request_published.send(sender=type(review_request),
                                          user=user,
                                          review_request=review_request,
                                          trivial=trivial,
                                          changedesc=self.changedesc)

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
        """
        scmtool = self.repository.get_scmtool()
        changeset = None

        if scmtool.supports_pending_changesets:
            changeset = scmtool.get_changeset(commit_id, allow_empty=True)

        if changeset and changeset.pending:
            self.update_from_pending_change(commit_id, changeset)
        elif self.repository.supports_post_commit:
            self.update_from_committed_change(commit_id)
        else:
            if changeset:
                raise InvalidChangeNumberError()
            else:
                raise NotImplementedError()

    def update_from_pending_change(self, commit_id, changeset):
        """Update the data from a server-side pending changeset.

        This will fetch the metadata from the server and update the fields on
        the draft.

        Args:
            commit_id (unicode):
                The changeset ID that the draft will update from.

            changeset (reviewboard.scmtools.core.ChangeSet):
                The changeset information to update from.
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

        if testing_done:
            self.testing_done = testing_done
            self.testing_done_rich_text = False

        if changeset.branch:
            self.branch = changeset.branch

        if changeset.bugs_closed:
            self.bugs_closed = ','.join(changeset.bugs_closed)

    def update_from_committed_change(self, commit_id):
        """Update from a committed change present on the server.

        Fetches the commit message and diff from the repository and sets the
        relevant fields.

        Args:
            commit_id (unicode):
                The commit ID to update from.
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

    def copy_fields_to_request(self, review_request):
        """Copies the draft information to the review request and updates the
        draft's change description.
        """
        def update_list(a, b, name, record_changes=True, name_field=None):
            aset = set([x.id for x in a.all()])
            bset = set([x.id for x in b.all()])

            if aset.symmetric_difference(bset):
                if record_changes and self.changedesc:
                    self.changedesc.record_field_change(name, a.all(), b.all(),
                                                        name_field)

                a.clear()
                for item in b.all():
                    a.add(item)

        for field_cls in get_review_request_fields():
            field = field_cls(review_request)

            if field.can_record_change_entry:
                old_value = field.load_value(review_request)
                new_value = field.load_value(self)

                if field.has_value_changed(old_value, new_value):
                    field.propagate_data(self)

                    if self.changedesc:
                        field.record_change_entry(self.changedesc,
                                                  old_value, new_value)

        # Screenshots are a bit special.  The list of associated screenshots
        # can change, but so can captions within each screenshot.
        if (review_request.screenshots_count > 0 or
            self.screenshots_count > 0):
            screenshots = list(self.screenshots.all())
            caption_changes = {}

            for s in review_request.screenshots.all():
                if s in screenshots and s.caption != s.draft_caption:
                    caption_changes[s.id] = {
                        'old': (s.caption,),
                        'new': (s.draft_caption,),
                    }

                    s.caption = s.draft_caption
                    s.save(update_fields=['caption'])

            # Now scan through again and set the caption correctly for
            # newly-added screenshots by copying the draft_caption over. We
            # don't need to include this in the changedescs here because it's a
            # new screenshot, and update_list will record the newly-added item.
            for s in screenshots:
                if s.caption != s.draft_caption:
                    s.caption = s.draft_caption
                    s.save(update_fields=['caption'])

            if caption_changes and self.changedesc:
                self.changedesc.fields_changed['screenshot_captions'] = \
                    caption_changes

            update_list(review_request.screenshots,
                        self.screenshots,
                        name='screenshots',
                        name_field="caption")

        if (review_request.inactive_screenshots_count > 0 or
            self.inactive_screenshots_count > 0):
            # There's no change notification required for this field.
            review_request.inactive_screenshots = \
                self.inactive_screenshots.all()

        # Files are treated like screenshots. The list of files can
        # change, but so can captions within each file.
        if (review_request.file_attachments_count > 0 or
            self.file_attachments_count > 0):
            files = list(self.file_attachments.all())
            caption_changes = {}

            for f in review_request.file_attachments.all():
                if f in files and f.caption != f.draft_caption:
                    caption_changes[f.id] = {
                        'old': (f.caption,),
                        'new': (f.draft_caption,),
                    }

                    f.caption = f.draft_caption
                    f.save(update_fields=['caption'])

            # Now scan through again and set the caption correctly for
            # newly-added files by copying the draft_caption over. We don't
            # need to include this in the changedescs here because it's a new
            # screenshot, and update_list will record the newly-added item.
            for f in files:
                if f.caption != f.draft_caption:
                    f.caption = f.draft_caption
                    f.save(update_fields=['caption'])

            if caption_changes and self.changedesc:
                self.changedesc.fields_changed['file_captions'] = \
                    caption_changes

            update_list(review_request.file_attachments,
                        self.file_attachments,
                        name='files',
                        name_field="display_name")

        if (review_request.inactive_file_attachments_count > 0 or
            self.inactive_file_attachments_count > 0):
            # There's no change notification required for this field.
            review_request.inactive_file_attachments = \
                self.inactive_file_attachments.all()

    def get_review_request(self):
        """Returns the associated review request."""
        return self.review_request

    class Meta:
        app_label = 'reviews'
        db_table = 'reviews_reviewrequestdraft'
        ordering = ['-last_updated']
        verbose_name = _('Review Request Draft')
        verbose_name_plural = _('Review Request Drafts')
