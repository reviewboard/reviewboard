"""Views for e-mail previews."""

from typing import Any, Dict, Optional

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from reviewboard.notifications.email.message import (
    prepare_batch_review_request_mail,
    prepare_reply_published_mail,
    prepare_review_published_mail,
    prepare_review_request_mail)
from reviewboard.notifications.email.views import BasePreviewEmailView
from reviewboard.reviews.models import Review
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin


class PreviewBatchEmailView(ReviewRequestViewMixin,
                            BasePreviewEmailView):
    """Display a preview of batch e-mails.

    This can be used to see what an HTML or plain text e-mail will look like
    for a batch publish operation.

    This supports several query parameters to control what data is included in
    the preview:

    changedesc_id (int):
        The PK of the ChangeDescription for displaying a review request update

    reviews_only (int):
        If present, will render as if no review request is being published,
        only reviews and review replies.

    reviews (comma-separated list of int):
        The PKs of reviews to include.

    review_replies (comma-separated list of int):
        The PKs of review replies to include.

    Version Added:
        6.0
    """

    build_email = staticmethod(prepare_batch_review_request_mail)

    def get_email_data(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return data used for the e-mail builder.

        The data returned will be passed to :py:attr:`build_email` to handle
        rendering the e-mail.

        This can also return a :py:class:`~django.http.HttpResponse`, which
        is useful for returning errors.

        Args:
            request (django.http.HttpResponse):
                The HTTP response from the client.

            *args (tuple):
                Additional positional arguments passed to the handler.

            **kwargs (dict):
                Additional keyword arguments passed to the handler.

        Returns:
            object:
            The dictionary data to pass as keyword arguments to
            :py:attr:`build_email`, or an instance of
            :py:class:`~django.http.HttpResponse` to immediately return to
            the client.

        Raises:
            django.http.Http404:
                The provided change description did not exist.
        """
        changedesc_id = request.GET.get('changedesc')
        reviews_only = request.GET.get('reviews_only')
        reviews = request.GET.get('reviews', '').split(',')
        review_ids = set(int(pk) for pk in reviews if pk != '')
        replies = request.GET.get('review_replies', '').split(',')
        reply_ids = set(int(pk) for pk in replies if pk != '')

        if changedesc_id:
            changedesc = get_object_or_404(self.review_request.changedescs,
                                           pk=int(changedesc_id))
            user = changedesc.get_user(self.review_request)
        else:
            changedesc = None
            user = self.review_request.submitter

        all_reviews = list(
            Review.objects.filter(pk__in=(review_ids | reply_ids)))

        return {
            'changedesc': changedesc,
            'review_request_changed': not reviews_only,
            'request': request,
            'review_replies': [review for review in all_reviews
                               if review.pk in review_ids],
            'review_request': self.review_request,
            'reviews': [review for review in all_reviews
                        if review.pk in reply_ids],
            'user': user,
        }


class PreviewReviewRequestEmailView(ReviewRequestViewMixin,
                                    BasePreviewEmailView):
    """Display a preview of an e-mail for a review request.

    This can be used to see what an HTML or plain text e-mail will look like
    for a newly-posted review request or an update to a review request.
    """

    build_email = staticmethod(prepare_review_request_mail)

    def get_email_data(
        self,
        request: HttpRequest,
        changedesc_id: Optional[int] = None,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return data used for the e-mail builder.

        The data returned will be passed to :py:attr:`build_email` to handle
        rendering the e-mail.

        This can also return a :py:class:`~django.http.HttpResponse`, which
        is useful for returning errors.

        Args:
            request (django.http.HttpResponse):
                The HTTP response from the client.

            changedesc_id (int, optional):
                The ID of a change description used when previewing a
                Review Request Updated e-mail.

            *args (tuple):
                Additional positional arguments passed to the handler.

            **kwargs (dict):
                Additional keyword arguments passed to the handler.

        Returns:
            object:
            The dictionary data to pass as keyword arguments to
            :py:attr:`build_email`, or an instance of
            :py:class:`~django.http.HttpResponse` to immediately return to
            the client.
        """
        close_type = None

        if changedesc_id:
            changedesc = get_object_or_404(self.review_request.changedescs,
                                           pk=changedesc_id)
            user = changedesc.get_user(self.review_request)

            if 'status' in changedesc.fields_changed:
                close_type = changedesc.fields_changed['status']['new'][0]
        else:
            changedesc = None
            user = self.review_request.submitter

        return {
            'user': user,
            'review_request': self.review_request,
            'changedesc': changedesc,
            'close_type': close_type,
        }


class PreviewReviewEmailView(ReviewRequestViewMixin, BasePreviewEmailView):
    """Display a preview of an e-mail for a review.

    This can be used to see what an HTML or plain text e-mail will look like
    for a review.
    """

    build_email = staticmethod(prepare_review_published_mail)

    def get_email_data(
        self,
        request: HttpRequest,
        review_id: int,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return data used for the e-mail builder.

        The data returned will be passed to :py:attr:`build_email` to handle
        rendering the e-mail.

        This can also return a :py:class:`~django.http.HttpResponse`, which
        is useful for returning errors.

        Args:
            request (django.http.HttpResponse):
                The HTTP response from the client.

            review_id (int):
                The ID of the review to preview.

            *args (tuple):
                Additional positional arguments passed to the handler.

            **kwargs (dict):
                Additional keyword arguments passed to the handler.

        Returns:
            object:
            The dictionary data to pass as keyword arguments to
            :py:attr:`build_email`, or an instance of
            :py:class:`~django.http.HttpResponse` to immediately return to
            the client.
        """
        review = get_object_or_404(Review,
                                   pk=review_id,
                                   review_request=self.review_request)

        return {
            'user': review.user,
            'review': review,
            'review_request': self.review_request,
            'to_owner_only': False,
            'request': request,
        }


class PreviewReplyEmailView(ReviewRequestViewMixin, BasePreviewEmailView):
    """Display a preview of an e-mail for a reply to a review.

    This can be used to see what an HTML or plain text e-mail will look like
    for a reply to a review.
    """

    build_email = staticmethod(prepare_reply_published_mail)

    def get_email_data(
        self,
        request: HttpRequest,
        review_id: int,
        reply_id: int,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return data used for the e-mail builder.

        The data returned will be passed to :py:attr:`build_email` to handle
        rendering the e-mail.

        This can also return a :py:class:`~django.http.HttpResponse`, which
        is useful for returning errors.

        Args:
            request (django.http.HttpResponse):
                The HTTP response from the client.

            review_id (int):
                The ID of the review the reply is for.

            reply_id (int):
                The ID of the reply to preview.

            *args (tuple):
                Additional positional arguments passed to the handler.

            **kwargs (dict):
                Additional keyword arguments passed to the handler.

        Returns:
            object:
            The dictionary data to pass as keyword arguments to
            :py:attr:`build_email`, or an instance of
            :py:class:`~django.http.HttpResponse` to immediately return to
            the client.
        """
        review = get_object_or_404(Review,
                                   pk=review_id,
                                   review_request=self.review_request)
        reply = get_object_or_404(Review, pk=reply_id, base_reply_to=review)

        return {
            'user': reply.user,
            'reply': reply,
            'review': review,
            'review_request': self.review_request,
        }
