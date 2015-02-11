from __future__ import unicode_literals

from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (INVALID_FORM_DATA, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import (BAD_HOST_KEY,
                                       HOSTINGSVC_AUTH_ERROR,
                                       REPO_AUTHENTICATION_ERROR,
                                       SERVER_CONFIG_ERROR,
                                       UNVERIFIED_HOST_CERT,
                                       UNVERIFIED_HOST_KEY)


class HostingServiceAccountResource(WebAPIResource):
    """Provides information and allows linking of hosting service accounts.

    The list of accounts tied to hosting services can be retrieved, and new
    accounts can be linked through an HTTP POST.
    """
    name = 'hosting_service_account'
    model = HostingServiceAccount
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the hosting service account.',
        },
        'username': {
            'type': six.text_type,
            'description': 'The username of the account.',
        },
        'service': {
            'type': six.text_type,
            'description': 'The ID of the service this account is on.',
        },
    }
    uri_object_key = 'account_id'

    allowed_methods = ('GET', 'POST',)

    @webapi_check_login_required
    def get_queryset(self, request, local_site_name=None, *args, **kwargs):
        local_site = self._get_local_site(local_site_name)
        return self.model.objects.accessible(visible_only=True,
                                             local_site=local_site)

    def has_access_permissions(self, request, account, *args, **kwargs):
        return account.is_accessible_by(request.user)

    def has_modify_permissions(self, request, account, *args, **kwargs):
        return account.is_mutable_by(request.user)

    def has_delete_permissions(self, request, account, *args, **kwargs):
        return account.is_mutable_by(request.user)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, request, *args, **kwargs):
        """Retrieves the list of accounts on the server.

        This will only list visible accounts. Any account that the
        administrator has hidden will be excluded from the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information on a particular account.

        This will only return very basic information on the account.
        Authentication information is not provided.
        """
        pass

    def serialize_service_field(self, obj, **kwargs):
        return obj.service_name

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(BAD_HOST_KEY, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED, REPO_AUTHENTICATION_ERROR,
                            SERVER_CONFIG_ERROR, UNVERIFIED_HOST_CERT,
                            UNVERIFIED_HOST_KEY)
    @webapi_request_fields(
        required={
            'username': {
                'type': six.text_type,
                'description': 'The username on the account.',
            },
            'service_id': {
                'type': six.text_type,
                'description': 'The registered ID of the service for the '
                               'account.',
            },
        },
        optional={
            'hosting_url': {
                'type': six.text_type,
                'description': 'The hosting URL on the account, if the '
                               'hosting service is self-hosted.',
            },
            'password': {
                'type': six.text_type,
                'description': 'The password on the account, if the hosting '
                               'service needs it.',
            },
        }
    )
    def create(self, request, username, service_id, password=None,
               hosting_url=None, local_site_name=None, *args, **kwargs):
        """Creates a hosting service account.

        The ``service_id`` is a registered HostingService ID. This must be
        known beforehand, and can be looked up in the Review Board
        administration UI.
        """
        local_site = self._get_local_site(local_site_name)

        if not HostingServiceAccount.objects.can_create(request.user,
                                                        local_site):
            return self._no_access_error(request.user)

        # Validate the service.
        service = get_hosting_service(service_id)

        if not service:
            return INVALID_FORM_DATA, {
                'fields': {
                    'service': ['This is not a valid service name'],
                }
            }

        if service.self_hosted and not hosting_url:
            return INVALID_FORM_DATA, {
                'fields': {
                    'hosting_url': ['This field is required'],
                }
            }

        account = HostingServiceAccount(service_name=service_id,
                                        username=username,
                                        hosting_url=hosting_url,
                                        local_site=local_site)
        service = account.service

        if service.needs_authorization:
            try:
                service.authorize(request, username, password, hosting_url,
                                  local_site_name)
            except AuthorizationError as e:
                return HOSTINGSVC_AUTH_ERROR, {
                    'reason': six.text_type(e),
                }

        service.save()

        return 201, {
            self.item_result_key: account,
        }


hosting_service_account_resource = HostingServiceAccountResource()
