"""Diff viewer view."""

from typing import Any, Dict, Optional

from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext

from reviewboard.accounts.mixins import UserProfileRequiredViewMixin
from reviewboard.attachments.models import get_latest_file_attachments
from reviewboard.diffviewer.views import DiffViewerView
from reviewboard.reviews.context import (comment_counts,
                                         diffsets_with_comments,
                                         has_comments_in_diffsets_excluding,
                                         interdiffs_with_comments,
                                         make_review_request_context)
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.reviews.models import Review


class ReviewsDiffViewerView(ReviewRequestViewMixin,
                            UserProfileRequiredViewMixin,
                            DiffViewerView):
    """Renders the diff viewer for a review request.

    This wraps the base
    :py:class:`~reviewboard.diffviewer.views.DiffViewerView` to display a diff
    for the given review request and the given diff revision or range.

    The view expects the following parameters to be provided:

    ``review_request_id``:
        The ID of the ReviewRequest containing the diff to render.

    The following may also be provided:

    ``revision``:
        The DiffSet revision to render.

    ``interdiff_revision``:
        The second DiffSet revision in an interdiff revision range.

    ``local_site``:
        The LocalSite the ReviewRequest must be on, if any.

    See :py:class:`~reviewboard.diffviewer.views.DiffViewerView`'s
    documentation for the accepted query parameters.
    """

    def __init__(
        self,
        **kwargs,
    ) -> None:
        """Initialize a view for the request.

        Args:
            **kwargs (dict):
                Keyword arguments passed to :py:meth:`as_view`.
        """
        super().__init__(**kwargs)

        self.draft = None
        self.diffset = None
        self.interdiffset = None

    def get(
        self,
        request: HttpRequest,
        revision: Optional[int] = None,
        interdiff_revision: Optional[int] = None,
        *args,
        **kwargs
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        This will look up the review request and DiffSets, given the
        provided information, and pass them to the parent class for rendering.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            revision (int, optional):
                The revision of the diff to view. This defaults to the latest
                diff.

            interdiff_revision (int, optional):
                The revision to use for an interdiff, if viewing an interdiff.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        review_request = self.review_request

        self.draft = review_request.get_draft(review_request.submitter)

        if self.draft and not self.draft.is_accessible_by(request.user):
            self.draft = None

        self.diffset = self.get_diff(revision, self.draft)

        if interdiff_revision and interdiff_revision != revision:
            # An interdiff revision was specified. Try to find a matching
            # diffset.
            self.interdiffset = self.get_diff(interdiff_revision, self.draft)

        return super().get(
            request=request,
            diffset=self.diffset,
            interdiffset=self.interdiffset,
            *args,
            **kwargs)

    def get_context_data(
        self,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return additional context data for the template.

        This provides some additional data used for rendering the diff
        viewer. This data is more specific to the reviewing functionality,
        as opposed to the data calculated by
        :py:meth:`DiffViewerView.get_context_data
        <reviewboard.diffviewer.views.DiffViewerView.get_context_data>`
        which is more focused on the actual diff.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            dict:
            Context data used to render the template.
        """
        # Try to find an existing pending review of this diff from the
        # current user.
        pending_review = \
            self.review_request.get_pending_review(self.request.user)

        has_draft_diff = self.draft and self.draft.diffset
        is_draft_diff = has_draft_diff and self.draft.diffset == self.diffset
        is_draft_interdiff = (has_draft_diff and self.interdiffset and
                              self.draft.diffset == self.interdiffset)

        # Get the list of diffsets. We only want to calculate this once.
        diffsets = self.review_request.get_diffsets()
        num_diffs = len(diffsets)

        if num_diffs > 0:
            latest_diffset = diffsets[-1]
        else:
            latest_diffset = None

        if self.draft and self.draft.diffset:
            num_diffs += 1

        last_activity_time = self.review_request.get_last_activity_info(
            diffsets)['timestamp']

        review_request_details = self.draft or self.review_request

        file_attachments = list(review_request_details.get_file_attachments())
        screenshots = list(review_request_details.get_screenshots())

        latest_file_attachments = get_latest_file_attachments(file_attachments)
        social_page_image_url = self.get_social_page_image_url(
            latest_file_attachments)

        # Compute the lists of comments based on filediffs and interfilediffs.
        # We do this using the 'through' table so that we can select_related
        # the reviews and comments.
        comments = {}
        q = (
            Review.comments.through.objects
            .filter(review__review_request=self.review_request)
            .select_related()
        )

        for obj in q:
            comment = obj.comment
            comment.review_obj = obj.review
            key = (comment.filediff_id, comment.interfilediff_id)
            comments.setdefault(key, []).append(comment)

        # Build the status information shown below the summary.
        close_info = self.review_request.get_close_info()

        if latest_diffset:
            status_extra_info = [{
                'text': gettext('Latest diff uploaded {timestamp}'),
                'timestamp': latest_diffset.timestamp,
            }]
        else:
            status_extra_info = []

        review_request_status_html = self.get_review_request_status_html(
            review_request_details=review_request_details,
            close_info=close_info,
            extra_info=status_extra_info)

        # Build the final context for the page.
        context = super().get_context_data(**kwargs)
        context.update({
            'close_description': close_info['close_description'],
            'close_description_rich_text': close_info['is_rich_text'],
            'close_timestamp': close_info['timestamp'],
            'diffsets': diffsets,
            'review': pending_review,
            'review_request_details': review_request_details,
            'review_request_status_html': review_request_status_html,
            'draft': self.draft,
            'last_activity_time': last_activity_time,
            'file_attachments': latest_file_attachments,
            'all_file_attachments': file_attachments,
            'screenshots': screenshots,
            'comments': comments,
            'social_page_image_url': social_page_image_url,
            'social_page_title': (
                'Diff for Review Request #%s: %s'
                % (self.review_request.display_id,
                   review_request_details.summary)
            ),
        })
        context.update(make_review_request_context(self.request,
                                                   self.review_request,
                                                   is_diff_view=True))

        diffset_pair = context['diffset_pair']
        diff_context = context['diff_context']

        diff_context.update({
            'num_diffs': num_diffs,
            'comments_hint': {
                'has_other_comments': has_comments_in_diffsets_excluding(
                    pending_review, diffset_pair),
                'diffsets_with_comments': [
                    {
                        'revision': diffset_info['diffset'].revision,
                        'is_current': diffset_info['is_current'],
                    }
                    for diffset_info in diffsets_with_comments(
                        pending_review, diffset_pair)
                ],
                'interdiffs_with_comments': [
                    {
                        'old_revision': pair['diffset'].revision,
                        'new_revision': pair['interdiff'].revision,
                        'is_current': pair['is_current'],
                    }
                    for pair in interdiffs_with_comments(
                        pending_review, diffset_pair)
                ],
            },
        })
        diff_context['revision'].update({
            'latest_revision': (latest_diffset.revision
                                if latest_diffset else None),
            'is_draft_diff': is_draft_diff,
            'is_draft_interdiff': is_draft_interdiff,
        })

        files = []

        for f in context['files']:
            filediff = f['filediff']
            interfilediff = f['interfilediff']
            base_filediff = f['base_filediff']

            if base_filediff:
                base_filediff_id = base_filediff.pk
            else:
                base_filediff_id = None

            data = {
                'newfile': f['newfile'],
                'binary': f['binary'],
                'deleted': f['deleted'],
                'id': filediff.pk,
                'depot_filename': f['depot_filename'],
                'dest_filename': f['dest_filename'],
                'dest_revision': f['dest_revision'],
                'revision': f['revision'],
                'filediff': {
                    'id': filediff.pk,
                    'revision': filediff.diffset.revision,
                },
                'base_filediff_id': base_filediff_id,
                'index': f['index'],
                'comment_counts': comment_counts(self.request.user, comments,
                                                 filediff, interfilediff),
                'public': f['public'],
            }

            if interfilediff:
                data['interfilediff'] = {
                    'id': interfilediff.pk,
                    'revision': interfilediff.diffset.revision,
                }

            if f['force_interdiff']:
                data['force_interdiff'] = True
                data['interdiff_revision'] = f['force_interdiff_revision']

            files.append(data)

        diff_context['files'] = files

        return context
