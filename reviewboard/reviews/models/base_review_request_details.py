from __future__ import unicode_literals

import re

from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models.default_reviewer import DefaultReviewer
from reviewboard.scmtools.errors import InvalidChangeNumberError


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
        """Returns the list of all screenshots on a review request.

        This includes all current screenshots, but not previous ones.

        By accessing screenshots through this method, future review request
        lookups from the screenshots will be avoided.
        """
        review_request = self.get_review_request()

        for screenshot in self.screenshots.all():
            screenshot._review_request = review_request
            yield screenshot

    def get_inactive_screenshots(self):
        """Returns the list of all inactive screenshots on a review request.

        This only includes screenshots that were previously visible but
        have since been removed.

        By accessing screenshots through this method, future review request
        lookups from the screenshots will be avoided.
        """
        review_request = self.get_review_request()

        for screenshot in self.inactive_screenshots.all():
            screenshot._review_request = review_request
            yield screenshot

    def get_file_attachments(self):
        """Returns the list of all file attachments on a review request.

        This includes all current file attachments, but not previous ones.

        By accessing file attachments through this method, future review
        request lookups from the file attachments will be avoided.
        """
        review_request = self.get_review_request()

        for file_attachment in self.file_attachments.all():
            file_attachment._review_request = review_request
            yield file_attachment

    def get_inactive_file_attachments(self):
        """Returns all inactive file attachments on a review request.

        This only includes file attachments that were previously visible
        but have since been removed.

        By accessing file attachments through this method, future review
        request lookups from the file attachments will be avoided.
        """
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
        diffset = self.get_latest_diffset()

        if not diffset:
            return

        people = set()
        groups = set()

        # TODO: This is kind of inefficient, and could maybe be optimized in
        # some fancy way.  Certainly the most superficial optimization that
        # could be made would be to cache the compiled regexes somewhere.
        files = diffset.files.all()
        reviewers = DefaultReviewer.objects.for_repository(self.repository,
                                                           self.local_site)

        for default in reviewers:
            try:
                regex = re.compile(default.file_regex)
            except:
                continue

            for filediff in files:
                if regex.match(filediff.source_file or filediff.dest_file):
                    for person in default.people.all():
                        if person.is_active:
                            people.add(person)

                    for group in default.groups.all():
                        groups.add(group)

                    break

        existing_people = self.target_people.all()

        for person in people:
            if person not in existing_people:
                self.target_people.add(person)

        existing_groups = self.target_groups.all()

        for group in groups:
            if group not in existing_groups:
                self.target_groups.add(group)

    def update_from_commit_id(self, commit_id):
        """Updates the data from a server-side changeset.

        If the commit ID refers to a pending changeset on an SCM which stores
        such things server-side (like perforce), the details like the summary
        and description will be updated with the latest information.

        If the change number is the commit ID of a change which exists on the
        server, the summary and description will be set from the commit's
        message, and the diff will be fetched from the SCM.
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
        """Updates the data from a server-side pending changeset.

        This will fetch the metadata from the server and update the fields on
        the review request.
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
        """Updates from a committed change present on the server.

        Fetches the commit message and diff from the repository and sets the
        relevant fields.
        """
        commit = self.repository.get_change(commit_id)
        summary, message = commit.split_message()
        message = message.strip()

        self.commit = commit_id
        self.summary = summary.strip()

        self.description = message
        self.description_rich_text = False

        DiffSet.objects.create_from_data(
            repository=self.repository,
            diff_file_name='diff',
            diff_file_contents=commit.diff.encode('utf-8'),
            parent_diff_file_name=None,
            parent_diff_file_contents=None,
            diffset_history=self.get_review_request().diffset_history,
            basedir='/',
            request=None)

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
