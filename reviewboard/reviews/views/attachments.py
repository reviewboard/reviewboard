"""Views for reviewing file attachments (and legacy screenshots)."""

import logging
from typing import Optional

from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic.base import View

from reviewboard.accounts.mixins import UserProfileRequiredViewMixin
from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import Screenshot
from reviewboard.reviews.ui.base import FileAttachmentReviewUI
from reviewboard.reviews.ui.screenshot import LegacyScreenshotReviewUI
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin


logger = logging.getLogger(__name__)


class ReviewFileAttachmentView(ReviewRequestViewMixin,
                               UserProfileRequiredViewMixin,
                               View):
    """Displays a file attachment with a review UI."""

    def get(
        self,
        request: HttpRequest,
        file_attachment_id: int,
        file_attachment_diff_id: Optional[int] = None,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle a HTTP GET request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            file_attachment_id (int):
                The ID of the file attachment to review.

            file_attachment_diff_id (int, optional):
                The ID of the file attachment to diff against.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response from the handler.
        """
        review_request = self.review_request
        draft = review_request.get_draft(request.user)

        # Make sure the attachment returned is part of either the review
        # request or an accessible draft.
        review_request_q = (Q(review_request=review_request) |
                            Q(inactive_review_request=review_request))

        if draft:
            review_request_q |= Q(drafts=draft) | Q(inactive_drafts=draft)

        file_attachment = get_object_or_404(
            FileAttachment,
            Q(pk=file_attachment_id) & review_request_q)

        review_ui = file_attachment.review_ui

        if not review_ui:
            review_ui = FileAttachmentReviewUI(review_request, file_attachment)

        if file_attachment_diff_id:
            file_attachment_revision = get_object_or_404(
                FileAttachment,
                Q(pk=file_attachment_diff_id) &
                Q(attachment_history=file_attachment.attachment_history) &
                review_request_q)
            review_ui.set_diff_against(file_attachment_revision)

        try:
            is_enabled_for = review_ui.is_enabled_for(
                user=request.user,
                review_request=review_request,
                file_attachment=file_attachment)
        except Exception as e:
            logger.error('Error when calling is_enabled_for for '
                         'FileAttachmentReviewUI %r: %s',
                         review_ui, e, exc_info=True,
                         extra={'request': request})
            is_enabled_for = False

        if review_ui and is_enabled_for:
            return review_ui.render_to_response(request)
        else:
            raise Http404


class ReviewScreenshotView(ReviewRequestViewMixin,
                           UserProfileRequiredViewMixin,
                           View):
    """Displays a review UI for a screenshot.

    Screenshots are a legacy feature, predating file attachments. While they
    can't be created anymore, this view does allow for reviewing screenshots
    uploaded in old versions.
    """

    def get(
        self,
        request: HttpRequest,
        screenshot_id: int,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle a HTTP GET request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            screenshot_id (int):
                The ID of the screenshot to review.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response from the handler.
        """
        review_request = self.review_request
        draft = review_request.get_draft(request.user)

        # Make sure the screenshot returned is part of either the review
        # request or an accessible draft.
        review_request_q = (Q(review_request=review_request) |
                            Q(inactive_review_request=review_request))

        if draft:
            review_request_q |= Q(drafts=draft) | Q(inactive_drafts=draft)

        screenshot = get_object_or_404(Screenshot,
                                       Q(pk=screenshot_id) & review_request_q)
        review_ui = LegacyScreenshotReviewUI(review_request, screenshot)

        return review_ui.render_to_response(request)
