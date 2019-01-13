from __future__ import unicode_literals

import re

from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.attachments.models import FileAttachmentHistory
from reviewboard.reviews.models.default_reviewer import DefaultReviewer


@python_2_unicode_compatible
class BaseReviewRequestDetails(models.Model):
    """Base information for a review request and draft.

    ReviewRequest and ReviewRequestDraft share a lot of fields and
    methods. This class provides those fields and methods for those
    classes.
    """
    MAX_SUMMARY_LENGTH = 300

    description = models.TextField(_("description"), blank=True)
    description_rich_text = models.BooleanField(
        _('description in rich text'),
        default=False)

    testing_done = models.TextField(_("testing done"), blank=True)
    testing_done_rich_text = models.BooleanField(
        _('testing done in rich text'),
        default=False)

    bugs_closed = models.CharField(_("bugs"), max_length=300, blank=True)
    branch = models.CharField(_("branch"), max_length=300, blank=True)
    commit_id = models.CharField(_('commit ID'), max_length=64, blank=True,
                                 null=True, db_index=True)

    extra_data = JSONField(null=True)

    # Deprecated and no longer used for new review requests as of 2.0.9.
    rich_text = models.BooleanField(_("rich text"), default=False)

    def get_review_request(self):
        raise NotImplementedError

    def get_bug_list(self):
        """Returns a list of bugs associated with this review request."""
        if self.bugs_closed == "":
            return []

        bugs = list(set(re.split(r"[, ]+", self.bugs_closed)))

        # First try a numeric sort, to show the best results for the majority
        # case of bug trackers with numeric IDs.  If that fails, sort
        # alphabetically.
        try:
            bugs.sort(key=int)
        except ValueError:
            bugs.sort()

        return bugs

    def get_screenshots(self):
        """Return a generator for all active screenshots.

        This includes all current screenshots, but not previous inactive ones.

        By accessing screenshots through this method, future review request
        lookups from the screenshots will be avoided.

        Yields:
            reviewboard.reviews.models.screenshot.Screenshot:
            A screenshot on the review request or draft.
        """
        if self.screenshots_count > 0:
            review_request = self.get_review_request()

            for screenshot in self.screenshots.all():
                screenshot._review_request = review_request
                yield screenshot

    def get_inactive_screenshots(self):
        """Return a generator for all inactive screenshots.

        This only includes screenshots that were previously visible but
        have since been removed.

        By accessing screenshots through this method, future review request
        lookups from the screenshots will be avoided.

        Yields:
            reviewboard.reviews.models.screenshot.Screenshot:
            An inactive screenshot on the review request or draft.
        """
        if self.inactive_screenshots_count > 0:
            review_request = self.get_review_request()

            for screenshot in self.inactive_screenshots.all():
                screenshot._review_request = review_request
                yield screenshot

    def get_file_attachments(self):
        """Return a list for all active file attachments.

        This includes all current file attachments, but not previous inactive
        ones.

        By accessing file attachments through this method, future review
        request lookups from the file attachments will be avoided.

        Returns:
            list of reviewboard.attachments.models.FileAttachment:
            The active file attachments on the review request or draft.
        """
        def get_attachments(review_request):
            for file_attachment in self.file_attachments.all():
                file_attachment._review_request = review_request

                # Handle legacy entries which don't have an associated
                # FileAttachmentHistory entry.
                if (not file_attachment.is_from_diff and
                    file_attachment.attachment_history is None):
                    history = FileAttachmentHistory.objects.create(
                        display_position=FileAttachmentHistory
                            .compute_next_display_position(
                                review_request))

                    review_request.file_attachment_histories.add(history)

                    file_attachment.attachment_history = history
                    file_attachment.save(update_fields=['attachment_history'])

                yield file_attachment

        def get_display_position(attachment):
            if attachment.attachment_history_id is not None:
                return attachment.attachment_history.display_position
            else:
                return 0

        if self.file_attachments_count > 0:
            review_request = self.get_review_request()

            return sorted(get_attachments(review_request),
                          key=get_display_position)
        else:
            return []

    def get_inactive_file_attachments(self):
        """Return a generator for all inactive file attachments.

        This only includes file attachments that were previously visible
        but have since been removed.

        By accessing file attachments through this method, future review
        request lookups from the file attachments will be avoided.

        Yields:
            reviewboard.attachments.models.FileAttachment:
            An inactive file attachment on the review request or draft.
        """
        if self.inactive_file_attachments_count > 0:
            review_request = self.get_review_request()

            for file_attachment in self.inactive_file_attachments.all():
                file_attachment._review_request = review_request
                yield file_attachment

    def add_default_reviewers(self):
        """Add default reviewers based on the diffset.

        This method goes through the DefaultReviewer objects in the database
        and adds any missing reviewers based on regular expression comparisons
        with the set of files in the diff.
        """
        if not self.repository:
            return

        diffset = self.get_latest_diffset()

        if not diffset:
            return

        match_default_reviewer_ids = []

        # This won't actually be queried until needed, since we're not
        # evaluating the queryset at this stage. That means we save a lookup
        # if the list of default reviewers is empty below.
        files = diffset.files.values_list('source_file', 'dest_file')

        default_reviewers = (
            DefaultReviewer.objects.for_repository(self.repository,
                                                   self.local_site)
            .only('pk', 'file_regex')
        )

        for default_reviewer in default_reviewers:
            try:
                regex = re.compile(default_reviewer.file_regex)
            except:
                continue

            for source_file, dest_file in files:
                if regex.match(source_file or dest_file):
                    match_default_reviewer_ids.append(default_reviewer.pk)
                    break

        if not match_default_reviewer_ids:
            return

        # Get the list of users and groups across all matched default
        # reviewers. We'll fetch them directly from the ManyToMany tables,
        # to avoid extra queries. Django's m2m.add() methods will ensure no
        # duplicates are added, and that insertions aren't performed if not
        # needed.
        self.target_people.add(*(
            entry.user
            for entry in (
                DefaultReviewer.people.through.objects
                .filter(defaultreviewer_id__in=match_default_reviewer_ids,
                        user__is_active=True)
                .select_related('user')
            )
        ))

        self.target_groups.add(*(
            entry.group
            for entry in (
                DefaultReviewer.groups.through.objects
                .filter(defaultreviewer_id__in=match_default_reviewer_ids)
                .select_related('group')
            )
        ))

    def save(self, **kwargs):
        self.bugs_closed = self.bugs_closed.strip()
        self.summary = self._truncate(self.summary, self.MAX_SUMMARY_LENGTH)

        super(BaseReviewRequestDetails, self).save(**kwargs)

    def _truncate(self, string, num):
        if len(string) > num:
            string = string[0:num]
            i = string.rfind('.')

            if i != -1:
                string = string[0:i + 1]

        return string

    def __str__(self):
        if self.summary:
            return six.text_type(self.summary)
        else:
            return six.text_type(_('(no summary)'))

    class Meta:
        abstract = True
        app_label = 'reviews'
