from __future__ import unicode_literals

from django.utils import six
from djblets.db.query import LocalDataQuerySet
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.responses import WebAPIResponsePaginated

from reviewboard.hostingsvcs.repository import RemoteRepository
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.resources import resources


class RemoteRepositoryResponsePaginated(WebAPIResponsePaginated):
    """Provides paginated reponses for lists of RemoteRepository objects.

    This is a specialization of WebAPIResponsePaginated designed to
    return lsits of RemoteRepository objects and to handle pagination in
    a way that's compatible with the pagination models of HostingService.
    """
    def __init__(self, request, queryset, *args, **kwargs):
        self.paginator = queryset[0]

        super(RemoteRepositoryResponsePaginated, self).__init__(
            request, queryset=None, *args, **kwargs)

    def has_prev(self):
        return self.paginator.has_prev

    def has_next(self):
        return self.paginator.has_next

    def get_prev_index(self):
        return max(self.start - 1, 0)

    def get_next_index(self):
        return self.start + 1

    def get_results(self):
        return self.paginator.page_data

    def get_total_results(self):
        return None

    def build_pagination_url(self, full_path, start, max_results,
                             query_parameters):
        return '%s?start=%s%s' % (full_path, start, query_parameters)


class RemoteRepositoryResource(WebAPIResource):
    """Returns information on remote repositories on a hosting service.

    This can be used to look up the information needed to connect to a
    remote repository or to add a repository to Review Board. Only remote
    repositories that are accessible to the linked hosting service account
    (i.e., that of the parent resource) will be provided by this resource.
    """
    added_in = '2.5'

    name = 'remote_repository'
    name_plural = 'remote_repositories'

    model = RemoteRepository
    model_object_key = 'id'
    model_parent_key = 'hosting_service_account'
    uri_object_key = 'repository_id'
    uri_object_key_regex = r'[A-Za-z0-9_./-]+'

    paginated_cls = RemoteRepositoryResponsePaginated

    fields = {
        'id': {
            'type': six.text_type,
            'description': 'The unique ID for this repository on the '
                           'hosting service.',
        },
        'name': {
            'type': six.text_type,
            'description': 'The name of the repository.',
        },
        'owner': {
            'type': six.text_type,
            'description': 'The owner of the repository, which may be a user '
                           'account or an organization, depending on the '
                           'service.',
        },
        'scm_type': {
            'type': six.text_type,
            'description': 'The type of repository, mapping to registered '
                           'SCMTools on Review Board.',
        },
        'path': {
            'type': six.text_type,
            'description': 'The repository path as recommended by the hosting '
                           'service.',
        },
        'mirror_path': {
            'type': six.text_type,
            'description': 'A secondary path that can be used to reach the '
                           'repository.',
        },
    }
    uri_object_key = 'repository_id'
    autogenerate_etags = True

    allowed_methods = ('GET',)

    def has_list_access_permissions(self, request, *args, **kwargs):
        account = resources.hosting_service_account.get_object(
            request, *args, **kwargs)

        # Only allow administrators or those with the ability to modify the
        # account to see what repositories are listed.
        return account.is_mutable_by(request.user)

    def has_access_permissions(self, request, remote_repository,
                               *args, **kwargs):
        # Only allow administrators or those with the ability to modify the
        # account to see what repositories are listed.
        return remote_repository.hosting_service_account.is_mutable_by(
            request.user)

    def get_queryset(self, request, start=None, is_list=False,
                     repository_id=None, *args, **kwargs):
        account = resources.hosting_service_account.get_object(
            request, *args, **kwargs)

        if is_list:
            # Wrap the paginator in a LocalDataQuerySet, so that we can get
            # to it later in RemoteRepositoryResponsePaginated.
            lookup_kwargs = {}

            for name in ('owner', 'owner-type', 'filter-type'):
                if kwargs.get(name):
                    arg = name.replace('-', '_')
                    lookup_kwargs[arg] = kwargs[name]

            result = account.service.get_remote_repositories(start=start,
                                                             **lookup_kwargs)
        else:
            result = account.service.get_remote_repository(repository_id)

        return LocalDataQuerySet([result])

    def get_serializer_for_object(self, obj):
        if isinstance(obj, RemoteRepository):
            return self

        return super(RemoteRepositoryResource, self).get_serializer_for_object(
            obj)

    # NOTE: We're not augmenting from any resources, because we don't want to
    #       include ?counts-only= or ?max-results=, and we have a different
    #       ?start=. Because of this, we need to be careful to apply our own
    #       decorators.
    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'owner': {
                'type': six.text_type,
                'description': 'The owner (user account or organization) '
                               'to look up repositories for. Defaults to '
                               'the owner of the hosting service account.',
            },
            'owner-type': {
                'type': six.text_type,
                'description': 'Indicates what sort of account the owner '
                               'represents. This may be required by some '
                               'services, and the values are dependent on '
                               'that service.',
            },
            'filter-type': {
                'type': six.text_type,
                'description': 'Filters the list of results. Allowed values '
                               'are dependent on the hosting service. '
                               'Unexpected values will be ignored.',
            },
            'start': {
                'type': int,
                'description': 'The 0-based index of the first page of '
                               'results to fetch.',
            },
        },
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Returns the list of remote repositories on the hosting service.

        Different hosting service backends have different criteria for
        performing the lookups. Some hosting services have multiple types of
        owners, specified by passing ``owner-type``. Filtering may also be
        possible by passing ``filter-type``. Performing lookups requires
        knowing the possible values for the service ahead of time and passing
        the proper parameters in the query string.

        Pagination works a bit differently for this resource than most.
        Instead of ``?start=`` taking an index into the number of results,
        this resource's ``?start=`` takes a 0-based index of the page of
        results.

        ``?max-results=`` and ``?counts-only=`` are not supported, as they're
        not compatible with all hosting services.

        Callers should always use the ``next`` and ``prev`` links for
        navigation, and should not build page indexes themselves.
        """
        return super(RemoteRepositoryResource, self).get_list(
            request, *args, **kwargs)

    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Provides information on a particular remote repository.

        If the remote repository exists and is accessible by the linked
        hosting service account (that of the parent resource), then the
        details of that repository will be returned in the payload.

        The ID expected for the lookup in the URL is specific to the type
        of hosting service.
        """
        pass


remote_repository_resource = RemoteRepositoryResource()
