from __future__ import unicode_literals

import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.scmtools.errors import (AuthenticationError,
                                         SCMError,
                                         RepositoryNotFoundError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import (SSHError,
                                    BadHostKeyError,
                                    UnknownHostKeyError)
from reviewboard.webapi.base import WebAPIResource
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
from reviewboard.webapi.resources import resources


class RepositoryResource(WebAPIResource):
    """Provides information on a registered repository.

    Review Board has a list of known repositories, which can be modified
    through the site's administration interface. These repositories contain
    the information needed for Review Board to access the files referenced
    in diffs.
    """
    model = Repository
    name_plural = 'repositories'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the repository.',
        },
        'name': {
            'type': six.text_type,
            'description': 'The name of the repository.',
        },
        'path': {
            'type': six.text_type,
            'description': 'The main path to the repository, which is used '
                           'for communicating with the repository and '
                           'accessing files.',
        },
        'mirror_path': {
            'type': six.text_type,
            'description': 'An alternate path to the repository, for '
                           'lookup purposes.',
        },
        'visible': {
            'type': bool,
            'description': 'Whether or not this repository is visible (admin '
                           'only).',
        },
        'tool': {
            'type': six.text_type,
            'description': 'The name of the internal repository '
                           'communication class used to talk to the '
                           'repository. This is generally the type of the '
                           'repository.'
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
                'type': str,
                'description': 'Filter repositories by one or more '
                               'comma-separated names.',
            },
            'path': {
                'type': str,
                'description': 'Filter repositories by one or more '
                               'comma-separated paths or mirror paths.',
            },
            'name-or-path': {
                'type': str,
                'description': 'Filter repositories by one or more '
                               'comma-separated names, paths, or '
                               'mirror paths.',
            },
            'tool': {
                'type': str,
                'description': 'Filter repositories by one or more '
                               'comma-separated tool names.',
            },
            'hosting-service': {
                'type': str,
                'description': 'Filter repositories by one or more '
                               'comma-separated hosting service IDs.',
            },
            'username': {
                'type': str,
                'description': 'Filter repositories by one or more '
                               'comma-separated usernames.',
            },
            'show-invisible': {
                'type': bool,
                'description': 'Whether to list only visible repositories or '
                               'all repositories.',
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
                'type': six.text_type,
                'description': 'The human-readable name of the repository.',
            },
            'path': {
                'type': six.text_type,
                'description': 'The path to the repository.',
            },
            'tool': {
                'type': six.text_type,
                'description': 'The ID of the SCMTool to use.',
            },
        },
        optional={
            'bug_tracker': {
                'type': six.text_type,
                'description': 'The URL to a bug in the bug tracker for '
                               'this repository, with ``%s`` in place of the '
                               'bug ID.',
            },
            'encoding': {
                'type': six.text_type,
                'description': 'The encoding used for files in the '
                               'repository. This is an advanced setting '
                               'and should only be used if you absolutely '
                               'need it.',
            },
            'mirror_path': {
                'type': six.text_type,
                'description': 'An alternate path to the repository.',
            },
            'password': {
                'type': six.text_type,
                'description': 'The password used to access the repository.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not review requests on the '
                               'repository will be publicly accessible '
                               'by users on the site. The default is true.',
            },
            'raw_file_url': {
                'type': six.text_type,
                'description': "A URL mask used to check out a particular "
                               "file using HTTP. This is needed for "
                               "repository types that can't access files "
                               "natively. Use ``<revision>`` and "
                               "``<filename>`` in the URL in place of the "
                               "revision and filename parts of the path.",
            },
            'trust_host': {
                'type': bool,
                'description': 'Whether or not any unknown host key or '
                               'certificate should be accepted. The default '
                               'is false, in which case this will error out '
                               'if encountering an unknown host key or '
                               'certificate.',
            },
            'username': {
                'type': six.text_type,
                'description': 'The username used to access the repository.',
            },
            'visible': {
                'type': bool,
                'description': 'Whether the repository is visible.',
            },
        },
    )
    def create(self, request, name, path, tool, trust_host=False,
               bug_tracker=None, encoding=None, mirror_path=None,
               password=None, public=None, raw_file_url=None, username=None,
               visible=True, local_site_name=None, *args, **kwargs):
        """Creates a repository.

        This will create a new repository that can immediately be used for
        review requests.

        The ``tool`` is a registered SCMTool ID. This must be known beforehand,
        and can be looked up in the Review Board administration UI.

        Before saving the new repository, the repository will be checked for
        access. On success, the repository will be created and this will
        return :http:`201`.

        In the event of an access problem (authentication problems,
        bad/unknown SSH key, or unknown certificate), an error will be
        returned and the repository information won't be updated. Pass
        ``trust_host=1`` to approve bad/unknown SSH keys or certificates.
        """
        local_site = self._get_local_site(local_site_name)

        if not Repository.objects.can_create(request.user, local_site):
            return self._no_access_error(request.user)

        try:
            scmtool = Tool.objects.get(name=tool)
        except Tool.DoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'tool': ['This is not a valid SCMTool'],
                }
            }

        cert = {}
        error_result = self._check_repository(scmtool.get_scmtool_class(),
                                              path, username, password,
                                              local_site, trust_host, cert,
                                              request)

        if error_result is not None:
            return error_result

        if public is None:
            public = True

        repository = Repository(
            name=name,
            path=path,
            mirror_path=mirror_path or '',
            raw_file_url=raw_file_url or '',
            username=username or '',
            password=password or '',
            tool=scmtool,
            bug_tracker=bug_tracker or '',
            encoding=encoding or '',
            public=public,
            visible=visible,
            local_site=local_site)

        if cert:
            repository.extra_data['cert'] = cert

        try:
            repository.full_clean()
        except ValidationError as e:
            if hasattr(e, 'params') and 'field' in e.params:
                return INVALID_FORM_DATA, {
                    'fields': {
                        e.params['field']: e.message,
                    },
                }
            else:
                return REPOSITORY_ALREADY_EXISTS

        repository.save()

        return 201, {
            self.item_result_key: repository,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            INVALID_FORM_DATA, SERVER_CONFIG_ERROR,
                            BAD_HOST_KEY, UNVERIFIED_HOST_KEY,
                            UNVERIFIED_HOST_CERT, REPO_AUTHENTICATION_ERROR,
                            REPO_INFO_ERROR)
    @webapi_request_fields(
        optional={
            'bug_tracker': {
                'type': six.text_type,
                'description': 'The URL to a bug in the bug tracker for '
                               'this repository, with ``%s`` in place of the '
                               'bug ID.',
            },
            'encoding': {
                'type': six.text_type,
                'description': 'The encoding used for files in the '
                               'repository. This is an advanced setting '
                               'and should only be used if you absolutely '
                               'need it.',
            },
            'mirror_path': {
                'type': six.text_type,
                'description': 'An alternate path to the repository.',
            },
            'name': {
                'type': six.text_type,
                'description': 'The human-readable name of the repository.',
            },
            'password': {
                'type': six.text_type,
                'description': 'The password used to access the repository.',
            },
            'path': {
                'type': six.text_type,
                'description': 'The path to the repository.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not review requests on the '
                               'repository will be publicly accessible '
                               'by users on the site. The default is true.',
            },
            'raw_file_url': {
                'type': six.text_type,
                'description': "A URL mask used to check out a particular "
                               "file using HTTP. This is needed for "
                               "repository types that can't access files "
                               "natively. Use ``<revision>`` and "
                               "``<filename>`` in the URL in place of the "
                               "revision and filename parts of the path.",
            },
            'trust_host': {
                'type': bool,
                'description': 'Whether or not any unknown host key or '
                               'certificate should be accepted. The default '
                               'is false, in which case this will error out '
                               'if encountering an unknown host key or '
                               'certificate.',
            },
            'username': {
                'type': six.text_type,
                'description': 'The username used to access the repository.',
            },
            'archive_name': {
                'type': bool,
                'description': "Whether or not the (non-user-visible) name of "
                               "the repository should be changed so that it "
                               "(probably) won't conflict with any future "
                               "repository names.",
            },
            'visible': {
                'type': bool,
                'description': 'Whether the repository is visible.',
            },
        },
    )
    def update(self, request, trust_host=False, *args, **kwargs):
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
            return self._no_access_error(request.user)

        for field in ('bug_tracker', 'encoding', 'mirror_path', 'name',
                      'password', 'path', 'public', 'raw_file_url',
                      'username', 'visible'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(repository, field, value)

        # Only check the repository if the access information has changed.
        if 'path' in kwargs or 'username' in kwargs or 'password' in kwargs:
            cert = {}

            error_result = self._check_repository(
                repository.tool.get_scmtool_class(),
                repository.path,
                repository.username,
                repository.password,
                repository.local_site,
                trust_host,
                cert,
                request)

            if error_result is not None:
                return error_result

            if cert:
                repository.extra_data['cert'] = cert

        # If the API call is requesting that we archive the name, we'll give it
        # a name which won't overlap with future user-named repositories. This
        # should usually be used just before issuing a DELETE call, which will
        # set the visibility flag to False
        if kwargs.get('archive_name', False):
            repository.archive(save=False)

        try:
            repository.full_clean()
        except ValidationError as e:
            return INVALID_FORM_DATA, {
                'fields': {
                    e.params['field']: e.message,
                },
            }

        repository.save()

        return 200, {
            self.item_result_key: repository,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Deletes a repository.

        The repository will not actually be deleted from the database, as
        that would also trigger a deletion of all review requests. Instead,
        it makes a repository as no longer being visible, which will hide it
        in the UIs and in the API.
        """
        try:
            repository = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, repository):
            return self._no_access_error(request.user)

        if not repository.review_requests.exists():
            repository.delete()
        else:
            # We don't actually delete the repository. We instead just hide it.
            # Otherwise, all the review requests are lost. By marking it as not
            # visible, it'll be removed from the UI and from the list in the
            # API.
            repository.visible = False
            repository.save()

        return 204, {}

    def _check_repository(self, scmtool_class, path, username, password,
                          local_site, trust_host, ret_cert, request):
        if local_site:
            local_site_name = local_site.name
        else:
            local_site_name = None

        while 1:
            # Keep doing this until we have an error we don't want
            # to ignore, or it's successful.
            try:
                scmtool_class.check_repository(path, username, password,
                                               local_site_name)
                return None
            except RepositoryNotFoundError:
                return MISSING_REPOSITORY
            except BadHostKeyError as e:
                if trust_host:
                    try:
                        client = SSHClient(namespace=local_site_name)
                        client.replace_host_key(e.hostname,
                                                e.raw_expected_key,
                                                e.raw_key)
                    except IOError as e:
                        return SERVER_CONFIG_ERROR, {
                            'reason': six.text_type(e),
                        }
                else:
                    return BAD_HOST_KEY, {
                        'hostname': e.hostname,
                        'expected_key': e.raw_expected_key.get_base64(),
                        'key': e.raw_key.get_base64(),
                    }
            except UnknownHostKeyError as e:
                if trust_host:
                    try:
                        client = SSHClient(namespace=local_site_name)
                        client.add_host_key(e.hostname, e.raw_key)
                    except IOError as e:
                        return SERVER_CONFIG_ERROR, {
                            'reason': six.text_type(e),
                        }
                else:
                    return UNVERIFIED_HOST_KEY, {
                        'hostname': e.hostname,
                        'key': e.raw_key.get_base64(),
                    }
            except UnverifiedCertificateError as e:
                if trust_host:
                    try:
                        cert = scmtool_class.accept_certificate(
                            path, local_site_name)

                        if cert:
                            ret_cert.update(cert)
                    except IOError as e:
                        return SERVER_CONFIG_ERROR, {
                            'reason': six.text_type(e),
                        }
                else:
                    return UNVERIFIED_HOST_CERT, {
                        'certificate': {
                            'failures': e.certificate.failures,
                            'fingerprint': e.certificate.fingerprint,
                            'hostname': e.certificate.hostname,
                            'issuer': e.certificate.issuer,
                            'valid': {
                                'from': e.certificate.valid_from,
                                'until': e.certificate.valid_until,
                            },
                        },
                    }
            except AuthenticationError as e:
                if 'publickey' in e.allowed_types and e.user_key is None:
                    return MISSING_USER_KEY
                else:
                    return REPO_AUTHENTICATION_ERROR, {
                        'reason': six.text_type(e),
                    }
            except SSHError as e:
                logging.error('Got unexpected SSHError when checking '
                              'repository: %s'
                              % e, exc_info=1, request=request)
                return REPO_INFO_ERROR, {
                    'error': six.text_type(e),
                }
            except SCMError as e:
                logging.error('Got unexpected SCMError when checking '
                              'repository: %s'
                              % e, exc_info=1, request=request)
                return REPO_INFO_ERROR, {
                    'error': six.text_type(e),
                }
            except Exception as e:
                logging.error('Unknown error in checking repository %s: %s',
                              path, e, exc_info=1, request=request)

                # We should give something better, but I don't have anything.
                # This will at least give a HTTP 500.
                raise


repository_resource = RepositoryResource()
