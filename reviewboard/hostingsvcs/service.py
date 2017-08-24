"""The base hosting service class and associated definitions."""

from __future__ import unicode_literals

import base64
import json
import logging
import mimetools

from django.conf.urls import include, patterns, url
from django.dispatch import receiver
from django.utils import six
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.six.moves.urllib.request import (Request as BaseURLRequest,
                                                   HTTPBasicAuthHandler,
                                                   urlopen)
from django.utils.translation import ugettext_lazy as _
from pkg_resources import iter_entry_points

import reviewboard.hostingsvcs.urls as hostingsvcs_urls
from reviewboard.signals import initializing


class URLRequest(BaseURLRequest):
    """A request that can use any HTTP method.

    By default, the :py:class:`urllib2.Request` class only supports HTTP GET
    and HTTP POST methods. This subclass allows for any HTTP method to be
    specified for the request.
    """

    def __init__(self, url, body='', headers=None, method='GET'):
        """Initialize the URLRequest.

        Args:
            url (unicode):
                The URL to make the request against.

            body (unicode or bytes):
                The content of the request.

            headers (dict, optional):
                Additional headers to attach to the request.

            method (unicode, optional):
                The request method. If not provided, it defaults to a ``GET``
                request.
        """
        # Request is an old-style class and therefore we cannot use super().
        BaseURLRequest.__init__(self, url, body, headers or {})
        self.method = method

    def get_method(self):
        """Return the HTTP method of the request.

        Returns:
            unicode:
            The HTTP method of the request.
        """
        return self.method

    def add_basic_auth(self, username, password):
        """Add HTTP Basic Authentication headers to the request.

        Args:
            username (unicode or bytes):
                The username.

            password (unicode or bytes):
                The password.
        """
        if isinstance(username, six.text_type):
            username = username.encode('utf-8')

        if isinstance(password, six.text_type):
            password = password.encode('utf-8')

        auth = b'%s:%s' % (username, password)
        self.add_header(HTTPBasicAuthHandler.auth_header,
                        b'Basic %s' % base64.b64encode(auth))


