"""Gerrit source code hosting support."""

from __future__ import unicode_literals

import base64
import json
import logging

from django import forms
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import (quote_plus, urlencode,
                                                 urljoin, urlparse)
from django.utils.six.moves.urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    build_opener)
from django.utils.translation import ugettext, ugettext_lazy as _

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            RepositoryError,
                                            HostingServiceAPIError)
from reviewboard.hostingsvcs.forms import (HostingServiceAuthForm,
                                           HostingServiceForm)
from reviewboard.hostingsvcs.service import (HostingService,
                                             HostingServiceClient,
                                             URLRequest)
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError


logger = logging.getLogger(__name__)

_PLUGIN_URL = 'https://github.com/reviewboard/gerrit-reviewboard-plugin/'


class GerritAuthForm(HostingServiceAuthForm):
    """The Gerrit authentication form.

    Gerrit requires an HTTP password to access the web API, so this form saves
    the provided password in the hosting account data.
    """

    def save(self, **kwargs):
        """Save the authentication form.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth`:HostingServiceAuthForm.save()
                <reviewboard.hostingsvcs.forms.HostingServiceAuthForm.save>`.

        Returns:
            reviewboard.hostingsvcs.models.HostingServiceAccount:
            The hosting service account.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                Information needed to authorize was missing, or authorization
                failed.
        """
        hosting_account = super(GerritAuthForm, self).save(save=False,
                                                           **kwargs)

        if not hosting_account.data:
            hosting_account.data = {}

        hosting_account.data['gerrit_http_password'] = encrypt_password(
            self.get_credentials()['password'])
        hosting_account.save()

        return hosting_account

    class Meta(object):
        help_texts = {
            'hosting_account_username': _(
                'Your HTTP username. You can find this under '
                '<tt>Settings &gt; HTTP Password</tt>.'
            ),
            'hosting_account_password': _(
                'Your HTTP password. You can find this under '
                '<tt>Settings &gt; HTTP Password</tt>.'
            ),
        }


class GerritForm(HostingServiceForm):
    """The Gerrit hosting service form."""

    gerrit_url = forms.URLField(
        label=_('Gerrit URL'),
        required=True,
        help_text=_('The full URL of your Gerrit instance, as in '
                    '<tt>http://gerrit.example.com/</tt>.'),
        widget=forms.TextInput(attrs={'size': 60}))

    gerrit_ssh_port = forms.IntegerField(
        label=_('SSH port'),
        required=True,
        help_text=_('The port configured for SSH access to Gerrit.'),
        initial=29418,
        min_value=1,
        max_value=65535,
        widget=forms.TextInput(attrs={'size': 60}))

    gerrit_project_name = forms.CharField(
        label=_('Project name'),
        required=True,
        help_text=_('The name of the project on Gerrit.'),
        widget=forms.TextInput(attrs={'size': 60}))

    def clean(self):
        """Clean the form.

        This method does no additional validation. It only parses the Gerrit
        URL to determine the domain to use for SSH access (since it will be the
        same domain as for HTTP access).

        Returns:
            dict:
            The cleaned form data.
        """
        self.cleaned_data = super(GerritForm, self).clean()

        gerrit_url = self.cleaned_data.get('gerrit_url')

        if gerrit_url:
            gerrit_domain = urlparse(gerrit_url).netloc

            if ':' in gerrit_domain:
                gerrit_domain = gerrit_domain.split(':', 1)[0]

            self.cleaned_data['gerrit_domain'] = gerrit_domain

        return self.cleaned_data


