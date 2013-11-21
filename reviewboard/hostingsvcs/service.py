from __future__ import unicode_literals

import base64
import json
import logging
import mimetools

from django.utils.translation import ugettext_lazy as _
from djblets.util.compat import six
from djblets.util.compat.six.moves.urllib.parse import urlparse
from djblets.util.compat.six.moves.urllib.request import (
    Request as URLRequest,
    HTTPBasicAuthHandler,
    urlopen)
from pkg_resources import iter_entry_points


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
    self_hosted = False

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

    def is_authorized(self):
        """Returns whether or not the account is currently authorized.

        An account may no longer be authorized if the hosting service
        switches to a new API that doesn't match the current authorization
        records. This function will determine whether the account is still
        considered authorized.
        """
        return False

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

    def authorize(self, username, password, hosting_url, local_site_name=None,
                  *args, **kwargs):
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

        return repository.get_scmtool().get_file(path, revision)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().file_exists(path, revision)

    def get_branches(self, repository):
        """Get a list of all branches in the repositories.

        This should be implemented by subclasses, and is expected to return a
        list of Branch objects. One (and only one) of those objects should have
        the "default" field set to True.
        """
        raise NotImplementedError

    def get_commits(self, repository, start=None):
        """Get a list of commits backward in history from a given starting point.

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

    #
    # HTTP utility methods
    #

    def _json_get(self, *args, **kwargs):
        data, headers = self._http_get(*args, **kwargs)
        return json.loads(data), headers

    def _json_post(self, *args, **kwargs):
        data, headers = self._http_post(*args, **kwargs)
        return json.loads(data), headers

    def _http_get(self, url, *args, **kwargs):
        return self._http_request(url, **kwargs)

    def _http_post(self, url, body=None, fields={}, files={},
                   content_type=None, headers={}, *args, **kwargs):
        headers = headers.copy()

        if body is None:
            if fields is not None:
                body, content_type = self._build_form_data(fields, files)
            else:
                body = ''

        if content_type:
            headers['Content-Type'] = content_type

        headers['Content-Length'] = '%d' % len(body)

        return self._http_request(url, body, headers, **kwargs)

    def _build_request(self, url, body=None, headers={}, username=None,
                       password=None):
        r = URLRequest(url, body, headers)

        if username is not None and password is not None:
            auth_key = username + ':' + password
            r.add_header(HTTPBasicAuthHandler.auth_header,
                         'Basic %s' %
                         base64.b64encode(auth_key.encode('utf-8')))

        return r

    def _http_request(self, url, body=None, headers={}, **kwargs):
        r = self._build_request(url, body, headers, **kwargs)
        u = urlopen(r)

        return u.read(), u.headers

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

        return content_type, content


_hosting_services = {}


def _populate_hosting_services():
    """Populates a list of known hosting services from Python entrypoints.

    This is called any time we need to access or modify the list of hosting
    services, to ensure that we have loaded the initial list once.
    """
    if not _hosting_services:
        for entry in iter_entry_points('reviewboard.hosting_services'):
            try:
                _hosting_services[entry.name] = entry.load()
            except Exception as e:
                logging.error(
                    'Unable to load repository hosting service %s: %s'
                    % (entry, e))


def get_hosting_services():
    """Gets the list of hosting services.

    This will return an iterator for iterating over each hosting service.
    """
    _populate_hosting_services()

    for name, cls in six.iteritems(_hosting_services):
        yield name, cls


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

    _hosting_services[name] = cls


def unregister_hosting_service(name):
    """Unregisters a previously registered hosting service."""
    _populate_hosting_services()

    try:
        del _hosting_services[name]
    except KeyError:
        logging.error('Failed to unregister unknown hosting service "%s"' %
                      name)
        raise KeyError('"%s" is not a registered hosting service' % name)
