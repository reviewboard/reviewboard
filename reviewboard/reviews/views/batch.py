"""Views for batch operations.

Version Added:
    6.0
"""

import json
import logging
from enum import Enum
from typing import List

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import (HttpRequest,
                         HttpResponse,
                         HttpResponseServerError,
                         JsonResponse)
from django.views.generic import View
from djblets.siteconfig.models import SiteConfiguration
from djblets.views.generic.base import CheckRequestMethodViewMixin

from reviewboard.accounts.mixins import CheckLoginRequiredViewMixin
from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.notifications.email.message import \
    prepare_batch_review_request_mail
from reviewboard.notifications.email.utils import send_email
from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin


logger = logging.getLogger(__name__)


class BatchOperation(str, Enum):
    """A batch operation to run.

    Version Added:
        6.0
    """

    #: Publish a set of review requests, reviews, and replies.
    PUBLISH = 'publish'

    #: Close review requests as discarded.
    DISCARD = 'discard'

    #: Close review requests as submitted.
    CLOSE = 'close'

    #: Mark review requests as archived.
    ARCHIVE = 'archive'

    #: Mark review requests as muted.
    MUTE = 'mute'

    #: Mark review requests as visible (unarchive and/or unmute).
    UNARCHIVE = 'unarchive'


class BatchOperationView(CheckRequestMethodViewMixin,
                         CheckLoginRequiredViewMixin,
                         CheckLocalSiteAccessViewMixin,
                         View):
    """Performs batch operations.

    This is effectively an RPC endpoint that allows clients to initiate various
    batch operations.

    This currently includes:

    * Publishing multiple items, including review requests, reviews, and review
      replies. This is for the unified banner when publishing both review
      request updates and reviews all at once (and with a single e-mail
      notification).
    * Closing review requests, either as submitted or discarded.
    * Adjusting the visibility state of review requests (archive or mute).

    This is not considered a public API, and may change from version to
    version. No stability or compatibility guarantees are made.

    Version Added:
        6.0
    """

    def post(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle a POST request for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Positional arguments passed to the handler.

            **kwargs (dict, unused):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        data = request.POST
        batch_str = data.get('batch')
        user = request.user
        assert isinstance(user, User)

        if not batch_str:
            return JsonResponse(
                data={
                    'stat': 'fail',
                    'error': 'Batch data was not found.',
                },
                status=400)

        try:
            batch_data = json.loads(batch_str)
        except Exception as e:
            logger.warning('Could not parse batch data "%s": %s',
                           batch_str, e,
                           extra={'request': request})
            return JsonResponse(
                data={
                    'stat': 'fail',
                    'error': 'Could not parse batch data: %s.' % e,
                },
                status=400)

        op_str = batch_data.get('op')

        try:
            op = BatchOperation(op_str)
        except ValueError:
            return JsonResponse(
                data={
                    'stat': 'fail',
                    'error': 'Unknown batch operation "%s".' % op_str,
                },
                status=400)

        review_request_ids = batch_data.get('review_requests')

        if review_request_ids:
            if not (isinstance(review_request_ids, list) and
                    all(isinstance(id, int) for id in review_request_ids)):
                return JsonResponse(
                    data={
                        'stat': 'fail',
                        'error': 'review_requests must be an array of integers.',
                    },
                    status=400)

            if self.local_site:
                id_field = 'local_id'
                extra_query = Q(local_id__in=review_request_ids)
            else:
                id_field = 'pk'
                extra_query = Q(pk__in=review_request_ids)

            review_requests_qs = (
                ReviewRequest.objects.public(
                    user=user,
                    status=None,
                    show_all_unpublished=True,
                    local_site=self.local_site,
                    extra_query=extra_query)
            )

            if op == BatchOperation.PUBLISH:
                review_requests_qs = review_requests_qs.select_related('draft')

            # We use in_bulk to deduplicate review requests. It's possible that
            # the .public() query can return duplicates, and we don't want to
            # use .distinct() because of performance issues with MySQL. Ideally
            # we'd just be able to avoid using extra_query and pass in the
            # id_field to this like we do for reviews below, but local_id isn't
            # unique (even though in the context of the resulting queryset it
            # is).
            review_requests = review_requests_qs.in_bulk()

            if len(review_requests) != len(review_request_ids):
                found_ids = [
                    getattr(rr, id_field)
                    for rr in review_requests.values()
                ]
                missing_ids = sorted(set(review_request_ids) - set(found_ids))

                if self.local_site:
                    return JsonResponse(
                        data={
                            'stat': 'fail',
                            'error': ('The following review requests are not '
                                      'valid for the local site: %r.'
                                      % missing_ids),
                        },
                        status=400)
                else:
                    return JsonResponse(
                        data={
                            'stat': 'fail',
                            'error': ('The following review requests are not '
                                      'valid: %r.'
                                      % missing_ids),
                        },
                        status=400)

            ordered_review_requests = [
                item[1]
                for item in sorted(review_requests.items())
            ]
        else:
            ordered_review_requests = []

        if op == BatchOperation.PUBLISH:
            review_ids = batch_data.get('reviews', [])
            trivial = batch_data.get('trivial', False)
            archive_after_publish = batch_data.get('archive', False)

            if review_ids:
                if not (isinstance(review_ids, list) and
                        all(isinstance(id, int) for id in review_ids)):
                    return JsonResponse(
                        data={
                            'stat': 'fail',
                            'error': 'reviews must be an array of integers.',
                        },
                        status=400)

                reviews_qs = (
                    Review.objects.accessible(
                        base_reply_to=Review.objects.ANY,
                        user=user,
                        local_site=self.local_site)
                    .prefetch_related('comments')
                    .select_related('user', 'base_reply_to'))

                # We use in_bulk to deduplicate reviews. It's possible that the
                # .accessible() query can return duplicates, and we don't want
                # to use .distinct() because of performance issues with MySQL.
                reviews = reviews_qs.in_bulk(review_ids)

                if len(reviews) != len(review_ids):
                    found_ids = reviews.keys()
                    missing_ids = sorted(set(review_ids) - set(found_ids))

                    if self.local_site:
                        return JsonResponse(
                            data={
                                'stat': 'fail',
                                'error': ('The following reviews are not valid '
                                          'for the local site: %r.'
                                          % missing_ids),
                            },
                            status=400)
                    else:
                        return JsonResponse(
                            data={
                                'stat': 'fail',
                                'error': (
                                    'The following reviews are not valid: %r.'
                                    % missing_ids),
                            },
                            status=400)
                review_objects = list(reviews.values())
            else:
                review_objects = []

            return self._publish(
                request=request,
                user=user,
                review_requests=ordered_review_requests,
                reviews=review_objects,
                trivial=trivial,
                archive_after_publish=archive_after_publish)
        elif op == BatchOperation.CLOSE:
            return self._close(
                request=request,
                user=user,
                review_requests=ordered_review_requests,
                close_type=ReviewRequest.SUBMITTED)
        elif op == BatchOperation.DISCARD:
            return self._close(
                request=request,
                user=user,
                review_requests=ordered_review_requests,
                close_type=ReviewRequest.DISCARDED)
        elif op == BatchOperation.ARCHIVE:
            return self._set_visibility(
                request=request,
                user=user,
                review_requests=ordered_review_requests,
                visibility=ReviewRequestVisit.ARCHIVED)
        elif op == BatchOperation.MUTE:
            return self._set_visibility(
                request=request,
                user=user,
                review_requests=ordered_review_requests,
                visibility=ReviewRequestVisit.MUTED)
        elif op == BatchOperation.UNARCHIVE:
            # This also means unmute.
            return self._set_visibility(
                request=request,
                user=user,
                review_requests=ordered_review_requests,
                visibility=ReviewRequestVisit.VISIBLE)
        else:
            logger.error('Hit unknown batch operation case: %s',
                         op_str,
                         extra={'request': request})
            return HttpResponseServerError()

    def _publish(
        self,
        *,
        request: HttpRequest,
        user: User,
        review_requests: List[ReviewRequest],
        reviews: List[Review],
        trivial: bool,
        archive_after_publish: bool,
    ) -> JsonResponse:
        """Publish a set of review requests and reviews.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            user (django.contrib.auth.models.User):
                The user initiating the publish operation.

            review_requests (list of reviewboard.reviews.models.ReviewRequest):
                The review requests to publish.

            reviews (list of reviewboard.reviews.models.Review):
                The reviews (and review replies) to publish.

            trivial (bool):
                Whether to skip sending e-mail notifications.

            archive_after_publish (bool):
                Whether to archive affected review requests after publishing.

        Returns:
            django.http.JsonResponse:
            The response to send to the client.
        """
        for review_request in review_requests:
            if not review_request.is_mutable_by(user):
                return JsonResponse(
                    data={
                        'stat': 'fail',
                        'error': ('User does not have permission to publish '
                                  'review request %d.'
                                  % review_request.display_id),
                    },
                    status=403)
            elif not review_request.get_draft():
                return JsonResponse(
                    data={
                        'stat': 'fail',
                        'error': ('No draft found for review request %d.'
                                  % review_request.display_id),
                    },
                    status=404)

        for review in reviews:
            if not review.is_mutable_by(user):
                return JsonResponse(
                    data={
                        'stat': 'fail',
                        'error': ('User does not have permission to publish '
                                  'review %d.'
                                  % review.pk),
                    },
                    status=403)
            elif review.public:
                return JsonResponse(
                    data={
                        'stat': 'fail',
                        'error': ('Review %d is already published.'
                                  % review.pk),
                    },
                    status=404)

            can_publish, err = review.can_publish(
                review_request_will_publish=(review.review_request in
                                             review_requests))

            if not can_publish:
                return JsonResponse(
                    data={
                        'stat': 'fail',
                        'error': err,
                    },
                    status=403)

        review_requests_to_archive = set()

        # We publish with trivial=True to skip the individual notifications,
        # and then we'll send one batched notification at the end. However, in
        # the case where we're calling this with only a single thing to
        # publish, go through the normal notifications path.
        num_review_requests = len(review_requests)
        num_reviews = len(reviews)

        suppress_notifications = \
            trivial or (num_review_requests + len(reviews)) != 1
        batches = {}

        for i, review_request in enumerate(review_requests):
            try:
                changes = review_request.publish(
                    user=user,
                    trivial=suppress_notifications)

                batches[review_request.pk] = {
                    'review_request': review_request,
                    'review_request_changed': True,
                    'reviews': [],
                    'review_replies': [],
                    'changedesc': changes,
                }

                if archive_after_publish:
                    review_requests_to_archive.add(review_request)
            except Exception as e:
                logger.exception('Failed to publish review request %d: %s',
                                 review_request.pk, e,
                                 extra={'request': request})

                if i >= 1:
                    stat = 'mixed'
                else:
                    stat = 'fail'

                return JsonResponse(
                    data={
                        'stat': stat,
                        'error': ('Failed to publish review request %d: %s'
                                  % (review_request.display_id, e)),
                        'review_requests_published': i,
                        'review_requests_not_published':
                            num_review_requests - i,
                        'reviews_published': 0,
                        'reviews_not_published': num_reviews,
                    },
                    status=500)

        for i, review in enumerate(reviews):
            try:
                review.publish(
                    user=user,
                    trivial=suppress_notifications,
                    review_request_will_publish=(review.review_request in
                                                 review_requests))

                review_request_id = review.review_request.pk

                if review_request_id not in batches:
                    batches[review_request_id] = {
                        'review_request': review.review_request,
                        'review_request_changed': False,
                        'reviews': [],
                        'review_replies': [],
                        'changedesc': None,
                    }

                if review.base_reply_to:
                    batches[review_request_id]['review_replies'].append(review)
                else:
                    batches[review_request_id]['reviews'].append(review)

                if archive_after_publish:
                    review_requests_to_archive.add(review.review_request)
            except Exception as e:
                logger.exception('Failed to publish review %d: %s',
                                 review.pk, e, extra={'request': request})

                if i > 1 or num_review_requests > 0:
                    stat = 'mixed'
                else:
                    stat = 'fail'

                return JsonResponse(
                    data={
                        'stat': stat,
                        'error': ('Failed to publish review %d: %s'
                                  % (review.pk, e)),
                        'review_requests_published': num_review_requests,
                        'review_requests_not_published': 0,
                        'reviews_published': i,
                        'reviews_not_published': num_reviews - i,
                    },
                    status=500)

        # Now prepare and send the batched notifications, if appropriate. We do
        # one e-mail per review request.
        siteconfig = SiteConfiguration.objects.get_current()

        if (suppress_notifications and
            not trivial and
            siteconfig.get('mail_send_review_mail')):
            for batch in batches.values():
                send_email(prepare_batch_review_request_mail,
                           user=user,
                           request=request,
                           **batch)

        # Finally, handle the "archive after publish" option. This affects all
        # published review requests, as well as all review requests associated
        # with reviews.
        for review_request in review_requests_to_archive:
            ReviewRequestVisit.objects.update_visibility(
                review_request, user, ReviewRequestVisit.ARCHIVED)

        return JsonResponse({
            'stat': 'ok',
        })

    def _close(
        self,
        *,
        request: HttpRequest,
        user: User,
        review_requests: List[ReviewRequest],
        close_type: str,
    ) -> JsonResponse:
        """Close a set of review requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            user (django.contrib.auth.models.User):
                The user initiating the operation.

            review_requests (list of reviewboard.reviews.models.ReviewRequest):
                The review requests to close.

            close_type (str):
                The status code to use. This is one of
                :py:attr:`reviewboard.reviews.models.ReviewRequest.STATUSES`.

        Returns:
            django.http.JsonResponse:
            The response to send to the client.
        """
        for review_request in review_requests:
            if (not review_request.is_mutable_by(user) and
                not user.has_perm('reviews.can_change_status',
                                  review_request.local_site)):
                return JsonResponse(
                    data={
                        'stat': 'fail',
                        'error': ('User does not have permission to close '
                                  'review request %d.'
                                  % review_request.display_id),
                    },
                    status=403)

        for i, review_request in enumerate(review_requests):
            try:
                review_request.close(close_type=close_type, user=user)
            except Exception as e:
                logger.exception('Failed to close review request %d: %s',
                                 review_request.pk, e,
                                 extra={'request': request})

                if i >= 1:
                    stat = 'mixed'
                else:
                    stat = 'fail'

                return JsonResponse(
                    data={
                        'stat': stat,
                        'error': ('Failed to close review request %d: %s'
                                  % (review_request.display_id, e)),
                        'review_requests_closed': i,
                        'review_requests_not_closed': len(review_requests) - i,
                    },
                    status=500)

        return JsonResponse({
            'stat': 'ok',
            'review_requests_closed': len(review_requests),
            'review_requests_not_closed': 0,
        })

    def _set_visibility(
        self,
        *,
        request: HttpRequest,
        user: User,
        review_requests: List[ReviewRequest],
        visibility: str,
    ) -> JsonResponse:
        """Set the visibility of a set of review requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            user (django.contrib.auth.models.User):
                The user initiating the operation.

            review_requests (list of reviewboard.reviews.models.ReviewRequest):
                The review requests to set the visibility for.

            visibility (str):
                The visibility state. This is one of
                :py:attr:`reviewboard.accounts.models.ReviewRequestVisit.
                VISIBILITY`.

        Returns:
            django.http.JsonResponse:
            The response to send to the client.
        """
        for review_request in review_requests:
            ReviewRequestVisit.objects.update_visibility(
                review_request,
                user,
                visibility)

        return JsonResponse({
            'stat': 'ok',
        })
