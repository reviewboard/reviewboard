from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)
from djblets.webapi.fields import (BooleanFieldType,
                                   IntFieldType,
                                   StringFieldType)

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import (BAD_HOST_KEY,
                                       MISSING_REPOSITORY,
                                       MISSING_USER_KEY,
                                       REPO_AUTHENTICATION_ERROR,
                                       REPO_INFO_ERROR,
                                       REPOSITORY_ALREADY_EXISTS,
                                       SERVER_CONFIG_ERROR,
                                       UNVERIFIED_HOST_CERT,
                                       UNVERIFIED_HOST_KEY)
from reviewboard.webapi.mixins import UpdateFormMixin
from reviewboard.webapi.resources import resources


class RepositoryResource(UpdateFormMixin, WebAPIResource):
    """Provides information on a registered repository.

    Review Board has a list of known repositories, which can be modified
    through the site's administration interface. These repositories contain
    the information needed for Review Board to access the files referenced
    in diffs.
    """

    model = Repository
    form_class = RepositoryForm

    name_plural = 'repositories'
    fields = {
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the repository.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the repository. Some of '
                           'this will be dependent on the type of repository '
                           'or hosting service being used, and those should '
                           'not be modified. Custom fields can be set by the '
                           'API or extensions.',
            'added_in': '3.0.18',
        },
        'name': {
            'type': StringFieldType,
            'description': 'The name of the repository.',
        },
        'path': {
            'type': StringFieldType,
            'description': 'The main path to the repository, which is used '
                           'for communicating with the repository and '
                           'accessing files.',
        },
        'mirror_path': {
            'type': StringFieldType,
            'description': 'An alternate path to the repository, for '
                           'lookup purposes.',
            'added_in': '1.7.19',
        },
        'visible': {
            'type': BooleanFieldType,
            'description': 'Whether or not this repository is visible (admin '
                           'only).',
            'added_in': '2.0',
        },
        'tool': {
            'type': StringFieldType,
            'description': 'The name of the internal repository '
                           'communication class used to talk to the '
                           'repository. This is generally the type of the '
                           'repository.',
        },
        'bug_tracker': {
            'type': StringFieldType,
            'description': 'The URL to a bug in the bug tracker for '
                           'this repository, with ``%s`` in place of the '
                           'bug ID.',
            'added_in': '2.5',
        }
    }
    uri_object_key = 'repository_id'
    item_child_resources = [
        resources.diff_file_attachment,
        resources.repository_branches,
        resources.repository_commits,
        resources.repository_info,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    @webapi_check_login_required
    def get_queryset(self, request, is_list=False, local_site_name=None,
                     show_invisible=False, *args, **kwargs):
        """Returns a queryset for Repository models."""
        local_site = self._get_local_site(local_site_name)

        if is_list:
            queryset = self.model.objects.accessible(
                request.user,
                visible_only=not show_invisible,
                local_site=local_site)

            q = Q()

            if 'q' in request.GET:
                q = q & Q(name__istartswith=request.GET.get('q'))

            if 'name' in request.GET:
                q = q & Q(name__in=request.GET.get('name').split(','))

            if 'path' in request.GET:
                paths = request.GET['path'].split(',')
                q = q & (Q(path__in=paths) | Q(mirror_path__in=paths))

            if 'name-or-path' in request.GET:
                name_or_paths = request.GET['name-or-path'].split(',')
                q = q & (Q(name__in=name_or_paths) |
                         Q(path__in=name_or_paths) |
                         Q(mirror_path__in=name_or_paths))

            if 'tool' in request.GET:
                q = q & Q(tool__name__in=request.GET['tool'].split(','))

            if 'hosting-service' in request.GET:
                q = q & Q(hosting_account__service_name__in=
                          request.GET['hosting-service'].split(','))

            if 'username' in request.GET:
                usernames = request.GET['username'].split(',')

                q = q & (Q(username__in=usernames) |
                         Q(hosting_account__username__in=usernames))

            return queryset.filter(q).distinct()
        else:
            return self.model.objects.filter(local_site=local_site)

    def parse_tool_field(self, value, **kwargs):
        """Parse the tool field in a request.

        Args:
            value (unicode):
                The name of the tool, as provided in the request.

            **kwargs (dict):
                Additional keyword arguments passed to the method.

        Returns:
            unicode:
            The resulting SCMTool ID to use for the form.

        Raises:
            django.core.exceptions.ValidationError:
                The tool could not be found.
        """
        try:
            return Tool.objects.filter(name=value)[0].scmtool_id
        except IndexError:
            raise ValidationError('This is not a valid SCMTool')

    def serialize_tool_field(self, obj, **kwargs):
        return obj.tool.name

    def has_access_permissions(self, request, repository, *args, **kwargs):
        return repository.is_accessible_by(request.user)

    def has_modify_permissions(self, request, repository, *args, **kwargs):
        return repository.is_mutable_by(request.user)

    def has_delete_permissions(self, request, repository, *args, **kwargs):
        return repository.is_mutable_by(request.user)

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional=dict({
            'name': {
                'type': StringFieldType,
                'description': 'Filter repositories by one or more '
                               'comma-separated names.',
                'added_in': '1.7.21',
            },
            'path': {
                'type': StringFieldType,
                'description': 'Filter repositories by one or more '
                               'comma-separated paths or mirror paths.',
                'added_in': '1.7.21',
            },
            'name-or-path': {
                'type': StringFieldType,
                'description': 'Filter repositories by one or more '
                               'comma-separated names, paths, or '
                               'mirror paths.',
                'added_in': '1.7.21',
            },
            'tool': {
                'type': StringFieldType,
                'description': 'Filter repositories by one or more '
                               'comma-separated tool names.',
                'added_in': '1.7.21',
            },
            'hosting-service': {
                'type': StringFieldType,
                'description': 'Filter repositories by one or more '
                               'comma-separated hosting service IDs.',
                'added_in': '1.7.21',
            },
            'username': {
                'type': StringFieldType,
                'description': 'Filter repositories by one or more '
                               'comma-separated usernames.',
                'added_in': '1.7.21',
            },
            'show-invisible': {
                'type': BooleanFieldType,
                'description': 'Whether to list only visible repositories or '
                               'all repositories.',
                'added_in': '2.0',
            },
            'q': {
                'type': StringFieldType,
                'description': 'Filter repositories by those that have a '
                               'name starting with the search term.',
                'added_in': '4.0',
            },
        }, **WebAPIResource.get_list.optional_fields),
        required=WebAPIResource.get_list.required_fields,
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Retrieves the list of repositories on the server.

        This will only list visible repositories. Any repository that the
        administrator has hidden will be excluded from the list.
        """
        show_invisible = request.GET.get('show-invisible', False)
        return super(RepositoryResource, self).get_list(
            request, show_invisible=show_invisible, *args, **kwargs)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information on a particular repository.

        This will only return basic information on the repository.
        Authentication information, hosting details, and repository-specific
        information are not provided.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(BAD_HOST_KEY, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED, REPO_AUTHENTICATION_ERROR,
                            REPO_INFO_ERROR, REPOSITORY_ALREADY_EXISTS,
                            SERVER_CONFIG_ERROR, UNVERIFIED_HOST_CERT,
                            UNVERIFIED_HOST_KEY)
    @webapi_request_fields(
        required={
            'name': {
                'type': StringFieldType,
                'description': 'The human-readable name of the repository.',
                'added_in': '1.6',
            },
            'tool': {
                'type': StringFieldType,
                'description': 'The name of the SCMTool to use. Valid '
                               'names can be found in the Administration UI.',
                'added_in': '1.6',
            },
        },
        optional={
            'bug_tracker': {
                'type': StringFieldType,
                'description': 'The URL to a bug in the bug tracker for '
                               'this repository, with ``%s`` in place of the '
                               'bug ID.',
                'added_in': '1.6',
            },
            'bug_tracker_hosting_url': {
                'type': StringFieldType,
                'description': (
                    'The URL to the base of your bug tracker hosting service, '
                    'for services that support this option and when using '
                    '``bug_tracker_type``.'
                ),
                'added_in': '3.0.19',
            },
            'bug_tracker_plan': {
                'type': StringFieldType,
                'description': (
                    'The bug tracker service plan, if specifying '
                    '``bug_tracker_type``. The value is specific to the '
                    'type of bug tracker hosting service.'
                ),
                'added_in': '3.0.19',
            },
            'bug_tracker_type': {
                'type': StringFieldType,
                'description': (
                    'The type of hosting service backing the bug tracker to '
                    'use for this repository, if not specifying '
                    '``bug_tracker``. This may require '
                    '``bug_tracker_hosting_account_username`` and some '
                    'service-specific fields (``bug_tracker_hosting_url``, '
                    '``bug_tracker_plan``, and fields containing the '
                    'service ID).'
                ),
                'added_in': '3.0.19',
            },
            'bug_tracker_use_hosting': {
                'type': BooleanFieldType,
                'description': (
                    "Whether to use the hosting service's own "
                    "bug tracker support for this repository. "
                    "This is dependent on the bug tracker, and "
                    "required ``hosting_type``."
                ),
                'added_in': '3.0.19',
            },
            'encoding': {
                'type': StringFieldType,
                'description': 'The encoding used for files in the '
                               'repository. This is an advanced setting '
                               'and should only be used if you absolutely '
                               'need it.',
                'added_in': '1.6',
            },
            'hosting_account_username': {
                'type': StringFieldType,
                'description': (
                    'The pre-configured username for a hosting service '
                    'account used to connect to this repository. This is '
                    'only used if ``hosting_type`` is set.'
                ),
                'added_in': '3.0.19',
            },
            'hosting_type': {
                'type': StringFieldType,
                'description': (
                    'The type of hosting service backing this repository, if '
                    'not configuring a plain repository. This will require '
                    '``hosting_account_username`` and some service-specific '
                    'fields (``hosting_url``, ``repository_plan``, and '
                    'fields prefixed with the hosting type ID).'
                ),
                'added_in': '3.0.19',
            },
            'hosting_url': {
                'type': StringFieldType,
                'description': (
                    'The URL to the base of your repository hosting service, '
                    'for services that support this option and when using '
                    '``hosting_type``.'
                ),
                'added_in': '3.0.19',
            },
            'mirror_path': {
                'type': StringFieldType,
                'description': 'An alternate path to the repository.',
                'added_in': '1.6',
            },
            'password': {
                'type': StringFieldType,
                'description': 'The password used to access the repository.',
                'added_in': '1.6',
            },
            'path': {
                'type': StringFieldType,
                'description': 'The path to the repository.',
                'added_in': '1.6',
            },
            'public': {
                'type': BooleanFieldType,
                'description': 'Whether or not review requests on the '
                               'repository will be publicly accessible '
                               'by users on the site. The default is true.',
                'added_in': '1.6',
            },
            'raw_file_url': {
                'type': StringFieldType,
                'description': "A URL mask used to check out a particular "
                               "file using HTTP. This is needed for "
                               "repository types that can't access files "
                               "natively. Use ``<revision>`` and "
                               "``<filename>`` in the URL in place of the "
                               "revision and filename parts of the path.",
                'added_in': '1.6',
            },
            'repository_plan': {
                'type': StringFieldType,
                'description': (
                    'The hosting service repository plan, if specifying '
                    '``hosting_type``. The value is specific to the type of '
                    'hosting service.'
                ),
                'added_in': '3.0.19',
            },
            'trust_host': {
                'type': BooleanFieldType,
                'description': 'Whether or not any unknown host key or '
                               'certificate should be accepted. The default '
                               'is false, in which case this will error out '
                               'if encountering an unknown host key or '
                               'certificate.',
                'added_in': '1.6',
            },
            'username': {
                'type': StringFieldType,
                'description': 'The username used to access the repository.',
                'added_in': '1.6',
            },
            'visible': {
                'type': BooleanFieldType,
                'description': 'Whether the repository is visible.',
                'added_in': '2.0',
            },
        },
        allow_unknown=True
    )
    def create(self, request, local_site, parsed_request_fields, *args,
               **kwargs):
        """Creates a repository.

        This will create a new repository that can immediately be used for
        review requests.

        The ``tool`` is a registered SCMTool name. This must be known
        beforehand, and can be looked up in the Review Board administration UI.

        Before saving the new repository, the repository will be checked for
        access. On success, the repository will be created and this will
        return :http:`201`.

        In the event of an access problem (authentication problems,
        bad/unknown SSH key, or unknown certificate), an error will be
        returned and the repository information won't be updated. Pass
        ``trust_host=1`` to approve bad/unknown SSH keys or certificates.
        """
        if not Repository.objects.can_create(request.user, local_site):
            return self.get_no_access_error(request)

        return self._create_or_update(form_data=parsed_request_fields,
                                      request=request,
                                      local_site=local_site,
                                      **kwargs)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            INVALID_FORM_DATA, SERVER_CONFIG_ERROR,
                            BAD_HOST_KEY, UNVERIFIED_HOST_KEY,
                            UNVERIFIED_HOST_CERT, REPO_AUTHENTICATION_ERROR,
                            REPO_INFO_ERROR)
    @webapi_request_fields(
        optional={
            'archive_name': {
                'type': BooleanFieldType,
                'description': "Whether or not the (non-user-visible) name of "
                               "the repository should be changed so that it "
                               "(probably) won't conflict with any future "
                               "repository names. Starting in 3.0.12, "
                               "performing a DELETE will archive the "
                               "repository, and is the preferred method.",
                'added_in': '1.6.2',
                'deprecated_in': '3.0.12',
            },
            'bug_tracker': {
                'type': StringFieldType,
                'description': 'The URL to a bug in the bug tracker for '
                               'this repository, with ``%s`` in place of the '
                               'bug ID.',
                'added_in': '1.6',
            },
            'bug_tracker_hosting_url': {
                'type': StringFieldType,
                'description': (
                    'The URL to the base of your bug tracker hosting service, '
                    'for services that support this option and when using '
                    '``bug_tracker_type``.'
                ),
                'added_in': '3.0.19',
            },
            'bug_tracker_plan': {
                'type': StringFieldType,
                'description': (
                    'The bug tracker service plan, if specifying '
                    '``bug_tracker_type``. The value is specific to the '
                    'type of bug tracker hosting service.'
                ),
                'added_in': '3.0.19',
            },
            'bug_tracker_type': {
                'type': StringFieldType,
                'description': (
                    'The type of hosting service backing the bug tracker to '
                    'use for this repository, if not specifying '
                    '``bug_tracker``. This may require '
                    '``bug_tracker_hosting_account_username`` and some '
                    'service-specific fields (``bug_tracker_hosting_url``, '
                    '``bug_tracker_plan``, and fields containing the '
                    'service ID).'
                ),
                'added_in': '3.0.19',
            },
            'bug_tracker_use_hosting': {
                'type': BooleanFieldType,
                'description': (
                    "Whether to use the hosting service's own "
                    "bug tracker support for this repository. "
                    "This is dependent on the bug tracker, and "
                    "required ``hosting_type``."
                ),
                'added_in': '3.0.19',
            },
            'encoding': {
                'type': StringFieldType,
                'description': 'The encoding used for files in the '
                               'repository. This is an advanced setting '
                               'and should only be used if you absolutely '
                               'need it.',
                'added_in': '1.6',
            },
            'hosting_account_username': {
                'type': StringFieldType,
                'description': (
                    'The pre-configured username for a hosting service '
                    'account used to connect to this repository. This is '
                    'only used if ``hosting_type`` is set.'
                ),
                'added_in': '3.0.19',
            },
            'hosting_type': {
                'type': StringFieldType,
                'description': (
                    'The type of hosting service backing this repository, if '
                    'not configuring a plain repository. This will require '
                    '``hosting_account_username`` and some service-specific '
                    'fields (``hosting_url``, ``repository_plan``, and '
                    'fields prefixed with the hosting type ID).'
                ),
                'added_in': '3.0.19',
            },
            'hosting_url': {
                'type': StringFieldType,
                'description': (
                    'The URL to the base of your repository hosting service, '
                    'for services that support this option and when using '
                    '``hosting_type``.'
                ),
                'added_in': '3.0.19',
            },
            'mirror_path': {
                'type': StringFieldType,
                'description': 'An alternate path to the repository.',
                'added_in': '1.6',
            },
            'name': {
                'type': StringFieldType,
                'description': 'The human-readable name of the repository.',
                'added_in': '1.6',
            },
            'password': {
                'type': StringFieldType,
                'description': 'The password used to access the repository.',
                'added_in': '1.6',
            },
            'path': {
                'type': StringFieldType,
                'description': 'The path to the repository.',
                'added_in': '1.6',
            },
            'public': {
                'type': BooleanFieldType,
                'description': 'Whether or not review requests on the '
                               'repository will be publicly accessible '
                               'by users on the site. The default is true.',
                'added_in': '1.6',
            },
            'raw_file_url': {
                'type': StringFieldType,
                'description': "A URL mask used to check out a particular "
                               "file using HTTP. This is needed for "
                               "repository types that can't access files "
                               "natively. Use ``<revision>`` and "
                               "``<filename>`` in the URL in place of the "
                               "revision and filename parts of the path.",
                'added_in': '1.6',
            },
            'repository_plan': {
                'type': StringFieldType,
                'description': (
                    'The hosting service repository plan, if specifying '
                    '``hosting_type``. The value is specific to the type of '
                    'hosting service.'
                ),
                'added_in': '3.0.19',
            },
            'trust_host': {
                'type': BooleanFieldType,
                'description': 'Whether or not any unknown host key or '
                               'certificate should be accepted. The default '
                               'is false, in which case this will error out '
                               'if encountering an unknown host key or '
                               'certificate.',
                'added_in': '1.6',
            },
            'username': {
                'type': StringFieldType,
                'description': 'The username used to access the repository.',
                'added_in': '1.6',
            },
            'visible': {
                'type': BooleanFieldType,
                'description': 'Whether the repository is visible.',
                'added_in': '2.0',
            },
        },
        allow_unknown=True
    )
    def update(self, request, local_site, parsed_request_fields,
               archive_name=None, *args, **kwargs):
        """Updates a repository.

        This will update the information on a repository. If the path,
        username, or password has changed, Review Board will try again to
        verify access to the repository.

        In the event of an access problem (authentication problems,
        bad/unknown SSH key, or unknown certificate), an error will be
        returned and the repository information won't be updated. Pass
        ``trust_host=1`` to approve bad/unknown SSH keys or certificates.
        """
        try:
            repository = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, repository):
            return self.get_no_access_error(request)

        form_data = parsed_request_fields.copy()
        form_data['tool'] = repository.tool.name

        return self._create_or_update(repository=repository,
                                      form_data=form_data,
                                      request=request,
                                      local_site=local_site,
                                      archive=archive_name,
                                      **kwargs)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Deletes a repository.

        Repositories associated with review requests won't be fully deleted
        from the database. Instead, they'll be archived, removing them from
        any lists of repositories but freeing up their name for use in a
        future repository.

        .. versionchanged::
            3.0.12
            Previous releases simply marked a repository as invisible when
            deleting. Starting in 3.0.12, the repository is archived instead.
        """
        try:
            repository = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, repository):
            return self.get_no_access_error(request)

        if repository.review_requests.exists():
            # We don't actually delete the repository. We instead archive it.
            # Otherwise, all the review requests are lost. By archiving it,
            # it'll be removed from the UI and from the list in the API.
            repository.archive()
        else:
            repository.delete()

        return 204, {}

    def _create_or_update(self, form_data, request, local_site,
                          repository=None, archive=False, **kwargs):
        """Create or update a repository.

        Args:
            form_data (dict):
                The repository data to pass to the form.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site being operated on.

            repository (reviewboard.scmtools.models.Repository):
                An existing repository instance to update, if responding to
                a HTTP PUT request.

            archive (bool, optional):
                Whether to archive the repository after updating it.

            **kwargs (dict):
                Keyword arguments representing additional fields handled by
                the API resource.

        Returns:
            tuple or django.http.HttpResponse:
            The response to send back to the client.
        """
        # Try to determine what we need to set bug_tracker_type to, based on
        # the input and any current settings. We need to do this for two
        # reasons:
        #
        # 1) If the user provides just a `bug_tracker` value, we want to make
        #    sure that the type is set correctly, without the user having to
        #    set it (partially for backwards-compatibility, partially because
        #    it's expected behavior).
        #
        # 2) UpdateFormMixin is going to set a default for `bug_tracker_type`
        #    based on the form field's default value, since it won't find it
        #    on the model.
        if (not form_data.get('bug_tracker_type') and
            (form_data.get('bug_tracker') or
             (repository is not None and
              repository.bug_tracker and
              not repository.extra_data.get('bug_tracker_use_hosting') and
              not repository.extra_data.get('bug_tracker_type')))):
            form_data['bug_tracker_type'] = \
                RepositoryForm.CUSTOM_BUG_TRACKER_ID

        hosting_type = form_data.get('hosting_type')
        hosting_account_id = None

        if hosting_type and hosting_type != 'custom':
            hosting_account_username = \
                form_data.pop('hosting_account_username', None)

            try:
                hosting_account = HostingServiceAccount.objects.get(
                    username=hosting_account_username,
                    hosting_url=form_data.get('hosting_url'),
                    service_name=hosting_type,
                    local_site=local_site)
            except HostingServiceAccount.DoesNotExist:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'hosting_account_username': [
                            'An existing hosting service account with the '
                            'username "%s" could not be found for the hosting '
                            'service "%s".'
                            % (hosting_account_username, hosting_type),
                        ],
                    },
                }

            hosting_account_id = hosting_account.pk

        # Set additional details for the repository form. We want to force
        # some state to be set or unset, and add in any extra form-specific
        # fields.
        form_data.update(kwargs['extra_fields'])
        form_data['hosting_account'] = hosting_account_id

        try:
            return self.handle_form_request(
                data=form_data,
                request=request,
                instance=repository,
                form_kwargs={
                    'limit_to_local_site': local_site,
                    'request': request,
                },
                save_kwargs={
                    'commit': False,
                },
                archive=archive,
                **kwargs)
        except ImportExtraDataError as e:
            return e.error_payload

    def save_form(self, form, archive=None, extra_fields=None, **kwargs):
        """Save the form.

        This will save the repository instance and then optionally archive
        the repository.

        Args:
            form (reviewboard.scmtools.forms.RepositoryForm):
                The form to save.

            archive (bool, optional):
                Whether to archive the repository.

            extra_fields (dict, optional):
                Extra fields from the request not otherwise handled by the
                API resource. Any ``extra_data`` modifications from this will
                be applied to the repository.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent method.

        Returns:
            reviewboard.scmtools.models.Repository:
            The saved repository.
        """
        repository = super(RepositoryResource, self).save_form(form=form,
                                                               **kwargs)

        # Any errors from this will be caught in _create_or_update.
        if extra_fields:
            self.import_extra_data(repository, repository.extra_data,
                                   extra_fields)

        repository.save()
        form.save_m2m()

        if archive:
            repository.archive()

        return repository

    def build_form_error_response(self, form=None, **kwargs):
        """Build an error response based on the form.

        Args:
            form (reviewboard.scmtools.forms.RepositoryForm, optional):
                The repository form.

            **kwargs (dict):
                Keyword arguments passed to this method.

        Returns:
            tuple or django.http.HttpResponse:
            The error response.
        """
        if form is not None:
            if form.get_repository_already_exists():
                return REPOSITORY_ALREADY_EXISTS
            elif form.form_validation_error is not None:
                code = getattr(form.form_validation_error, 'code', None)
                params = getattr(form.form_validation_error, 'params') or {}
                e = params.get('exception')

                if code == 'repository_not_found':
                    return MISSING_REPOSITORY
                elif code == 'repo_auth_failed':
                    return REPO_AUTHENTICATION_ERROR, {
                        'reason': six.text_type(e),
                    }
                elif code == 'cert_unverified':
                    cert = e.certificate

                    return UNVERIFIED_HOST_CERT, {
                        'certificate': {
                            'failures': cert.failures,
                            'fingerprint': cert.fingerprint,
                            'hostname': cert.hostname,
                            'issuer': cert.issuer,
                            'valid': {
                                'from': cert.valid_from,
                                'until': cert.valid_until,
                            },
                        },
                    }
                elif code == 'host_key_invalid':
                    return BAD_HOST_KEY, {
                        'hostname': e.hostname,
                        'expected_key': e.raw_expected_key.get_base64(),
                        'key': e.raw_key.get_base64(),
                    }
                elif code == 'host_key_unverified':
                    return UNVERIFIED_HOST_KEY, {
                        'hostname': e.hostname,
                        'key': e.raw_key.get_base64(),
                    }
                elif code in ('accept_cert_failed',
                              'add_host_key_failed',
                              'replace_host_key_failed'):
                    return SERVER_CONFIG_ERROR, {
                        'reason': six.text_type(e),
                    }
                elif code == 'missing_ssh_key':
                    return MISSING_USER_KEY
                elif code in ('unexpected_scm_failure',
                              'unexpected_ssh_failure',
                              'unexpected_failure'):
                    return REPO_INFO_ERROR, {
                        'error': six.text_type(e),
                    }

        return super(RepositoryResource, self).build_form_error_response(
            form=form,
            **kwargs)


repository_resource = RepositoryResource()