class GerritClient(HostingServiceClient):
    """The Gerrit hosting service API client."""

    _JSON_PREFIX = ")]}'\n"
    _JSON_PREFIX_LENGTH = len(_JSON_PREFIX)

    def __init__(self, hosting_service):
        """Initialize the client.

        Args:
            hosting_service (reviewboard.hostingsvcs.service.HostingService):
                The hosting service initializing this client.
        """
        super(GerritClient, self).__init__(hosting_service)
        self.account = hosting_service.account

    def get_opener(self, url, username, password):
        """Return an opener with an installed password manager.

        Gerrit's API requires HTTP Digest Auth for its API endpoints. Unlike
        HTTP Basic Auth, this method requires a failed request and response to
        build the digest header, so we cannot pre-compute the header and send
        it along with the initial request.

        Args:
            url (unicode):
                The only part of this required of the URL is the FQDN and the
                URL scheme. The location and fragment portions will be ignored.

            username (unicode):
                The username to use for authentication.

            password (unicode):
                The password to use for authentication.

        Returns:
            urllib2.OpenerDirector:
            The opener with the password manager installed.
        """
        assert username is not None
        assert password is not None

        result = urlparse(url)
        top_level_url = '%s://%s' % (result.scheme, result.netloc)

        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, top_level_url, username, password)
        return build_opener(HTTPDigestAuthHandler(password_mgr))

    def http_request(self, url, body=None, headers=None, method='GET',
                     username=None, password=None):
        """Make an HTTP request to the given URL and return the result.

        This method requires both the username and password arguments to be
        passed since all Gerrit API endpoints require authentication.

        Args:
            url (unicode):
                The URL to make the request against.

            body (unicode, optional):
                The request body.

            headers (dict, optional):
                Additional headers to include in the request.

            method (unicode, optional):
                The HTTP method to use for the request. This defaults to GET.

            username (unicode):
                The username to use for authentication.

            password (unicode):
                The password to use for authentication.

        Returns:
            tuple:
            A 2-tuple of:

            * The response body (:py:class:`bytes`).
            * The response headers (:py:class:`dict`).
        """
        assert username is not None
        assert password is not None

        opener = self.get_opener(url, username, password)
        request = URLRequest(url, body, headers, method=method)

        # Gerrit 2.14+ require Basic Auth, so add that header. Old versions
        # use Digest Auth, which get_opener() already prepared.
        if username is not None and password is not None:
            request.add_basic_auth(username, password)

        try:
            response = opener.open(request)
        except HTTPError as e:
            try:
                raise HostingServiceAPIError(e.reason, e.getcode(), e.read())
            except AttributeError:
                raise HostingServiceError(e.reason, e.getcode())
        except URLError as e:
            raise HostingServiceError(e.reason)

        return response.read(), response.headers

    def api_get(self, url, username=None, password=None, json=True, *args,
                **kwargs):
        """Make a request to the API and return the result.

        Args:
            url (unicode):
                The URL to make the request against.

            username (unicode, optional):
                The username to use when making the request. If not provided,
                the account username will be used.

                This argument must be passed when authorizing.

            password (unicode, optional):
                The password to use when making the request. If not provided,
                the account password will be used.

                This argument must be passed when authorizing.

            json (bool, optional):
                Whether or not to interpret the response as JSON. Defaults to
                ``True``.

            *args (tuple):
                Additional positional arguments to pass to the HTTP request
                method.

            **kwargs (dict):
                Additional keyword arguments to pass to the HTTP request
                method.

        Returns:
            object:
            One of the following:

            * If ``json`` is ``True``, the parsed response (:py:class:`dict`).
            * Otherwise, the raw response (:py:class:`unicode`).
        """
        if json:
            method = self.json_get
        else:
            method = self.http_get

        if username is None or password is None:
            username = self.account.username
            password = decrypt_password(
                self.account.data['gerrit_http_password'])

        return method(
            url,
            username=username,
            password=password,
            *args,
            **kwargs
        )[0]

    def _do_json_method(self, method, url, *args, **kwargs):
        """Make an HTTP request and interpret the result as JSON.

        Gerrit prepends all JSON responses with ``)]}'`` to ensure that they
        cannot be used inline. This method strips that off those characters
        from the response and interprets the rest as JSON.

        Args:
            method (callable):
                The method to use to make the request.

            url (unicode):
                The URL to make the request to

            *args (tuple):
                Positional arguments to pass to ``method``.

            **kwargs (dict):
                Keyword arguments to pass to ``method``.

        Returns:
            tuple:
            A 2-tuple of:

            * The response body parsed as JSON (:py:class:`dict`).
            * The response headers (:py:class:`dict`).
        """
        data, headers = method(url, *args, **kwargs)

        if data:
            if not data.startswith(self._JSON_PREFIX):
                logger.error(
                    'JSON response from Gerrit URL %s does not begin with '
                    '%r: %s',
                    url, self._JSON_PREFIX, data)
            else:
                data = json.loads(data[self._JSON_PREFIX_LENGTH:])

        return data, headers


