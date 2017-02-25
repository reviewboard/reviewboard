from __future__ import unicode_literals

import json

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import six
from django.utils.translation import ugettext as _
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED,
                                   WebAPITokenGenerationError)

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import TOKEN_GENERATION_FAILED
from reviewboard.webapi.models import WebAPIToken
from reviewboard.webapi.resources import resources


class APITokenResource(WebAPIResource):
    """Manages the tokens used to access the API.

    This resource allows callers to retrieve their list of tokens, register
    new tokens, delete old ones, and update information on existing tokens.
    """
    model = WebAPIToken
    name = 'api_token'
    verbose_name = 'API Token'

    api_token_access_allowed = False

    added_in = '2.5'

    fields = {
        'id': {
            'type': six.text_type,
            'description': 'The numeric ID of the token entry.',
        },
        'token': {
            'type': six.text_type,
            'description': 'The token value.',
        },
        'time_added': {
            'type': six.text_type,
            'description': 'The date and time that the token was added '
                           '(in ``YYYY-MM-DD HH:MM:SS`` format).',
        },
        'last_updated': {
            'type': six.text_type,
            'description': 'The date and time that the token was last '
                           'updated (in ``YYYY-MM-DD HH:MM:SS`` format).',
        },
        'note': {
            'type': six.text_type,
            'description': 'The note explaining the purpose of this token.',
        },
        'policy': {
            'type': dict,
            'description': 'The access policies defined for this token.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the token. '
                           'This can be set by the API or extensions.',
        },
    }

    uri_object_key = 'api_token_id'
    last_modified_field = 'last_updated'
    model_parent_key = 'user'

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get_queryset(self, request, local_site_name=None, *args, **kwargs):
        user = resources.user.get_object(
            request, local_site_name=local_site_name, *args, **kwargs)

        local_site = self._get_local_site(local_site_name)

        return self.model.objects.filter(user=user, local_site=local_site)

    def has_list_access_permissions(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True

        user = resources.user.get_object(request, *args, **kwargs)
        return user == request.user

    def has_access_permissions(self, request, token, *args, **kwargs):
        return token.is_accessible_by(request.user)

    def has_modify_permissions(self, request, token, *args, **kwargs):
        return token.is_mutable_by(request.user)

    def has_delete_permissions(self, request, token, *args, **kwargs):
        return token.is_deletable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED, TOKEN_GENERATION_FAILED)
    @webapi_request_fields(
        required={
            'note': {
                'type': six.text_type,
                'description': 'The note explaining the purpose of '
                               'this token.',
            },
            'policy': {
                'type': six.text_type,
                'description': 'The token access policy, encoded as a '
                               'JSON string.',
            },
        },
        allow_unknown=True
    )
    def create(self, request, note, policy, extra_fields={},
               local_site_name=None, *args, **kwargs):
        """Registers a new API token.

        The token value be generated and returned in the payload.

        Callers are expected to provide a note and a policy.

        Note that this may, in theory, fail due to too many token collisions.
        If that happens, please re-try the request.
        """
        try:
            user = resources.user.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_list_access_permissions(request, *args, **kwargs):
            return self.get_no_access_error(request)

        try:
            self._validate_policy(policy)
        except ValueError as e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'policy': six.text_type(e),
                },
            }

        local_site = self._get_local_site(local_site_name)

        try:
            token = WebAPIToken.objects.generate_token(user,
                                                       note=note,
                                                       policy=policy,
                                                       local_site=local_site)
        except WebAPITokenGenerationError as e:
            return TOKEN_GENERATION_FAILED.with_message(six.text_type(e))

        if extra_fields:
            self.import_extra_data(token, token.extra_data, extra_fields)
            token.save()

        return 201, {
            self.item_result_key: token,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'note': {
                'type': six.text_type,
                'description': 'The note explaining the purpose of '
                               'this token.',
            },
            'policy': {
                'type': six.text_type,
                'description': 'The token access policy, encoded as a '
                               'JSON string.',
            },
        },
        allow_unknown=True
    )
    def update(self, request, extra_fields={}, *args, **kwargs):
        """Updates the information on an existing API token.

        The note, policy, and extra data on the token may be updated.
        """
        try:
            token = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, token, *args, **kwargs):
            return self.get_no_access_error(request)

        if 'note' in kwargs:
            token.note = kwargs['note']

        if 'policy' in kwargs:
            try:
                token.policy = self._validate_policy(kwargs['policy'])
            except ValidationError as e:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'policy': e.message,
                    },
                }

        if extra_fields:
            self.import_extra_data(token, token.extra_data, extra_fields)

        token.save()

        return 200, {
            self.item_result_key: token,
        }

    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Delete the API token, invalidating all clients using it.

        The API token will be removed from the user's account, and will no
        longer be usable for authentication.

        After deletion, this will return a :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves a list of API tokens belonging to a user.

        If accessing this API on a Local Site, the results will be limited
        to those associated with that site.

        This can only be accessed by the owner of the tokens, or superusers.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information on a particular API token.

        This can only be accessed by the owner of the tokens, or superusers.
        """
        pass

    def _validate_policy(self, policy_str):
        try:
            policy = json.loads(policy_str)
        except Exception as e:
            raise ValidationError(
                _('The policy is not valid JSON: %s')
                % six.text_type(e))

        self.model.validate_policy(policy)

        return policy


api_token_resource = APITokenResource()
