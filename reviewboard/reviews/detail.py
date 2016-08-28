"""Definitions for the review request detail view."""

from __future__ import unicode_literals

from reviewboard.reviews.fields import get_review_request_fieldsets
from reviewboard.reviews.models import BaseComment, ReviewRequest


class BaseReviewRequestPageEntry(object):
    """An entry on the review detail page.

    This contains backend logic and frontend templates for one of the boxes
    that appears below the main review request box on the review request detail
    page.

    Attributes:
        timestamp (datetime.datetime):
            The timestamp of the entry.

        collasped (bool):
            Whether the entry should be initially collapsed.
    """

    #: The template to render for the HTML.
    template_name = None

    #: The template to render for any JavaScript.
    js_template_name = None

    def __init__(self, timestamp, collapsed):
        """Initialize the entry.

        Args:
            timestamp (datetime.datetime):
                The timestamp of the entry.

            collapsed (bool):
                Whether the entry is collapsed by default.
        """
        self.timestamp = timestamp
        self.collapsed = collapsed


class ReviewEntry(BaseReviewRequestPageEntry):
    """A review box.

    Attributes:
        review (reviewboard.reviews.models.Review):
            The review for this entry.

        issue_open_count (int):
            The count of open issues within this review.

        has_issues (bool):
            Whether there are any issues (open or not).

        comments (dict):
            A dictionary of comments. Each key in this represents a comment
            type, and the values are lists of comment objects.
    """

    template_name = 'reviews/boxes/review.html'
    js_template_name = 'reviews/boxes/review.js'

    def __init__(self, request, review_request, review, collapsed):
        """Initialize the entry.

        Args:
            request (django.http.HttpRequest):
                The request object.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that the change is for.

            review (reviewboard.reviews.models.Review):
                The review.

            collapsed (bool):
                Whether the entry is collapsed by default.
        """
        super(ReviewEntry, self).__init__(review.timestamp, collapsed)

        self.request = request
        self.review_request = review_request
        self.review = review
        self.issue_open_count = 0
        self.has_issues = False
        self.comments = {
            'diff_comments': [],
            'screenshot_comments': [],
            'file_attachment_comments': [],
            'general_comments': [],
        }

    def add_comment(self, comment_type, comment):
        """Add a comment to this entry.

        Args:
            comment_type (unicode):
                The type of comment (an index into the :py:attr:`comments`
                dictionary).

            comment (reviewboard.reviews.models.BaseComment):
                The comment to add.
        """
        self.comments[comment_type].append(comment)

        if comment.issue_opened:
            self.has_issues = True

            if comment.issue_status == BaseComment.OPEN:
                self.issue_open_count += 1

                if self.review_request.submitter == self.request.user:
                    self.collapsed = False


class ChangeEntry(BaseReviewRequestPageEntry):
    """A change description box.

    Attributes:
        changedesc (reviewboard.changedescs.models.ChangeDescription):
            The change description for this entry.
    """

    template_name = 'reviews/boxes/change.html'
    js_template_name = 'reviews/boxes/change.js'

    def __init__(self, request, review_request, changedesc, collapsed,
                 locals_vars):
        """Initialize the entry.

        Args:
            request (django.http.HttpRequest):
                The request object.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that the change is for.

            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description for this entry.

            collapsed (bool):
                Whether the entry is collapsed by default.

            locals_vars (dict):
                A dictionary of the local variables inside the review detail
                view. This is done because some of the fields in the change
                description may make use of some of the maps maintained while
                building the page in order to avoid adding additional queries

                .. seealso::

                   :py:data:`~reviewboard.reviews.fields.Field.locals_vars`
            """
        super(ChangeEntry, self).__init__(changedesc.timestamp, collapsed)

        self.changedesc = changedesc
        self.fields_changed_groups = []
        cur_field_changed_group = None

        # See if there was a review request status change.
        status_change = changedesc.fields_changed.get('status')

        if status_change:
            assert 'new' in status_change
            self.new_status = ReviewRequest.status_to_string(
                status_change['new'][0])
        else:
            self.new_status = None

        # Process the list of fields, in order by fieldset. These will be
        # put into groups composed of inline vs. full-width field values,
        # for render into the box.
        fieldsets = get_review_request_fieldsets(
            include_main=True,
            include_change_entries_only=True)

        for fieldset in fieldsets:
            for field_cls in fieldset.field_classes:
                field_id = field_cls.field_id

                if field_id not in changedesc.fields_changed:
                    continue

                inline = field_cls.change_entry_renders_inline

                if (not cur_field_changed_group or
                    cur_field_changed_group['inline'] != inline):
                    # Begin a new group of fields.
                    cur_field_changed_group = {
                        'inline': inline,
                        'fields': [],
                    }
                    self.fields_changed_groups.append(cur_field_changed_group)

                if hasattr(field_cls, 'locals_vars'):
                    field = field_cls(review_request, request=request,
                                      locals_vars=locals_vars)
                else:
                    field = field_cls(review_request, request=request)

                cur_field_changed_group['fields'] += \
                    field.get_change_entry_sections_html(
                        changedesc.fields_changed[field_id])
