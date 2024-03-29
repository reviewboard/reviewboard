"""Views for reviewing file attachments (and legacy screenshots)."""

from __future__ import annotations

import logging
from inspect import signature
from typing import Optional, TYPE_CHECKING

from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic.base import View

from reviewboard.accounts.mixins import UserProfileRequiredViewMixin
from reviewboard.attachments.models import FileAttachment
from reviewboard.deprecation import RemovedInReviewBoard80Warning
from reviewboard.reviews.models import Screenshot
from reviewboard.reviews.ui.base import DiffMismatchReviewUI, ReviewUI
from reviewboard.reviews.ui.screenshot import LegacyScreenshotReviewUI
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin


if TYPE_CHECKING:
    from reviewboard.reviews.models import ReviewRequest


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
        diff_against_attachment: Optional[FileAttachment] = None

        review_ui_class = ReviewUI.for_object(file_attachment)

        if file_attachment_diff_id:
            diff_against_attachment = get_object_or_404(
                FileAttachment,
                Q(pk=file_attachment_diff_id) &
                Q(attachment_history=file_attachment.attachment_history) &
                review_request_q)
            diff_review_ui_class = ReviewUI.for_object(diff_against_attachment)

            if review_ui_class is not diff_review_ui_class:
                # The file types between the original and modified attachments
                # don't match. Just use the base ReviewUI to render, which will
                # show an error message.
                dummy_review_ui = DiffMismatchReviewUI(
                    review_request=review_request,
                    obj=file_attachment)
                dummy_review_ui.set_diff_against(diff_against_attachment)

                return dummy_review_ui.render_to_response(request)

        if (review_ui_class is None or
            (diff_against_attachment and
             not review_ui_class.supports_diffing)):
            raise Http404

        review_ui = review_ui_class(
            review_request=review_request,
            obj=file_attachment)

        if diff_against_attachment:
            review_ui.set_diff_against(diff_against_attachment)

        if not self._is_review_ui_enabled_for(
            review_ui, request, review_request, file_attachment):
            raise Http404

        if diff_against_attachment and not self._is_review_ui_enabled_for(
            review_ui, request, review_request, diff_against_attachment):
            raise Http404

        return review_ui.render_to_response(request)

    def _is_review_ui_enabled_for(
        self,
        review_ui: ReviewUI,
        request: HttpRequest,
        review_request: ReviewRequest,
        file_attachment: FileAttachment,
    ) -> bool:
        """Return whether a Review UI is enabled for the given object.

        Args:
            review_ui (reviewboard.reviews.ui.base.ReviewUI):
                The Review UI to check.

            request (django.http.HttpRequest):
                The user making the request.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request.

            file_attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment.
        """
        params = signature(review_ui.is_enabled_for).parameters

        try:
            if 'file_attachment' in params:
                RemovedInReviewBoard80Warning.warn(
                    'The file_attachment parameter to ReviewUI.is_enabled_for '
                    'has been removed. Please use obj= instead in Review UI %r'
                    % review_ui)

                return review_ui.is_enabled_for(
                    user=request.user,
                    review_request=review_request,
                    file_attachment=file_attachment)
            else:
                return review_ui.is_enabled_for(
                    user=request.user,
                    review_request=review_request,
                    obj=file_attachment)
        except Exception as e:
            logger.error('Error when calling is_enabled_for for '
                         'ReviewUI %r: %s',
                         review_ui, e, exc_info=True,
                         extra={'request': request})

            return False


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
