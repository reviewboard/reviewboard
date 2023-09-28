"""Main review request page view."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from django.utils.timezone import utc
from django.views.generic.base import TemplateView
from djblets.views.generic.etag import ETagViewMixin

from reviewboard.accounts.mixins import UserProfileRequiredViewMixin
from reviewboard.accounts.models import Profile, ReviewRequestVisit
from reviewboard.attachments.models import get_latest_file_attachments
from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.reviews.context import make_review_request_context
from reviewboard.reviews.detail import ReviewRequestPageData, entry_registry
from reviewboard.reviews.markdown_utils import is_rich_text_default_for_user
from reviewboard.reviews.models.review_request import FileAttachmentState
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin

if TYPE_CHECKING:
    from reviewboard.attachments.models import FileAttachment


logger = logging.getLogger(__name__)


class ReviewRequestDetailView(ReviewRequestViewMixin,
                              UserProfileRequiredViewMixin,
                              ETagViewMixin,
                              TemplateView):
    """A view for the main review request page.

    This page shows information on the review request, all the reviews and
    issues that have been posted, and the status updates made on uploaded
    changes.
    """

    template_name = 'reviews/review_detail.html'

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

        self.data = None
        self.visited = None
        self.blocks = None
        self.last_activity_time = None
        self.last_visited = None

    def get_etag_data(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> str:
        """Return an ETag for the view.

        This will look up state needed for the request and generate a
        suitable ETag. Some of the information will be stored for later
        computation of the template context.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Positional arguments passsed to the handler.

            **kwargs (dict, unused):
                Keyword arguments passed to the handler.

        Returns:
            str:
            The ETag for the page.
        """
        review_request = self.review_request

        # Track the visit to this review request, so the dashboard can
        # reflect whether there are new updates.
        self.visited, self.last_visited = self.track_review_request_visit()

        # Begin building data for the contents of the page. This will include
        # the reviews, change descriptions, and other content shown on the
        # page.
        data = ReviewRequestPageData(review_request=review_request,
                                     request=request,
                                     last_visited=self.last_visited)
        self.data = data

        data.query_data_pre_etag()

        self.blocks = review_request.get_blocks()

        # Prepare data used in both the page and the ETag.
        starred = self.is_review_request_starred()

        self.last_activity_time = review_request.get_last_activity_info(
            data.diffsets, data.reviews)['timestamp']
        etag_timestamp = self.last_activity_time

        entry_etags = ':'.join(
            entry_cls.build_etag_data(data)
            for entry_cls in entry_registry
        )

        if data.draft:
            draft_timestamp = data.draft.last_updated
        else:
            draft_timestamp = ''

        return ':'.join(str(value) for value in (
            request.user,
            etag_timestamp,
            draft_timestamp,
            data.latest_changedesc_timestamp,
            entry_etags,
            data.latest_review_timestamp,
            review_request.last_review_activity_timestamp,
            is_rich_text_default_for_user(request.user),
            is_site_read_only_for(request.user),
            [r.pk for r in self.blocks],
            starred,
            self.visited and self.visited.visibility,
            (self.last_visited and
             self.last_visited < self.last_activity_time),
            settings.AJAX_SERIAL,
        ))

    def track_review_request_visit(
        self,
    ) -> Tuple[Optional[ReviewRequestVisit], Optional[datetime]]:
        """Track a visit to the review request.

        If the user is authenticated, their visit to this page will be
        recorded. That information is used to provide an indicator in the
        dashboard when a review request is later updated.

        Returns:
            tuple:
            A tuple containing the following items:

            Tuple:
                0 (reviewboard.accounts.models.ReviewRequestVisit):
                    The resulting visit object, if the user is authenticated
                    and the visit could be created or updated.

                1 (datetime.datetime):
                    The timestamp when the user had last visited the review
                    request, prior to this visit (or ``None`` if they haven't).
        """
        user = self.request.user
        visited = None
        last_visited = None

        if user.is_authenticated:
            review_request = self.review_request

            try:
                visited, visited_is_new = \
                    ReviewRequestVisit.objects.get_or_create(
                        user=user, review_request=review_request)
                last_visited = visited.timestamp.replace(tzinfo=utc)
            except ReviewRequestVisit.DoesNotExist:
                # Somehow, this visit was seen as created but then not
                # accessible. We need to log this and then continue on.
                logger.error('Unable to get or create ReviewRequestVisit '
                             'for user "%s" on review request at %s',
                             user.username,
                             review_request.get_absolute_url())
                visited = None

            # If the review request is public and pending review and if the
            # user is logged in, mark that they've visited this review request.
            if (visited and
                review_request.public and
                review_request.status == review_request.PENDING_REVIEW):
                visited.timestamp = timezone.now()
                visited.save()

        return visited, last_visited

    def is_review_request_starred(self) -> bool:
        """Return whether the review request has been starred by the user.

        Returns:
            bool:
            ``True`` if the user has starred the review request.
            ``False`` if they have not.
        """
        user = self.request.user

        if user.is_authenticated:
            try:
                return (
                    user.get_profile(create_if_missing=False)
                    .starred_review_requests
                    .filter(pk=self.review_request.pk)
                    .exists()
                )
            except Profile.DoesNotExist:
                pass

        return False

    def get_context_data(
        self,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return data for the template.

        This will return information on the review request, the entries to
        show, file attachments, issues, metadata to use when sharing the
        review request on social networks, and everything else needed to
        render the page.

        Args:
            **kwargs (dict):
                Additional keyword arguments passed to the view.

        Returns:
            dict:
            Context data for the template.
        """
        review_request = self.review_request
        request = self.request
        data = self.data
        assert data is not None

        data.query_data_post_etag()
        entries = data.get_entries()
        review_request_details = data.review_request_details

        review = review_request.get_pending_review(request.user)
        close_info = review_request.get_close_info()
        review_request_status_html = self.get_review_request_status_html(
            review_request_details=review_request_details,
            close_info=close_info)

        file_attachments = \
            get_latest_file_attachments(data.active_file_attachments)
        all_file_attachments: List[FileAttachment] = data.all_file_attachments
        attachments_length_before = len(file_attachments)

        # Add the file attachments that are pending deletion so that
        # we can display them.
        file_attachments.extend(get_latest_file_attachments([
            attachment
            for attachment in all_file_attachments
            if (review_request_details.get_file_attachment_state(attachment) ==
                FileAttachmentState.PENDING_DELETION)
        ]))

        if attachments_length_before != len(file_attachments):
            # Pending deletion file attachments were added, sort the list so
            # that all attachments appear in the right order.
            file_attachments.sort(
                key=lambda file: file.attachment_history.display_position)

        social_page_image_url = self.get_social_page_image_url(
            file_attachments)

        context = super().get_context_data(**kwargs)
        context.update(make_review_request_context(request, review_request))
        context.update({
            'all_file_attachments': all_file_attachments,
            'blocks': self.blocks,
            'draft': data.draft,
            'review_request_details': review_request_details,
            'review_request_visit': self.visited,
            'review_request_status_html': review_request_status_html,
            'entries': entries,
            'last_activity_time': self.last_activity_time,
            'last_visited': self.last_visited,
            'review': review,
            'request': request,
            'close_description': close_info['close_description'],
            'close_description_rich_text': close_info['is_rich_text'],
            'close_timestamp': close_info['timestamp'],
            'issue_counts': data.issue_counts,
            'issues': data.issues,
            'file_attachments': file_attachments,
            'screenshots': data.active_screenshots,
            'social_page_image_url': social_page_image_url,
            'social_page_title': (
                'Review Request #%s: %s'
                % (review_request.display_id, review_request.summary)
            ),
        })

        return context
