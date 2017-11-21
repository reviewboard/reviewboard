from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   INVALID_FORM_DATA,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.reviews.features import status_updates_feature
from reviewboard.reviews.models import Review, StatusUpdate
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources


class StatusUpdateResource(WebAPIResource):
    """Provides status updates on review requests.

    A status update is a way for a third-party service or extension to mark
    some kind of status on a review request. Examples of this could include
    static analysis tools or continuous integration services.

    Status updates may optionally be associated with a
    :ref:`change description <webapi2.0-change-resource>`, in which case they
    will be shown in that change description box on the review request page.
    Otherwise, the status update will be shown in a box immediately below the
    review request details.
    """

    required_features = [
        status_updates_feature,
    ]

    model = StatusUpdate
    name = 'status_update'
    fields = {
        'change': {
            'type': 'reviewboard.webapi.resources.change.ChangeResource',
            'description': 'The change to a review request which this status '
                           'update applies to (for example, the change '
                           'adding a diff that was built by CI). If this is '
                           'blank, the status update is for the review '
                           'request as initially published.',
        },
        'description': {
            'type': six.text_type,
            'description': 'A user-visible description of the status update.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the status update. '
                           'This can be set by the API or extensions.',
        },
        'id': {
            'type': int,
            'description': 'The ID of the status update.',
        },
        'review': {
            'type': 'reviewboard.webapi.resources.review.ReviewResource',
            'description': 'A review which corresponds to this status update.',
        },
        'service_id': {
            'type': six.text_type,
            'description': 'A unique identifier for the service providing '
                           'the status update.',
        },
        'state': {
            'type': ('pending', 'done_success', 'done_failure', 'error',
                     'timed-out'),
            'description': 'The current state of the status update.',
        },
        'summary': {
            'type': six.text_type,
            'description': 'A user-visible short summary of the status '
                           'update.',
        },
        'timeout': {
            'type': int,
            'description': 'An optional timeout for pending status updates, '
                           'measured in seconds.',
        },
        'url': {
            'type': six.text_type,
            'description': 'An optional URL to link to for more details about '
                           'the status update.',
        },
        'url_text': {
            'type': six.text_type,
            'description': 'The text to use for the link.',
        },
    }
    uri_object_key = 'status_update_id'
    model_parent_key = 'review_request'
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    added_in = '3.0'

    def has_access_permissions(self, request, status_update, *args, **kwargs):
        """Return whether the user has permissions to access the status update.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            status_update (reviewboard.reviews.models.StatusUpdate):
                The status update to check permissions for.

            *args (tuple):
                Additional arguments (unused).

            **kwargs (dict):
                Additional keyword arguments (unused).

        Returns:
            boolean:
            Whether the user making the request has read access for the status
            update.
        """
        return status_update.review_request.is_accessible_by(request.user)

    def has_modify_permissions(self, request, status_update, *args, **kwargs):
        """Return whether the user has permissions to modify the status update.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            status_update (reviewboard.reviews.models.StatusUpdate):
                The status update to check permissions for.

            *args (tuple):
                Additional arguments (unused).

            **kwargs (dict):
                Additional keyword arguments (unused).

        Returns:
            boolean:
            Whether the user making the request has modify access for the
            status update.
        """
        return status_update.is_mutable_by(request.user)

    def has_delete_permissions(self, request, status_update, *args, **kwargs):
        """Return whether the user has permissions to delete the status update.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            status_update (reviewboard.reviews.models.StatusUpdate):
                The status update to check permissions for.

            *args (tuple):
                Additional arguments (unused).

            **kwargs (dict):
                Additional keyword arguments (unused).

        Returns:
            boolean:
            Whether the user making the request has delete access for the
            status update.
        """
        return status_update.is_mutable_by(request.user)

    def serialize_change_field(self, obj, **kwargs):
        """Return a serialized version of the ``change`` field.

        Args:
            obj (reviewboard.reviews.models.StatusUpdate):
                The status update being serialized.

            **kwargs (dict):
                Additional keyword arguments (unused).

        Returns:
            reviewboard.changedescs.models.ChangeDescription:
            The change description object. This will get serialized as a link
            to the relevant resource.
        """
        return obj.change_description

    def serialize_state_field(self, obj, **kwargs):
        """Return a serialized version of the ``state`` field.

        Args:
            obj (reviewboard.reviews.models.StatusUpdate):
                The status update being serialized.

            **kwargs (dict):
                Additional keyword arguments (unused).

        Returns:
            unicode:
            The serialized state.
        """
        return StatusUpdate.state_to_string(obj.effective_state)

    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'change': {
                'type': int,
                'description': 'The change description to get status updates '
                               'for.'
            },
            'service-id': {
                'type': six.text_type,
                'description': 'The service ID to query for.',
            },
            'state': {
                'type': ('pending', 'done-success', 'done-failure', 'error'),
                'description': 'The state to query for.',
            },
        },
    )
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of status updates on a review request.

        By default, this returns all status updates for the review request.
        """

    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on a single status update."""

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Return a queryset for StatusUpdate models.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            is_list (boolean):
                Whether this query is for the list resource (which supports
                additional query options).

            *args (tuple):
                Additional arguments to be passed to parent resources.

            **kwargs (dict):
                Additional keyword arguments to be passed to parent resources.

        Returns:
            django.db.models.query.QuerySet:
            A QuerySet containing the matching status updates.
        """
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)

        q = Q()

        if is_list:

            if 'change' in request.GET:
                q = q & Q(change_description=int(request.GET.get('change')))

            if 'service-id' in request.GET:
                q = q & Q(service_id=request.GET.get('service-id'))

            if 'state' in request.GET:
                q = q & Q(state=StatusUpdate.string_to_state(
                    request.GET.get('state')))

        return review_request.status_updates.filter(q)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required={
            'service_id': {
                'type': six.text_type,
                'description': 'A unique identifier for the service providing '
                               'the status update.',
            },
            'summary': {
                'type': six.text_type,
                'description': 'A user-visible short summary of the status '
                               'update.',
            },
        },
        optional={
            'change_id': {
                'type': int,
                'description': 'The change to a review request which this '
                               'status update applies to (for example, the '
                               'change adding a diff that was built by CI). '
                               'If this is blank, the status update is for '
                               'the review request as initially published.',
            },
            'description': {
                'type': six.text_type,
                'description': 'A user-visible description of the status '
                               'update.',
            },
            'review_id': {
                'type': int,
                'description': 'A review which corresponds to this status '
                               'update.',
            },
            'state': {
                'type': ('pending', 'done-success', 'done-failure', 'error'),
                'description': 'The current state of the status update.',
            },
            'timeout': {
                'type': int,
                'description': 'An optional timeout for pending status '
                               'updates, measured in seconds.',
            },
            'url': {
                'type': six.text_type,
                'description': 'A URL to link to for more details about '
                               'the status update.',
            },
            'url_text': {
                'type': six.text_type,
                'description': 'The text to use for the link.',
            },
        },
        allow_unknown=True
    )
    def create(self, request, state='pending', extra_fields={},
               *args, **kwargs):
        """Creates a new status update.

        At a minimum, the service ID and a summary must be provided.

        If desired, the new status update can be associated with a change
        description and/or a review. If a change description is included, this
        status update will be displayed in the review request page within that
        change description's box. If a review is attached, once that review is
        published, it will appear alongside the status update.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        status_update = self.model(review_request=review_request,
                                   user=request.user)

        return self._update_status(status_update, extra_fields,
                                   state=state, **kwargs)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'change_id': {
                'type': int,
                'description': 'The change to a review request which this '
                               'status update applies to (for example, the '
                               'change adding a diff that was built by CI). '
                               'If this is blank, the status update is for '
                               'the review request as initially published.',
            },
            'description': {
                'type': six.text_type,
                'description': 'A user-visible description of the status '
                               'update.',
            },
            'review_id': {
                'type': int,
                'description': 'A review which corresponds to this status '
                               'update.',
            },
            'service_id': {
                'type': six.text_type,
                'description': 'A unique identifier for the service providing '
                               'the status update.',
            },
            'state': {
                'type': ('pending', 'done-success', 'done-failure', 'error'),
                'description': 'The current state of the status update.',
            },
            'summary': {
                'type': six.text_type,
                'description': 'A user-visible short summary of the status '
                               'update.',
            },
            'timeout': {
                'type': int,
                'description': 'An optional timeout for pending status '
                               'updates, measured in seconds.',
            },
            'url': {
                'type': six.text_type,
                'description': 'A URL to link to for more details about '
                               'the status update.',
            },
            'url_text': {
                'type': six.text_type,
                'description': 'The text to use for the link.',
            },
        },
        allow_unknown=True
    )
    def update(self, request, extra_fields={}, *args, **kwargs):
        """Updates the status update.

        Only the owner of a status update can make changes. One or more fields
        can be updated at once.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            status_update = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, status_update):
            return self.get_no_access_error(request)

        return self._update_status(status_update, extra_fields, **kwargs)

    def _update_status(self, status_update, extra_fields, **kwargs):
        """Update the fields of the StatusUpdate model.

        Args:
            status_update (reviewboard.reviews.models.StatusUpdate):
                The status update to modify.

            extra_fields (dict):
                Any additional fields to update into the status update's
                ``extra_data`` field.

            **kwargs (dict):
                A dictionary of field names and new values to update.
        """
        for field_name in ('description', 'service_id', 'summary', 'timeout',
                           'url', 'url_text'):
            if field_name in kwargs:
                setattr(status_update, field_name, kwargs[field_name])

        if 'state' in kwargs:
            status_update.state = StatusUpdate.string_to_state(kwargs['state'])

        if 'change_id' in kwargs:
            try:
                status_update.change_description = \
                    ChangeDescription.objects.get(pk=kwargs['change_id'])
            except ChangeDescription.DoesNotExist:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'change_id': ['Invalid change description ID'],
                    },
                }

        if 'review_id' in kwargs:
            try:
                status_update.review = \
                    Review.objects.get(pk=kwargs['review_id'])
            except Review.DoesNotExist:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'review_id': ['Invalid review ID'],
                    },
                }

        try:
            self.import_extra_data(status_update, status_update.extra_data,
                                   extra_fields)
        except ImportExtraDataError as e:
            return e.error_payload

        if status_update.pk is None:
            code = 201
        else:
            code = 200

        status_update.save()

        return code, {
            self.item_result_key: status_update,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Deletes the status update permanently.

        After a successful delete, this will return :http:`204`.
        """
        try:
            status_update = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, status_update,
                                           *args, **kwargs):
            return self.get_no_access_error(request)

        status_update.delete()

        return 204, {}


status_update_resource = StatusUpdateResource()
