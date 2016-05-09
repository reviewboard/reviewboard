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
    def __init__(self, url, body='', headers={}, method='GET'):
        BaseURLRequest.__init__(self, url, body, headers)
        self.method = method

    def get_method(self):
        return self.method


class HostingServiceClient(object):
    """Client for communicating with a hosting service's API.

    This implementation includes abstractions for performing HTTP operations,
    and wrappers for those to interpret responses as JSON data.

    HostingService subclasses can also include an override of this class to add
    additional checking (such as GitHub's checking of rate limit headers), or
    add higher-level API functionality.
    """
    def __init__(self, hosting_service):
        pass

    #
    # HTTP utility methods
    #

    def http_delete(self, url, headers={}, *args, **kwargs):
        """Perform an HTTP DELETE on the given URL."""
        return self.http_request(url, headers=headers, method='DELETE',
                                 **kwargs)

    def http_get(self, url, *args, **kwargs):
        """Perform an HTTP GET on the given URL."""
        return self.http_request(url, method='GET', **kwargs)

    def http_post(self, url, body=None, fields={}, files={}, content_type=None,
                  headers={}, *args, **kwargs):
        """Perform an HTTP POST on the given URL."""
        headers = headers.copy()

        if body is None:
            if fields is not None:
                body, content_type = self._build_form_data(fields, files)
            else:
                body = ''

        if content_type:
            headers['Content-Type'] = content_type

        headers['Content-Length'] = '%d' % len(body)

        return self.http_request(url, body=body, headers=headers,
                                 method='POST', **kwargs)

    def http_request(self, url, body=None, headers={}, method='GET', **kwargs):
        """Perform some HTTP operation on a given URL."""
        r = self._build_request(url, body, headers, method=method, **kwargs)
        u = urlopen(r)

        return u.read(), u.headers

    #
    # JSON utility methods
    #

    def json_delete(self, *args, **kwargs):
        """Perform an HTTP DELETE and interpret the results as JSON."""
        return self._do_json_method(self.http_delete, *args, **kwargs)

    def json_get(self, *args, **kwargs):
        """Perform an HTTP GET and interpret the results as JSON."""
        return self._do_json_method(self.http_get, *args, **kwargs)

    def json_post(self, *args, **kwargs):
        """Perform an HTTP POST and interpret the results as JSON."""
        return self._do_json_method(self.http_post, *args, **kwargs)

    def _do_json_method(self, method, *args, **kwargs):
        """Internal helper for JSON operations."""
        data, headers = method(*args, **kwargs)

        if data:
            data = json.loads(data)

        return data, headers

    #
    # Internal utilities
    #

    def _build_request(self, url, body=None, headers={}, username=None,
                       password=None, method='GET'):
        """Build a URLRequest object, including HTTP Basic auth"""
        r = URLRequest(url, body, headers, method=method)

        if username is not None and password is not None:
            auth_key = username + ':' + password
            r.add_header(HTTPBasicAuthHandler.auth_header,
                         'Basic %s' %
                         base64.b64encode(auth_key.encode('utf-8')))

        return r

    def _build_form_data(self, fields, files):
        """Encodes data for use in an HTTP POST."""
        BOUNDARY = mimetools.choose_boundary()
        content = ""

        for key in fields:
            content += "--" + BOUNDARY + "\r\n"
            content += "Content-Disposition: form-data; name=\"%s\"\r\n" % key
            content += "\r\n"
            content += six.text_type(fields[key]) + "\r\n"

        for key in files:
            filename = files[key]['filename']
            value = files[key]['content']
            content += "--" + BOUNDARY + "\r\n"
            content += "Content-Disposition: form-data; name=\"%s\"; " % key
            content += "filename=\"%s\"\r\n" % filename
            content += "\r\n"
            content += value + "\r\n"

        content += "--" + BOUNDARY + "--\r\n"
        content += "\r\n"

        content_type = "multipart/form-data; boundary=%s" % BOUNDARY

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
        assert account
        self.account = account

        self.client = self.client_class(self)

    def is_authorized(self):
        """Returns whether or not the account is currently authorized.

        An account may no longer be authorized if the hosting service
        switches to a new API that doesn't match the current authorization
        records. This function will determine whether the account is still
        considered authorized.
        """
        return False

    def get_password(self):
        """Returns the raw password for this hosting service.

        Not all hosting services provide this, and not all would need it.
        It's primarily used when building a Subversion client, or other
        SCMTools that still need direct access to the repository itself.
        """
        return None

    def is_ssh_key_associated(self, repository, key):
        """Returns whether or not the key is associated with the repository.

        If the ``key`` (an instance of :py:mod:`paramiko.PKey`) is present
        among the hosting service's deploy keys for a given ``repository`` or
        account, then it is considered associated. If there is a problem
        checking with the hosting service, an :py:exc:`SSHKeyAssociationError`
        will be raised.
        """
        raise NotImplementedError

    def associate_ssh_key(self, repository, key):
        """Associates an SSH key with a given repository

        The ``key`` (an instance of :py:mod:`paramiko.PKey`) will be added to
        the hosting service's list of deploy keys (if possible). If there
        is a problem uploading the key to the hosting service, a
        :py:exc:`SSHKeyAssociationError` will be raised.
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
        """
        return scmtool_class.check_repository(path, username, password,
                                              local_site_name)

    def get_file(self, repository, path, revision, *args, **kwargs):
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().get_file(path, revision, **kwargs)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().file_exists(path, revision, **kwargs)

    def get_branches(self, repository):
        """Get a list of all branches in the repositories.

        This should be implemented by subclasses, and is expected to return a
        list of Branch objects. One (and only one) of those objects should have
        the "default" field set to True.
        """
        raise NotImplementedError

    def get_commits(self, repository, branch=None, start=None):
        """Get a list of commits backward in history from a given point.

        This should be implemented by subclasses, and is expected to return a
        list of Commit objects (usually 30, but this is flexible depending on
        the limitations of the APIs provided.

        This can be called multiple times in succession using the "parent"
        field of the last entry as the start parameter in order to paginate
        through the history of commits in the repository.
        """
        raise NotImplementedError

    def get_change(self, repository, revision):
        """Get an individual change.

        This should be implemented by subclasses, and is expected to return a
        tuple of (commit message, diff), both strings.
        """
        raise NotImplementedError

    def get_remote_repositories(self, owner=None, owner_type=None,
                                filter_type=None, start=None, per_page=None):
        """Get a list of remote repositories for the owner.

        This should be implemented by subclasses, and is expected to return an
        APIPaginator providing pages of RemoteRepository objects.

        The ``start`` and ``per_page`` parameters can be used to control
        where pagination begins and how many results are returned per page,
        if the subclass supports it.

        ``owner`` is expected to default to a reasonable value (typically
        the linked account's username). The hosting service may also require
        an ``owner_type`` value that identifies what the ``owner`` means.
        This value is specific to the hosting service backend.

        Likewise, ``filter_type`` is specific to the hosting service backend.
        If supported, it may be used to filter the types of hosting services.
        """
        raise NotImplementedError

    def get_remote_repository(self, repository_id):
        """Get the remote repository for the ID.

        This should be implemented by subclasses, and is expected to return
        a RemoteRepository if found, or raise ObjectDoesNotExist if not found.
        """
        raise NotImplementedError

    @classmethod
    def get_repository_fields(cls, username, hosting_url, plan, tool_name,
                              field_vars):
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
        """Returns instructions for setting up incoming webhooks.

        Subclasses can override this (and set
        `has_repository_hook_instructions = True` on the subclass) to provide
        instructions that administrators can see when trying to configure an
        incoming webhook for the hosting service.

        This is expected to return HTML for the instructions. The function
        is responsible for escaping any content.
        """
        raise NotImplementedError

    @classmethod
    def get_bug_tracker_requires_username(cls, plan=None):
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        return ('%(hosting_account_username)s' in
                cls._get_field(plan, 'bug_tracker_field', ''))

    @classmethod
    def get_bug_tracker_field(cls, plan, field_vars):
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