class HostingServiceClient(object):
    """Client for communicating with a hosting service's API.

    This implementation includes abstractions for performing HTTP operations,
    and wrappers for those to interpret responses as JSON data.

    HostingService subclasses can also include an override of this class to add
    additional checking (such as GitHub's checking of rate limit headers), or
    add higher-level API functionality.
    """

    def __init__(self, hosting_service):
        """Initialize the client.

        This method is a no-op. Subclasses requiring access to the hosting
        service or account should override this method.

        Args:
            hosting_service (HostingService):
                The hosting service that is using this client.
        """
        pass

    #
    # HTTP utility methods
    #

    def http_delete(self, url, headers=None, *args, **kwargs):
        """Perform an HTTP DELETE on the given URL.

        Args:
            url (unicode):
                The URL to perform the request on.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            tuple:
            A tuple of:

            * The response body (:py:class:`bytes`).
            * The response headers (:py:class:`dict`).

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self.http_request(url, headers=headers, method='DELETE',
                                 **kwargs)

    def http_get(self, url, headers=None, *args, **kwargs):
        """Perform an HTTP GET on the given URL.

        Args:
            url (unicode):
                The URL to perform the request on.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            tuple:
            A tuple of:

            * The response body (:py:class:`bytes`)
            * The response headers (:py:class:`dict`)

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self.http_request(url, headers=headers, method='GET', **kwargs)

    def http_post(self, url, body=None, fields=None, files=None,
                  content_type=None, headers=None, *args, **kwargs):
        """Perform an HTTP POST on the given URL.

        Args:
            url (unicode):
                The URL to perform the request on.

            body (unicode, optional):
                The request body. if not provided, it will be generated from
                the ``fields`` and ``files`` arguments.

            fields (dict, optional):
                Form fields to use to generate the request body. This argument
                will only be used if ``body`` is ``None``.

            files (dict, optional):
                Files to use to generate the request body. This argument will
                only be used if ``body`` is ``None``.

            content_type (unicode, optional):
                The content type of the request. If provided, it will be
                appended as the :mailheader:`Content-Type` header.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            tuple:
            A tuple of:

            * The response body (:py:class:`bytes`)
            * The response headers (:py:class:`dict`)

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        if headers:
            headers = headers.copy()
        else:
            headers = {}

        if body is None:
            if fields is not None:
                body, content_type = self.build_form_data(fields, files)
            else:
                body = ''

        if content_type:
            headers['Content-Type'] = content_type

        headers['Content-Length'] = '%d' % len(body)

        return self.http_request(url, body=body, headers=headers,
                                 method='POST', **kwargs)

    def http_request(self, url, body=None, headers=None, method='GET',
                     username=None, password=None):
        """Perform some HTTP operation on a given URL.

        If the ``username`` and ``password`` arguments are provided, the
        headers required for HTTP Basic Authentication will be added to
        the request.

        Args:
            url (unicode):
                The URL to open.

            body (unicode, optional):
                The request body.

            headers (dict, optional):
                Headers to include in the request.

            method (unicode, optional):
                The HTTP method to use to perform the request.

            username (unicode, optional):
                The username to use for HTTP Basic Authentication.

            password (unicode, optional):
                The password to use for HTTP Basic Authentication.

        Returns:
            tuple:
            A tuple of:

            * The response body (:py:class:`bytes`)
            * The response headers (:py:class:`dict`)

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        request = URLRequest(url, body, headers, method=method)

        if username is not None and password is not None:
            request.add_basic_auth(username, password)

        response = urlopen(request)

        return response.read(), response.headers

    #
    # JSON utility methods
    #

    def json_delete(self, *args, **kwargs):
        """Perform an HTTP DELETE and interpret the results as JSON.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_delete`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_delete`.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self._do_json_method(self.http_delete, *args, **kwargs)

    def json_get(self, *args, **kwargs):
        """Perform an HTTP GET and interpret the results as JSON.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_get`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_get`.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self._do_json_method(self.http_get, *args, **kwargs)

    def json_post(self, *args, **kwargs):
        """Perform an HTTP POST and interpret the results as JSON.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_post`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_post`.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self._do_json_method(self.http_post, *args, **kwargs)

    def _do_json_method(self, method, *args, **kwargs):
        """Parse the result of an HTTP operation as JSON.

        Args:
            method (callable):
                The callable to use to execute the request.

            *args (tuple):
                Positional arguments to pass to ``method``.

            **kwargs (dict):
                Keyword arguments to pass to ``method``.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            urllib2.HTTPError:
                When the HTTP request fails.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        data, headers = method(*args, **kwargs)

        if data:
            data = json.loads(data)

        return data, headers

    #
    # Internal utilities
    #

    @staticmethod
    def build_form_data(fields, files=None):
        """Encode data for use in an HTTP POST.

        Args:
            fields (dict):
                A mapping of field names (:py:class:`unicode`) to values.

            files (dict, optional):
                A mapping of field names (:py:class:`unicode`) to files
                (:py:class:`dict`).

        Returns:
            tuple:
            A tuple of:

            * The request content (:py:class:`unicode`).
            * The request content type (:py:class:`unicode`).
        """
        boundary = mimetools.choose_boundary()
        content_parts = []

        for key, value in six.iteritems(fields):
            if isinstance(key, six.text_type):
                key = key.encode('utf-8')

            if isinstance(value, six.text_type):
                value = value.encode('utf-8')

            content_parts.append(
                b'--%(boundary)s\r\n'
                b'Content-Disposition: form-data; name="%(key)s"\r\n'
                b'\r\n'
                b'%(value)s\r\n'
                % {
                    'boundary': boundary,
                    'key': key,
                    'value': value,
                }
            )

        if files:
            for key, data in six.iteritems(files):
                filename = data['filename']
                content = data['content']

                if isinstance(key, six.text_type):
                    key = key.encode('utf-8')

                if isinstance(filename, six.text_type):
                    filename = filename.encode('utf-8')

                if isinstance(content, six.text_type):
                    content = content.encode('utf-8')

                content_parts.append(
                    b'--%(boundary)s\r\n'
                    b'Content-Disposition: form-data; name="%(key)s";'
                    b' filename="%(filename)s"\r\n'
                    b'\r\n'
                    b'%(value)s\r\n'
                    % {
                        'boundary': boundary,
                        'key': key,
                        'filename': filename,
                        'value': content,
                    }
                )

        content_parts.append(b'--%s--' % boundary)

        content = b''.join(content_parts)
        content_type = b'multipart/form-data; boundary=%s' % boundary

        return content, content_type


