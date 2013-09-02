from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.reviews.models import Review
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.user import UserResource


class BaseReviewResource(WebAPIResource):
    """Base class for review resources.

    Provides common fields and functionality for all review resources.
    """
    model = Review
    fields = {
        'body_bottom': {
            'type': str,
            'description': 'The review content below the comments.',
        },
        'body_top': {
            'type': str,
            'description': 'The review content above the comments.',
        },
        'id': {
            'type': int,
            'description': 'The numeric ID of the review.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the review is currently '
                           'visible to other users.',
        },
        'ship_it': {
            'type': bool,
            'description': 'Whether or not the review has been marked '
                           '"Ship It!"',
        },
        'timestamp': {
            'type': str,
            'description': 'The date and time that the review was posted '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'user': {
            'type': UserResource,
            'description': 'The user who wrote the review.',
        },
    }
    last_modified_field = 'timestamp'

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get_queryset(self, request, review_request_id, is_list=False,
                     *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, review_request_id, *args, **kwargs)
        q = Q(review_request=review_request) & \
            Q(**self.get_base_reply_to_field(*args, **kwargs))

        if is_list:
            # We don't want to show drafts in the list.
            q = q & Q(public=True)

        return self.model.objects.filter(q)

    def get_base_reply_to_field(self):
        raise NotImplementedError

    def has_access_permissions(self, request, review, *args, **kwargs):
        return review.public or review.user == request.user

    def has_modify_permissions(self, request, review, *args, **kwargs):
        return not review.public and review.user == request.user

    def has_delete_permissions(self, request, review, *args, **kwargs):
        return not review.public and review.user == request.user

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'ship_it': {
                'type': bool,
                'description': 'Whether or not to mark the review "Ship It!"',
            },
            'body_top': {
                'type': str,
                'description': 'The review content above the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The review content below the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a new review.

        The new review will start off as private. Only the author of the
        review (the user who is logged in and issuing this API call) will
        be able to see and interact with the review.

        Initial data for the review can be provided by passing data for
        any number of the fields. If nothing is provided, the review will
        start off as blank.

        If the user submitting this review already has a pending draft review
        on this review request, then this will update the existing draft and
        return :http:`303`. Otherwise, this will create a new draft and
        return :http:`201`. Either way, this request will return without
        a payload and with a ``Location`` header pointing to the location of
        the new draft review.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        review, is_new = Review.objects.get_or_create(
            review_request=review_request,
            user=request.user,
            public=False,
            **self.get_base_reply_to_field(*args, **kwargs))

        if is_new:
            status_code = 201  # Created
        else:
            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            status_code = 303  # See Other

        result = self._update_review(request, review, *args, **kwargs)

        if not isinstance(result, tuple) or result[0] != 200:
            return result
        else:
            return status_code, result[1], {
                'Location': self.get_href(review, request, *args, **kwargs),
            }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'ship_it': {
                'type': bool,
                'description': 'Whether or not to mark the review "Ship It!"',
            },
            'body_top': {
                'type': str,
                'description': 'The review content above the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The review content below the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a review.

        This updates the fields of a draft review. Published reviews cannot
        be updated.

        Only the owner of a review can make changes. One or more fields can
        be updated at once.

        The only special field is ``public``, which, if set to ``1``, will
        publish the review. The review will then be made publicly visible. Once
        public, the review cannot be modified or made private again.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return self._update_review(request, review, *args, **kwargs)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes the draft review.

        This only works for draft reviews, not public reviews. It will
        delete the review and all comments on it. This cannot be undone.

        Only the user who owns the draft can delete it.

        Upon deletion, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on a particular review.

        If the review is not public, then the client's logged in user
        must either be the owner of the review. Otherwise, an error will
        be returned.
        """
        pass

    def _update_review(self, request, review, public=None, *args, **kwargs):
        """Common function to update fields on a draft review."""
        if not self.has_modify_permissions(request, review):
            # Can't modify published reviews or those not belonging
            # to the user.
            return self._no_access_error(request.user)

        for field in ('ship_it', 'body_top', 'body_bottom'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(review, field, value)

        review.save()

        if public:
            review.publish(user=request.user)

        return 200, {
            self.item_result_key: review,
        }
