"""API resource for managing hosting service accounts."""

from __future__ import annotations

from typing import Optional, Sequence, TYPE_CHECKING

from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (INVALID_FORM_DATA, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import IntFieldType, StringFieldType

from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.forms import HostingServiceAuthForm
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import (BAD_HOST_KEY,
                                       HOSTINGSVC_AUTH_ERROR,
                                       REPO_AUTHENTICATION_ERROR,
                                       SERVER_CONFIG_ERROR,
                                       UNVERIFIED_HOST_CERT,
                                       UNVERIFIED_HOST_KEY)
from reviewboard.webapi.resources import resources

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest
    from djblets.webapi.responses import WebAPIResponseLinks
    from djblets.webapi.resources.base import WebAPIResourceHandlerResult


class HostingServiceAccountResource(WebAPIResource):
    """Provides information and allows linking of hosting service accounts.

    The list of accounts tied to hosting services can be retrieved, and new
    accounts can be linked through an HTTP POST.
    """

    item_resource_added_in = '1.6.7'
    list_resource_added_in = '2.5'

    name = 'hosting_service_account'
    model = HostingServiceAccount
    fields = {
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the hosting service account.',
        },
        'username': {
            'type': StringFieldType,
            'description': 'The username of the account.',
        },
        'service': {
            'type': StringFieldType,
            'description': 'The ID of the service this account is on.',
        },
    }
    uri_object_key = 'account_id'

    allowed_methods = ('GET', 'POST')

    item_child_resources = [
        resources.remote_repository,
    ]

    @webapi_check_login_required
    def get_queryset(
        self,
        request: HttpRequest,
        local_site_name: Optional[str] = None,
        is_list: bool = False,
        *args,
        **kwargs,
    ) -> QuerySet[HostingServiceAccount]:
        """Return a queryset for the resource.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            local_site_name (str, optional):
                The name of the current Local Site, if present.

            is_list (bool, optional):
                Whether to return a list queryset.

            *args (tuple):
                Positional arguments parsed from the URL.

            **kwargs (dict):
                Keyword arguments parsed from the URL.
        """
        local_site = self._get_local_site(local_site_name)

        queryset = self.model.objects.accessible(visible_only=True,
                                                 local_site=local_site)

        if is_list:
            if 'username' in request.GET:
                queryset = queryset.filter(username=request.GET['username'])

            if 'service' in request.GET:
                queryset = queryset.filter(service_name=request.GET['service'])

        return queryset

    def has_access_permissions(
        self,
        request: HttpRequest,
        account: HostingServiceAccount,
        *args,
        **kwargs,
    ) -> bool:
        """Return whether the account is accessible by a user.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The hosting service account to check.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            bool:
            Whether the hosting service account can be accessed by the user.
        """
        return account.is_accessible_by(request.user)

    def has_modify_permissions(
        self,
        request: HttpRequest,
        account: HostingServiceAccount,
        *args,
        **kwargs,
    ) -> bool:
        """Return whether the account is mutable by a user.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The hosting service account to check.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            bool:
            Whether the hosting service account can be modified by the user.
        """
        return account.is_mutable_by(request.user)

    def has_delete_permissions(
        self,
        request: HttpRequest,
        account: HostingServiceAccount,
        *args,
        **kwargs,
    ) -> bool:
        """Return whether the account can be deleted by a user.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The hosting service account to check.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            bool:
            Whether the hosting service account can be deleted by the user.
        """
        return account.is_mutable_by(request.user)

    def get_links(
        self,
        resources: Sequence[WebAPIResource] = [],
        obj: Optional[HostingServiceAccount] = None,
        *args,
        **kwargs,
    ) -> WebAPIResponseLinks:
        """Return links for the resource.

        Args:
            resources (list of reviewboard.webapi.base.WebAPIResource):
                A list of resources to include links to.

            obj (reviewboard.hostingsvcs.models.HostingServiceAccount,
                 optional):
                The current hosting service account, if accessing an item
                resource.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            djblets.webapi.responses.WebAPIResponseLinks:
            The links to include in the payload.
        """
        links = super().get_links(resources, obj=obj, *args, **kwargs)

        if obj:
            service = obj.service

            if not service.supports_list_remote_repositories:
                del links['remote_repositories']

        return links

    @webapi_request_fields(optional={
        'username': {
            'type': StringFieldType,
            'description': 'Filter accounts by username.',
            'added_in': '2.5',
        },
        'service': {
            'type': StringFieldType,
            'description': 'Filter accounts by the hosting service ID.',
            'added_in': '2.5',
        },
    })
    @augment_method_from(WebAPIResource)
    def get_list(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> WebAPIResourceHandlerResult:
        """Retrieves the list of accounts on the server.

        This will only list visible accounts. Any account that the
        administrator has hidden will be excluded from the list.
        """
        ...

    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs) -> WebAPIResourceHandlerResult:
        """Retrieves information on a particular account.

        This will only return very basic information on the account.
        Authentication information is not provided.
        """
        ...

    def serialize_service_field(
        self,
        obj: HostingServiceAccount,
        **kwargs,
    ) -> str:
        """Serialize the ``service`` field.

        Args:
            obj (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The hosting service account.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            str:
            The serialized content for the service field.
        """
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
                'type': StringFieldType,
                'description': 'The username on the account.',
            },
            'service_id': {
                'type': StringFieldType,
                'description': 'The registered ID of the service for the '
                               'account.',
            },
        },
        optional={
            'hosting_url': {
                'type': StringFieldType,
                'description': 'The hosting URL on the account, if the '
                               'hosting service is self-hosted.',
                'added_in': '1.7.8',
            },
            'password': {
                'type': StringFieldType,
                'description': 'The password on the account, if the hosting '
                               'service needs it.',
            },
        },
        allow_unknown=True,
    )
    def create(
        self,
        request: HttpRequest,
        username: str,
        service_id: str,
        *,
        password: Optional[str] = None,
        hosting_url: Optional[str] = None,
        local_site_name: Optional[str] = None,
        extra_fields: dict[str, str],
        **kwargs,
    ) -> WebAPIResourceHandlerResult:
        """Creates a hosting service account.

        The ``service_id`` is a registered HostingService ID. This must be
        known beforehand, and can be looked up in the Review Board
        administration UI.

        Depending on the hosting service, other parameters may be required.
        These can include API keys or two-factor auth tokens, and is dependent
        on each type of service. If a service requires additional fields,
        making requests to this API method will return an error indicating what
        fields are missing.
        """
        local_site = self._get_local_site(local_site_name)

        if not HostingServiceAccount.objects.can_create(request.user,
                                                        local_site):
            return self.get_no_access_error(request)

        # Validate the service.
        service = hosting_service_registry.get_hosting_service(service_id)

        if not service:
            return INVALID_FORM_DATA, {
                'fields': {
                    'service': ['This is not a valid service name'],
                },
            }

        if service.self_hosted and not hosting_url:
            return INVALID_FORM_DATA, {
                'fields': {
                    'hosting_url': ['This field is required'],
                },
            }

        if service.needs_authorization:
            form_cls = service.auth_form or HostingServiceAuthForm
            form = form_cls(
                {
                    'hosting_account_password': password,
                    'hosting_account_username': username,
                    'hosting_url': hosting_url,
                    **extra_fields,
                },
                hosting_service_cls=service,
                local_site=local_site)

            if not form.is_valid():
                invalid_fields: dict[str, list[str]] = {}

                for field_name, errors in form.errors.items():
                    invalid_fields[field_name] = [
                        ', '.join(error.messages)
                        for error in errors.as_data()
                    ]

                return INVALID_FORM_DATA, {
                    'fields': invalid_fields,
                }

            try:
                account = form.save()
            except Exception as e:
                return HOSTINGSVC_AUTH_ERROR, {
                    'reason': str(e),
                }
        else:
            account = HostingServiceAccount(service_name=service_id,
                                            username=username,
                                            hosting_url=hosting_url,
                                            local_site=local_site)

            account.save()

        return 201, {
            self.item_result_key: account,
        }


hosting_service_account_resource = HostingServiceAccountResource()
