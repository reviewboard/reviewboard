from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.reviews.models import ReviewRequest
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources


class BaseArchivedObjectResource(WebAPIResource):
    """A base resource for objects archived or muted by a user."""

    added_in = '2.5'
    name = None
    model_parent_key = 'user'
    uri_object_key = 'review_request_id'
    visibility = None

    allowed_methods = ('POST', 'DELETE')

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(required={
        'object_id': {
            'type': six.text_type,
            'description': 'The ID of the object to hide.',
        },
    })
    def create(self, request, object_id, *args, **kwargs):
        """Handle HTTP POST operations."""
        try:
            obj_kwargs = kwargs.copy()
            obj_kwargs[self.uri_object_key] = object_id
            review_request = resources.review_request.get_object(
                request, *args, **obj_kwargs)
            user = resources.user.get_object(request, *args, **kwargs)
        except (ReviewRequest.DoesNotExist, User.DoesNotExist):
            return DOES_NOT_EXIST

        visit, is_new = ReviewRequestVisit.objects.get_or_create(
            user=user,
            review_request=review_request,
            defaults={
                'visibility': self.visibility,
            })

        if not is_new and visit.visibility != self.visibility:
            visit.visibility = self.visibility
            visit.save(update_fields=['visibility'])

        return 201, {
            self.item_result_key: review_request,
        }

    @webapi_check_local_site
    @webapi_login_required
    def delete(self, request, review_request_id, *args, **kwargs):
        """Handle HTTP DELETE operations."""
        try:
            obj_kwargs = kwargs.copy()
            obj_kwargs[self.uri_object_key] = review_request_id
            review_request = resources.review_request.get_object(
                request, *args, **obj_kwargs)
            user = resources.user.get_object(request, *args, **kwargs)
        except (ReviewRequest.DoesNotExist, User.DoesNotExist):
            return DOES_NOT_EXIST

        if not resources.user.has_modify_permissions(request, user,
                                                     *args, **kwargs):
            return self.get_no_access_error(request)

        visit, is_new = ReviewRequestVisit.objects.get_or_create(
            user=user,
            review_request=review_request,
            defaults={
                'visibility': self.visibility,
            })

        if not is_new and visit.visibility == self.visibility:
            visit.visibility = ReviewRequestVisit.VISIBLE
            visit.save(update_fields=['visibility'])

        return 204, {}