class HostingService(object):
    """An interface to a hosting service for repositories and bug trackers.

    HostingService subclasses are used to more easily configure repositories
    and to make use of third party APIs to perform special operations not
    otherwise usable by generic repositories.

    A HostingService can specify forms for repository and bug tracker
    configuration.

    It can also provide a list of repository "plans" (such as public
    repositories, private repositories, or other types available to the hosting
    service), along with configuration specific to the plan. These plans will
    be available when configuring the repository.
    """

    name = None
    plans = None
    supports_bug_trackers = False
    supports_post_commit = False
    supports_repositories = False
    supports_ssh_key_association = False
    supports_two_factor_auth = False
    supports_list_remote_repositories = False
    has_repository_hook_instructions = False

    self_hosted = False
    repository_url_patterns = None

    client_class = HostingServiceClient

    #: Optional form used to configure authentication settings for an account.
    auth_form = None

    # These values are defaults that can be overridden in repository_plans
    # above.
    needs_authorization = False
    supported_scmtools = []
    form = None
    fields = []
    repository_fields = {}
    bug_tracker_field = None

    def __init__(self, account):
        """Initialize the hosting service.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to use with the service.
        """
        assert account
        self.account = account

        self.client = self.client_class(self)

    def is_authorized(self):
        """Return whether or not the account is currently authorized.

        An account may no longer be authorized if the hosting service
        switches to a new API that doesn't match the current authorization
        records. This function will determine whether the account is still
        considered authorized.

        Returns:
            bool:
            Whether or not the associated account is authorized.
        """
        return False

    def get_password(self):
        """Return the raw password for this hosting service.

        Not all hosting services provide this, and not all would need it.
        It's primarily used when building a Subversion client, or other
        SCMTools that still need direct access to the repository itself.

        Returns:
            unicode:
            The password.
        """
        return None

    def is_ssh_key_associated(self, repository, key):
        """Return whether or not the key is associated with the repository.

        If the given key is present amongst the hosting service's deploy keys
        for the given repository, then it is considered to be associated.

        Sub-classes should implement this when the hosting service supports
        SSH key association.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the key must be associated with.

            key (paramiko.PKey):
                The key to check for association.

        Returns:
            bool:
            Whether or not the key is associated with the repository.

        Raises:
            reviewboard.hostingsvcs.errors.SSHKeyAssociationError:
                If an error occured during communication with the hosting
                service.
        """
        raise NotImplementedError

    def associate_ssh_key(self, repository, key):
        """Associate an SSH key with a given repository.

        Sub-classes should implement this when the hosting service supports
        SSH key association.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to associate the key with.

            key (paramiko.PKey):
                The key to add to the repository's list of deploy keys.

        Raises:
            reviewboard.hostingsvcs.errors.SSHKeyAssociationError:
                If an error occured during key association.
        """
        raise NotImplementedError

    def authorize(self, username, password, hosting_url, credentials,
                  two_factor_auth_code=None, local_site_name=None,
                  *args, **kwargs):
        """Authorize an account for the hosting service.

        Args:
            username (unicode):
                The username for the account.

            password (unicode):
                The password for the account.

            hosting_url (unicode):
                The hosting URL for the service, if self-hosted.

            credentials (dict):
                All credentials provided by the authentication form. This
                will contain the username, password, and anything else
                provided by that form.

            two_factor_auth_code (unicode, optional):
                The two-factor authentication code provided by the user.

            local_site_name (unicode, optional):
                The Local Site name, if any, that the account should be
                bound to.

            *args (tuple):
                Extra unused positional arguments.

            **kwargs (dict):
                Extra keyword arguments containing values from the
                repository's configuration.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.

            reviewboard.hostingsvcs.errors.TwoFactorAuthCodeRequiredError:
                A two-factor authentication code is required to authorize
                this account. The request must be retried with the same
                credentials and with the ``two_factor_auth_code`` parameter
                provided.
        """
        raise NotImplementedError

    def check_repository(self, path, username, password, scmtool_class,
                         local_site_name, *args, **kwargs):
        """Checks the validity of a repository configuration.

        This performs a check against the hosting service or repository
        to ensure that the information provided by the user represents
        a valid repository.

        This is passed in the repository details, such as the path and
        raw credentials, as well as the SCMTool class being used, the
        LocalSite's name (if any), and all field data from the
        HostingServiceForm as keyword arguments.

        Args:
            path (unicode):
                The repository URL.

            username (unicode):
                The username to use.

            password (unicode):
                The password to use.

            scmtool_class (type):
                The subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`
                that should be used.

            local_site_name (unicode):
                The name of the local site associated with the repository, or
                ``None`.

            *args (tuple):
                Additional positional arguments, unique to each hosting
                service.

            **kwargs (dict):
                Additional keyword arguments, unique to each hosting service.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository is not valid.
        """
        scmtool_class.check_repository(path, username, password,
                                       local_site_name)

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Return the requested file.

        Files can only be returned from hosting services that support
        repositories.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (unicode):
                The file path.

            revision (unicode):
                The revision the file should be retrieved from.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Additional keyword arguments to pass to the SCMTool.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            NotImplementedError:
                If this hosting service does not support repositories.
        """
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().get_file(path, revision, **kwargs)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        """Return whether or not the given path exists in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to check for file existence.

            path (unicode):
                The file path.

            revision (unicode):
                The revision to check for file existence.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Additional keyword arguments to be passed to the SCMTool.

        Returns:
            bool:
            Whether or not the file exists at the given revision in the
            repository.

        Raises:
            NotImplementedError:
                If this hosting service does not support repositories.
        """
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().file_exists(path, revision, **kwargs)

    def get_branches(self, repository):
        """Return a list of all branches in the repositories.

        This should be implemented by subclasses, and is expected to return a
        list of Branch objects. One (and only one) of those objects should have
        the "default" field set to True.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository for which branches should be returned.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches.
        """
        raise NotImplementedError

    def get_commits(self, repository, branch=None, start=None):
        """Return a list of commits backward in history from a given point.

        This should be implemented by subclasses, and is expected to return a
        list of Commit objects (usually 30, but this is flexible depending on
        the limitations of the APIs provided.

        This can be called multiple times in succession using the "parent"
        field of the last entry as the start parameter in order to paginate
        through the history of commits in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve commits from.

            branch (unicode, optional):
                The branch to retrieve from. If this is not provided, the
                default branch will be used.

            start (unicode, optional):
                An optional starting revision. If this is not provided, the
                most recent commits will be returned.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.
        """
        raise NotImplementedError

    def get_change(self, repository, revision):
        """Return an individual change.

        This method should be implemented by subclasses.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to get the change from.

            revision (unicode):
                The revision to retrieve.

        Returns:
            reviewboard.scmtools.core.Commit:
            The change.
        """
        raise NotImplementedError

    def get_remote_repositories(self, owner=None, owner_type=None,
                                filter_type=None, start=None, per_page=None,
                                **kwargs):
        """Return a list of remote repositories for the owner.

        This method should be implemented by subclasses.

        Args:
            owner (unicode, optional):
                The owner of the repositories. This is usually a username.

            owner_type (unicode, optional):
                A hosting service-specific indicator of what the owner is (such
                as a user or a group).

            filter_type (unicode, optional):
                Some hosting service-specific criteria to filter by.

            start (int, optional):
                The index to start at.

            per_page (int, optional):
                The number of results per page.

        Returns:
            reviewboard.hostingsvcs.utils.APIPaginator:
            A paginator for the returned repositories.
        """
        raise NotImplementedError

    def get_remote_repository(self, repository_id):
        """Return the remote repository for the ID.

        This method should be implemented by subclasses.

        Args:
            repository_id (unicode):
                The repository's identifier. This is unique to each hosting
                service.

        Returns:
            reviewboard.hostingsvcs.repository.RemoteRepository:
            The remote repository.

        Raises:
            django.core.excptions.ObjectDoesNotExist:
                If the remote repository does not exist.
        """
        raise NotImplementedError

    @classmethod
    def get_repository_fields(cls, username, hosting_url, plan, tool_name,
                              field_vars):
        """Return the repository fields based on the given plan and tool.

        If the ``plan`` argument is specified, that will be used to fill in
        some tool-specific field values. Otherwise they will be retrieved from
        the :py:class:`HostingService`'s defaults.

        Args:
            username (unicode):
                The username.

            hosting_url (unicode):
                The URL of the repository.

            plan (unicode):
                The name of the plan.

            tool_name (unicode):
                The :py:attr:`~reviewboard.scmtools.core.SCMTool.name` of the
                :py:class:`~reviewboard.scmtools.core.SCMTool`.

            field_vars (dict):
                The field values from the hosting service form.

        Returns:
            dict:
            The filled in repository fields.

        Raises:
            KeyError:
               The provided plan is not valid for the hosting service.
        """
        if not cls.supports_repositories:
            raise NotImplementedError

        # Grab the list of fields for population below. We have to do this
        # differently depending on whether or not this hosting service has
        # different repository plans.
        fields = cls._get_field(plan, 'repository_fields')

        new_vars = field_vars.copy()
        new_vars['hosting_account_username'] = username

        if cls.self_hosted:
            new_vars['hosting_url'] = hosting_url
            new_vars['hosting_domain'] = urlparse(hosting_url)[1]

        results = {}

        assert tool_name in fields

        for field, value in six.iteritems(fields[tool_name]):
            try:
                results[field] = value % new_vars
            except KeyError as e:
                logging.error('Failed to generate %s field for hosting '
                              'service %s using %s and %r: Missing key %s'
                              % (field, six.text_type(cls.name), value,
                                 new_vars, e),
                              exc_info=1)
                raise KeyError(
                    _('Internal error when generating %(field)s field '
                      '(Missing key "%(key)s"). Please report this.') % {
                        'field': field,
                        'key': e,
                    })

        return results

    def get_repository_hook_instructions(self, request, repository):
        """Return instructions for setting up incoming webhooks.

        Subclasses can override this (and set
        `has_repository_hook_instructions = True` on the subclass) to provide
        instructions that administrators can see when trying to configure an
        incoming webhook for the hosting service.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            repository (reviewboard.scmtools.models.Repository):
                The repository for webhook setup instructions.

        Returns:
            django.utils.text.SafeText:
            Rendered and escaped HTML for displaying to the user.
        """
        raise NotImplementedError

    @classmethod
    def get_bug_tracker_requires_username(cls, plan=None):
        """Return whether or not the bug tracker requires usernames.

        Args:
            plan (unicode, optional):
                The name of the plan associated with the account.

        Raises:
            NotImplementedError:
                If the hosting service does not support bug tracking.
        """
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        return ('%(hosting_account_username)s' in
                cls._get_field(plan, 'bug_tracker_field', ''))

    @classmethod
    def get_bug_tracker_field(cls, plan, field_vars):
        """Return the bug tracker field for the given plan.

        Args:
            plan (unicode):
                The name of the plan associated with the account.

            field_vars (dict):
                The field values from the hosting service form.

        Returns:
            unicode:
            The value of the bug tracker field.

        Raises
            KeyError:
               The provided plan is not valid for the hosting service.
        """
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        bug_tracker_field = cls._get_field(plan, 'bug_tracker_field')

        if not bug_tracker_field:
            return ''

        try:
            return bug_tracker_field % field_vars
        except KeyError as e:
            logging.error('Failed to generate %s field for hosting '
                          'service %s using %r: Missing key %s'
                          % (bug_tracker_field, six.text_type(cls.name),
                             field_vars, e),
                          exc_info=1)
            raise KeyError(
                _('Internal error when generating %(field)s field '
                  '(Missing key "%(key)s"). Please report this.') % {
                    'field': bug_tracker_field,
                    'key': e,
                })

    @classmethod
    def _get_field(cls, plan, name, default=None):
        """Return the value of the field for the given plan.

        If ``plan`` is not ``None``, the field will be looked up in the plan
        configuration for the service. Otherwise the hosting service's default
        value will be used.

        Args:
            plan (unicode):
                The plan name.

            name (unicode):
                The field name.

            default (unicode, optional):
                A default value if the field is not present.

        Returns:
            unicode:
            The field value.
        """
        if cls.plans:
            assert plan

            for plan_name, info in cls.plans:
                if plan_name == plan and name in info:
                    return info[name]

        return getattr(cls, name, default)


_hosting_services = {}
_hostingsvcs_urlpatterns = {}
_populated = False


def _populate_hosting_services():
    """Populates a list of known hosting services from Python entrypoints.

    This is called any time we need to access or modify the list of hosting
    services, to ensure that we have loaded the initial list once.
    """
    global _populated

    if not _populated:
        _populated = True

        for entry in iter_entry_points('reviewboard.hosting_services'):
            try:
                register_hosting_service(entry.name, entry.load())
            except Exception as e:
                logging.error(
                    'Unable to load repository hosting service %s: %s'
                    % (entry, e))


def _add_hosting_service_url_pattern(name, cls):
    """Adds the URL patterns defined by the registering hosting service.

    Creates a base URL pattern for the hosting service based on the name
    and adds the repository_url_patterns of the class to the base URL
    pattern.

    Throws a KeyError if the hosting URL pattern has already been added
    before. Does not add the url_pattern of the hosting service if the
    repository_url_patterns property is None.
    """
    if name in _hostingsvcs_urlpatterns:
        raise KeyError('URL patterns for "%s" are already added.' % name)

    if cls.repository_url_patterns:
        cls_urlpatterns = patterns(
            '',
            url(r'^(?P<hosting_service_id>' + name + ')/',
                include(cls.repository_url_patterns))
        )
        _hostingsvcs_urlpatterns[name] = cls_urlpatterns
        hostingsvcs_urls.dynamic_urls.add_patterns(cls_urlpatterns)


def get_hosting_services():
    """Gets the list of hosting services."""
    _populate_hosting_services()

    return _hosting_services.values()


def get_hosting_service(name):
    """Retrieves the hosting service with the given name.

    If the hosting service is not found, None will be returned.
    """
    _populate_hosting_services()

    return _hosting_services.get(name, None)


def register_hosting_service(name, cls):
    """Registers a custom hosting service class.

    A name can only be registered once. A KeyError will be thrown if attempting
    to register a second time.
    """
    _populate_hosting_services()

    if name in _hosting_services:
        raise KeyError('"%s" is already a registered hosting service' % name)

    cls.hosting_service_id = name
    _hosting_services[name] = cls
    cls.id = name

    _add_hosting_service_url_pattern(name, cls)


def unregister_hosting_service(name):
    """Unregisters a previously registered hosting service."""
    _populate_hosting_services()

    try:
        del _hosting_services[name]
    except KeyError:
        logging.error('Failed to unregister unknown hosting service "%s"' %
                      name)
        raise KeyError('"%s" is not a registered hosting service' % name)

    if name in _hostingsvcs_urlpatterns:
        hostingsvc_urlpattern = _hostingsvcs_urlpatterns[name]
        hostingsvcs_urls.dynamic_urls.remove_patterns(hostingsvc_urlpattern)
        del _hostingsvcs_urlpatterns[name]


@receiver(initializing, dispatch_uid='populate_hosting_services')
def _on_initializing(**kwargs):
    _populate_hosting_services()