class Gerrit(HostingService):
    """Source code hosting support for Gerrit.

    Gerrit does not have an API that supports being a hosting service, so the
    gerrit-reviewboard-plugin_ must be installed to use this hosting service.

    If authentication fails to detect the presence of the plugin, the user will
    be informed of such.

    .. _gerrit-reviewboard-plugin:
       https://downloads.reviewboard.org/releases/gerrit-reviewboard-plugin/
    """

    REQUIRED_PLUGIN_VERSION = (1, 0, 0)
    REQUIRED_PLUGIN_VERSION_STR = '%d.%d.%d' % REQUIRED_PLUGIN_VERSION

    name = _('Gerrit')
    client_class = GerritClient
    form = GerritForm
    auth_form = GerritAuthForm
    needs_authorization = True
    supports_repositories = True
    supports_post_commit = True
    supported_scmtools = ['Git']

    repository_fields = {
        'Git': {
            'path': 'ssh://%(hosting_account_username)s@%(gerrit_domain)s:'
                    '%(gerrit_ssh_port)s/%(gerrit_project_name)s',
            'mirror_path':
                'ssh://%(hosting_account_username)s@%(gerrit_domain)s/'
                '%(gerrit_ssh_port)s/%(gerrit_project_name)s',
        },
    }

    def check_repository(self, gerrit_url=None, gerrit_project_name=None,
                         *args, **kwargs):
        """Check that the repository is configured correctly.

        This method ensures that the user has access to an existing repository
        on the Gerrit server and that the ``gerrit-reviewboard`` plugin is
        installed and of a compatible version.

        Args:
            gerrit_url (unicode):
                The URL to the Gerrit server.

            gerrit_project_name (unicode):
                The repository's configured project name on Gerrit.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                One of the following:

                * The repository does not exist.
                * The user does not have access to the repository.
                * The ``gerrit-reviewboard`` plugin is not installed.
                * The ``gerrit-reviewboard`` plugin that is installed is an
                  incompatible version.
        """
        url = urljoin(gerrit_url,
                      'a/projects/%s' % quote_plus(gerrit_project_name))

        try:
            self.client.api_get(url, json=False)
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                raise RepositoryError(
                    ugettext('The project "%s" does not exist or you do not '
                             'have access to it.')
                    % gerrit_project_name)

            raise

        url = urljoin(gerrit_url, 'a/plugins/')

        try:
            rsp = self.client.api_get(url)
        except HostingServiceError as e:
            logger.exception(
                'Could not retrieve the list of Gerrit plugins from %s: %s',
                url, e)
            raise RepositoryError(
                ugettext('Could not retrieve the list of Gerrit plugins '
                         'from %(url).')
                % {
                    'url': url,
                })

        if 'gerrit-reviewboard' not in rsp:
            raise RepositoryError(
                ugettext('The "gerrit-reviewboard" plugin is not installed '
                         'on the server. See %(plugin_url)s for installation '
                         'instructions.')
                % {
                    'plugin_url': _PLUGIN_URL,
                })
        else:
            version_str = rsp['gerrit-reviewboard']['version']

            try:
                version = self._parse_plugin_version(version_str)
            except Exception as e:
                logger.exception(
                    'Could not parse gerrit-reviewboard plugin version "%s" '
                    'from %s: %s',
                    version, url, e)
                raise RepositoryError(
                    ugettext('Could not parse gerrit-reviewboard version: '
                             '"%(version)s" from URL %(url)s: %(error)s')
                    % {
                        'version': version,
                        'error': e,
                        'url': url,
                    })

            if version < self.REQUIRED_PLUGIN_VERSION:
                raise RepositoryError(
                    ugettext('The "gerrit-reviewboard" plugin on the server '
                             'is an incompatible version: found %(found)s but '
                             'version %(required)s or higher is required.')
                    % {
                        'found': version_str,
                        'required': self.REQUIRED_PLUGIN_VERSION_STR,
                    }
                )

    def authorize(self, username, password, credentials,
                  local_site_name=None, gerrit_url=None, *args, **kwargs):
        """Authorize against the Gerrit server.

        Args:
            username (unicode):
                The username to use for authentication.

            password  unicode):
                The password to use for authentication.

            credentials (dict):
                The credentials from the authentication form.

            local_site_name (unicode, optional):
                The name of the :py:class:`~reviewboard.site.models.LocalSite`
                the repository is associated with.

            gerrit_url (unicode):
                The URL of the Gerrit server.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The provided credentials were incorrect.
        """
        if gerrit_url is None:
            raise AuthorizationError('Gerrit URL is required.')

        url = urljoin(gerrit_url, '/a/projects/')

        try:
            self.client.api_get(url, username=username, password=password,
                                json=False)
        except HostingServiceError as e:
            if self.account.pk:
                self.account.data['authorized'] = False

            if e.http_code != 401:
                logger.error(
                    'Unknown HTTP response while authenticating with Gerrit '
                    'at %s: %s',
                    url, e)

                raise AuthorizationError(
                    ugettext('Could not authenticate with Gerrit at %(url): '
                             '%(error)s')
                    % {
                        'url': url,
                        'error': e.message,
                    },
                    http_code=e.http_code)

            raise AuthorizationError(
                ugettext('Unable to authenticate to Gerrit at %(url)s. The '
                         'username or password used may be invalid.')
                % {
                    'url': url,
                },
                http_code=e.http_code)

        self.account.data['authorized'] = True

    def is_authorized(self):
        """Return whether or not the account is authorized with Gerrit.

        Returns:
            bool:
            Whether or not the account has successfully authorized with Gerrit.
        """
        return self.account.data.get('authorized', False)

    def get_branches(self, repository):
        """Return the branches from Gerrit.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch branches for.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The list of branches.
        """
        url = self._build_project_api_url(repository, ('branches',))
        rsp = self.client.api_get(url)
        branches = []

        for branch in rsp:
            ref = branch['ref']

            if ref == 'refs/meta/config':
                continue
            elif ref.startswith('refs/heads/'):
                branch_id = ref[len('refs/heads/'):]
                commit = branch['revision']
            else:
                continue

            branches.append(Branch(
                id=branch_id,
                commit=commit,
                default=(branch_id == 'master'),
            ))

        return branches

    def get_commits(self, repository, branch=None, start=None, limit=None):
        """Return a list of commits from the API.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository configured to use Gerrit.

            branch (unicode, optional):
                The branch to retrieve commits for.

            start (unicode, optional):
                The commit SHA1 to start retrieving commits at.

            limit (int, optional):
                The number of commits to retrieve. If unspecified, the default
                is 30 (which is also the maximum).

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The commits returned by the API. These commits will not have diffs
            attached.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceAPIError:
                An error occurred communicating with the Gerrit API.
        """
        if not start:
            start = branch

        query = dict(
            (field, bytes(value))
            for field, value in (('start', start), ('limit', limit))
            if value is not None
        )

        url = self._build_project_api_url(repository, ('all-commits',),
                                          query=query)

        try:
            rsp = self.client.api_get(url)
        except HostingServiceAPIError as e:
            # get_change uses this under the hood to retrieve a single commit,
            # so we can specialize the error message to make it more useful in
            # that case.
            if limit == 1:
                raise HostingServiceAPIError(
                    ugettext('Could not retrieve commit "%(rev)s": %(error)s')
                    % {
                        'rev': start,
                        'error': e.message,
                    },
                    http_code=e.http_code,
                    rsp=e.rsp)
            else:
                raise HostingServiceAPIError(
                    ugettext('Could not retrieve commits starting at '
                             '"%(rev)s": %(error)s')
                    % {
                        'rev': start,
                        'error': e.message,
                    },
                    http_code=e.getcode(),
                    rsp=e.rsp)

        return [
            self._parse_commit(meta)
            for meta in rsp
        ]

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        """Return whether or not the file exists at the specified revision.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository configured to use Gerrit.

            path (unicode):
                The path to the file (ignored).

            revision (unicode):
                The file's Git object ID.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            bool:
            Whether or not the file exists.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceAPIError:
                An error occurred communicating with the Gerrit API.
        """
        url = self._build_project_api_url(repository, ('blobs', revision))

        try:
            self.client.api_get(url)
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                return False

            raise

        return True

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Return the contents of a file at the specified revision.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository configured to use Gerrit.

            path (unicode):
                The file path (ignored).

            revision (unicode):
                The file's Git object ID.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.hostingsvcs.errors.FileNotFoundError:
                The file does not exist in the remote repository.

            reviewboard.hostingsvcs.errors.HostingServiceAPIError:
                An error occurred communicating with the Gerrit API.
        """
        url = self._build_project_api_url(repository,
                                          ('blobs', revision, 'content'))

        try:
            rsp = self.client.api_get(url, json=False)
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                raise FileNotFoundError(path, revision=revision)

            raise HostingServiceAPIError(
                ugettext('Could not get file "%(file)s" at revision '
                         '"%(rev)s": %(error)s')
                % {
                    'file': path,
                    'rev': revision,
                    'error': e.read(),
                },
                http_code=e.http_code)

        try:
            return base64.b64decode(rsp)
        except Exception as e:
            raise HostingServiceAPIError(
                ugettext('An error occurred while retrieving "%(file)s" at '
                         'revision "%(rev)s" from Gerrit: the response could '
                         'not be decoded: %(error)s')
                % {
                    'file': path,
                    'rev': revision,
                    'error': e,
                })

    def get_change(self, repository, revision):
        """Return a single change.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository configured to use Gerrit.

            revision (unicode):
                The SHA1 of the commit to fetch.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit with its diff.
        """
        # The commit endpoint that Gerrit exposes is subtly different from the
        # one our plugin exposes and requires more work on our end to parse, so
        # we just use the all-commits endpoint we expose and limit it to a
        # single commit.
        commit = self.get_commits(repository, start=revision, limit=1)[0]

        url = self._build_project_api_url(repository,
                                          ('commits', revision, 'diff'))
        try:
            diff = self.client.api_get(url, json=False)
        except HostingServiceError as e:
            logger.exception('Could not retrieve change "%s": %s',
                             revision, e)
            raise RepositoryError(
                ugettext('Could not retrieve change "%(rev)s" from repository '
                         '%(repo)d: %(error)s"')
                % {
                    'rev': revision,
                    'repo': repository.id,
                    'error': e,
                })

        commit.diff = diff

        return commit

    def _parse_commit(self, meta, diff=None):
        """Parse and return the meta response and return a Commit.

        Args:
            meta (dict):
                A member of the JSON response from the ``all-commits``
                endpoint corresponding to a single commit.

            diff (bytes, optional):
                The diff corresponding to the commit.

        Returns:
            reviewboard.scmtools.core.Commit:
            The parsed commit.
        """
        commit = Commit(
            author_name=meta['author'],
            id=meta['revision'],
            date=meta['time'],
            message=meta['message'],
            diff=diff
        )

        if meta['parents']:
            commit.parent = meta['parents'][0]

        return commit

    def _parse_plugin_version(self, version_str):
        """Parse a plugin version string into a tuple.

        Args:
            version_str (unicode):
                A version string such as "1.0.0".

        Returns:
            tuple:
            A 3-tuple of the plugin version as ints.
        """
        return tuple(map(int, version_str.split('.')))

    def _build_project_api_url(self, repository, rest_parts, query=None):
        """Return an API URL for the Gerrit projects API.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository configured to use Gerrit.

            rest_parts (iterable):
                The rest of the URL parts.

            **query (dict, optional):
                The query parameters to append to the URL.

        Returns:
            unicode:
            The full URL.
        """
        parts = [
            'a',
            'projects',
            quote_plus(repository.extra_data['gerrit_project_name']),
        ]
        parts.extend(rest_parts)

        url = urljoin(repository.extra_data['gerrit_url'], '/'.join(parts))

        if query:
            url = '%s/?%s' % (url, urlencode(query))
        else:
            url = '%s/' % url

        return url
