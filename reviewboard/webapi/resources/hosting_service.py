from __future__ import unicode_literals

import inspect

from django.utils import six
from djblets.db.query import LocalDataQuerySet
from djblets.util.decorators import augment_method_from
from djblets.webapi.fields import (BooleanFieldType,
                                   ListFieldType,
                                   StringFieldType)

from reviewboard.hostingsvcs.service import (get_hosting_services,
                                             HostingService)
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.resources import resources


class HostingServiceResource(WebAPIResource):
    """Provides information on registered hosting services.

    Review Board has a list of supported remote hosting services for
    repositories and bug trackers. These hosting services contain the
    information needed for Review Board to link with any repositories hosted
    on that service and access content for display in the diff viewer.

    This resource allows for querying that list and determining what
    capabilities of the hosting service can be used by Review Board.
    """
    added_in = '2.5'

    name = 'hosting_service'
    model_object_key = 'hosting_service_id'
    model = HostingService
    uri_object_key = 'hosting_service_id'
    uri_object_key_regex = r'[a-z0-9_-]+'

    fields = {
        'id': {
            'type': StringFieldType,
            'description': "The hosting service's unique ID.",
        },
        'name': {
            'type': StringFieldType,
            'description': 'The name of the hosting service.',
        },
        'needs_authorization': {
            'type': BooleanFieldType,
            'description': 'Whether an account must be authorized and linked '
                           'in order to use this service.',
        },
        'self_hosted': {
            'type': BooleanFieldType,
            'description': 'Whether the service is meant to be self-hosted '
                           'in the network.',
        },
        'plans': {
            'type': dict,
            'description': (
                'Information on account configuration plans supported by '
                'the hosting service. These correspond to the '
                '``repository_plan`` field used when creating or updating a '
                'repository (see :ref:`webapi2.0-repository-list-resource`). '
                'This is not used for all services.'
            ),
            'added_in': '3.0.19',
        },
        'supported_scmtools': {
            'type': ListFieldType,
            'items': {
                'type': StringFieldType,
            },
            'description': 'The comprehensive list of repository types '
                           'suppported by Review Board. Each of these is a '
                           'registered SCMTool ID or human-readable name.\n'
                           '\n'
                           'Some of these may not be supported by the service '
                           'anymore. See ``visible_scmtools``.'
        },
        'supports_bug_trackers': {
            'type': BooleanFieldType,
            'description': 'Whether bug trackers are available.',
        },
        'supports_list_remote_repositories': {
            'type': BooleanFieldType,
            'description': 'Whether remote repositories on the hosting '
                           'service can be listed through the API.',
        },
        'supports_repositories': {
            'type': BooleanFieldType,
            'description': 'Whether repository linking is supported.',
        },
        'supports_two_factor_auth': {
            'type': BooleanFieldType,
            'description': 'Whether two-factor authentication is supported '
                           'when linking an account.',
        },
        'visible_scmtools': {
            'type': ListFieldType,
            'items': {
                'type': StringFieldType,
            },
            'description': 'The list of repository types that are shown by '
                           'Review Board when configuring a new repository. '
                           'Each of these is a registered SCMTool ID or '
                           'human-readable name.',
            'added_in': '3.0.17',
        },
    }

    def serialize_id_field(self, hosting_service, *args, **kwargs):
        return hosting_service.hosting_service_id

    def serialize_plans_field(self, hosting_service, *args, **kwargs):
        """Serialize the plans field.

        This will convert the existing :py:attr:`HostingService.plans
        <reviewboard.hostingsvcs.service.HostingService.plans>` field (or
        create a new one if the service doesn't support multiple plans) into
        a more slimmed-down payload that can be transmitted via the API.

        Args:
            hosting_service (reviewboard.hostingsvcs.service.HostingService):
                The hosting service being serialized.

            *args (tuple, unused):
                Additional positional arguments.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            dict:
            The serialized plan information.
        """
        plans = hosting_service.plans
        default_form = hosting_service.form

        if not plans:
            plans = [
                ('', {
                    'name': 'Default',
                    'fields': default_form,
                }),
            ]

        return {
            plan_id: {
                'name': info['name'],
                'fields': {
                    field_name: {
                        'name': field.label,
                        'required': field.required,
                        'help_text': field.help_text,
                    }
                    for field_name, field in six.iteritems(
                        info.get('form', default_form).base_fields)
                },
            }
            for plan_id, info in plans
        }

    def serialize_visible_scmtools_field(self, hosting_service, *args,
                                         **kwargs):
        """Serialize the visible_scmtools field on the hosting service.

        Args:
            hosting_service (reviewboard.hostingsvcs.service.HostingService):
                The hosting service being serialized.

            *args (tuple, unused):
                Additional positional arguments.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            list of unicode:
            The list of visible SCMTools.
        """
        # If the hosting service does not explicitly define this, it will be
        # None. We need to then return the list of supported SCMTools.
        scmtools = hosting_service.visible_scmtools

        if scmtools is None:
            scmtools = hosting_service.supported_scmtools

        return scmtools

    def has_list_access_permissions(self, *args, **kwargs):
        return True

    def has_access_permissions(self, *args, **kwargs):
        return True

    def get_queryset(self, request, *args, **kwargs):
        return LocalDataQuerySet(get_hosting_services())

    def get_serializer_for_object(self, obj):
        if inspect.isclass(obj) and issubclass(obj, HostingService):
            return self

        return super(HostingServiceResource, self).get_serializer_for_object(
            obj)

    def get_links(self, items, obj=None, *args, **kwargs):
        links = super(HostingServiceResource, self).get_links(
            items, obj, *args, **kwargs)

        if obj:
            request = kwargs.get('request')

            accounts_url = resources.hosting_service_account.get_list_url(
                local_site_name=request._local_site_name)
            repos_url = resources.repository.get_list_url(
                local_site_name=request._local_site_name)

            links.update({
                'accounts': {
                    'method': 'GET',
                    'href': request.build_absolute_uri(
                        '%s?service=%s' % (accounts_url,
                                           obj.hosting_service_id)
                    ),
                },
                'repositories': {
                    'method': 'GET',
                    'href': request.build_absolute_uri(
                        '%s?hosting-service=%s'
                        % (repos_url, obj.hosting_service_id)
                    ),
                }
            })

        return links

    @augment_method_from(WebAPIResource)
    def get_list(self, request, *args, **kwargs):
        """Lists all the hosting services supported by Review Board.

        Unlike most resources, this will not be paginated. The number of
        hosting services will be small, and it's useful to get them all in
        one request.
        """
        pass

    @augment_method_from(WebAPIResource)
    def get(self, request, *args, **kwargs):
        """Returns information on a particular hosting service.

        This will cover the capabilities of the hosting service, and
        information needed to help link repositories and bug trackers
        hosted on it.
        """
        pass


hosting_service_resource = HostingServiceResource()
