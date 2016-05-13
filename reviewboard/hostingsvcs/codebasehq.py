from __future__ import unicode_literals

import logging
from xml.dom.minidom import parseString

from django import forms
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.translation import ugettext_lazy as _, ugettext

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceAPIError,
                                            RepositoryError)
from reviewboard.hostingsvcs.forms import (HostingServiceAuthForm,
                                           HostingServiceForm)
from reviewboard.hostingsvcs.service import (HostingService,
                                             HostingServiceClient)
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError


class CodebaseHQAuthForm(HostingServiceAuthForm):
    api_key = forms.CharField(
        label=_('API key'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The API key provided to your Codebase account. This is '
                    'available in My Profile under API Credentials.'))

    domain = forms.CharField(
        label=_('Codebase domain'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The subdomain used to access your Codebase account. '
                    'This is the "<tt>subdomain</tt>" of '
                    '<tt>subdomain</tt>.codebasehq.com.'))

    def get_credentials(self):
        credentials = super(CodebaseHQAuthForm, self).get_credentials()
        credentials.update({
            'domain': self.cleaned_data['domain'],
            'api_key': self.cleaned_data['api_key'],
        })

        return credentials

    class Meta(object):
        help_texts = {
            'hosting_account_username': _(
                'The username you use to log into Codebase. This should '
                '<em>not</em> include the domain name.'
            ),
            'hosting_account_password': _(
                'The password you use to log into Codebase. This is separate '
                'from the API key below.'
            ),
        }


class CodebaseHQForm(HostingServiceForm):
    codebasehq_project_name = forms.CharField(
        label=_('Project name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    codebasehq_repo_name = forms.CharField(
        label=_('Repository short name'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The short name of your repository. This can be found by '
                    'clicking the Settings button on the right-hand '
                    'side of the repository browser.'))


class CodebaseHQClient(HostingServiceClient):
    """Client for talking to the Codebase API.

    This implements the API methods that the hosting service needs, converting
    requests into API calls and those back into structured results.
    """

    #: Mimetype used for API requests and responses.
    API_MIMETYPE = 'application/xml'

    def __init__(self, hosting_service):
        """Initialize the client.

        Args:
            hosting_service (CodebaseHQ):
                The hosting service that owns this client.
        """
        self.hosting_service = hosting_service

    def api_get_file(self, repository, project_name, repo_name, path,
                     revision):
        """Return the content of a file in a repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository entry in Review Board.

            project_name (unicode):
                The name of the Codebase project.

            repo_name (unicode):
                The name of the repository.

            path (unicode):
                The path to the file in the repository.

            revision (unicode):
                The revision of the file or commit.

        Returns:
            bytes:
            The contents of the file.
        """
        url = '%s/%s/blob/' % (project_name, repo_name)

        if repository.tool.name == 'Git':
            url += revision
        else:
            if path.startswith('/'):
                path = path[1:]

            url += '%s/%s' % (revision, path)

        result = self.api_get(self.build_api_url(url), raw_content=True)

        # XXX As of May 2, 2016, Codebase's file fetching API has a bug where
        #     the final trailing newline is missing from file contents. A
        #     report has been filed, but until this is fixed, we need to work
        #     around this by adding back a newline.
        #
        #     In order to do this without outright breaking files, we'll try to
        #     determine the appropriate newline type. This is fragile, but
        #     hopefully temporary.
        if b'\r\n' in result:
            result += b'\r\n'
        else:
            result += b'\n'

        return result

    def api_get_public_keys(self, username):
        """Return information on all public keys for a user.

        Args:
            username (unicode):
                The user to fetch public keys for.

        Returns:
            dict:
            Information on each of the user's public keys.
        """
        return self.api_get(self.build_api_url('users/%s/public_keys'
                                               % username))

    def api_get_repository(self, project_name, repo_name):
        """Return information on a repository.

        Args:
            project_name (unicode):
                The name of the Codebase project.

            repo_name (unicode):
                The name of the repository.

        Returns:
            dict:
            Information on the repository.

            See https://support.codebasehq.com/kb/repositories for the
            data returned.
        """
        return self.api_get(
            self.build_api_url('%s/%s' % (project_name, repo_name)))

    def build_api_url(self, url):
        """Return the URL for an API call.

        Args:
            url (unicode):
                The relative URL for the API call.

        Returns:
            unicode:
            The absolute URL for the API call.
        """
        return 'https://api3.codebasehq.com/%s' % url

    def api_get(self, url, raw_content=False):
        """Perform an HTTP GET request to the API.

        Args:
            url (unicode):
                The full URL to the API resource.

            raw_content (bool, optional):
                If set to ``True``, the raw content of the result will be
                returned, instead of a parsed XML result.

        Returns:
            object:
            The parsed content of the result, as a dictionary, or the raw
            bytes content if ``raw_content`` is ``True``.
        """
        hosting_service = self.hosting_service

        try:
            account_data = hosting_service.account.data
            api_username = '%s/%s' % (account_data['domain'],
                                      hosting_service.account.username)
            api_key = decrypt_password(account_data['api_key'])

            data, headers = self.http_get(
                url,
                username=api_username,
                password=api_key,
                headers={
                    'Accept': self.API_MIMETYPE,
                })

            if raw_content:
                return data
            else:
                return self.parse_xml(data)
        except HTTPError as e:
            data = e.read()
            msg = six.text_type(e)

            rsp = self.parse_xml(data)

            if rsp and 'errors' in rsp:
                errors = rsp['errors']

                if 'error' in errors:
                    msg = errors['error']

            if e.code == 401:
                raise AuthorizationError(msg)
            else:
                raise HostingServiceAPIError(msg, http_code=e.code, rsp=rsp)
        except URLError as e:
            raise HostingServiceAPIError(e.reason)

    def get_xml_text(self, nodes):
        """Return the text contents of a set of XML nodes.

        Args:
            nodes (list of xml.dom.minidom.Element):
                The list of nodes.

        Returns:
            unicode:
            The text content of the nodes.
        """
        return ''.join(
            node.data
            for node in nodes
            if node.nodeType == node.TEXT_NODE
        )

    def parse_xml(self, s):
        """Return the parsed content for an XML document.

        Args:
            s (unicode):
                The XML document as a string.

        Returns:
            dict:
            The parsed content of the XML document, with each key
            being a dictionary of other parsed content.

            If the document cannot be parsed, this will return ``None``.
        """
        try:
            doc = parseString(s)
        except:
            return None

        root = doc.documentElement

        return {
            root.tagName: self._parse_xml_node(root),
        }

    def _parse_xml_node(self, node):
        """Return the parsed content for a node in an XML document.

        This parses the content of a Codebase XML document, turning it into
        arrays, strings, and dictionaries of data.

        Args:
            node (xml.dom.minidom.Element):
                The node being parsed.

        Returns:
            object:
            The parsed content of the node, based on the type of node being
            processed.
        """
        node_type = node.getAttribute('type')
        is_nil = node.getAttribute('nil')

        if node_type == 'array':
            result = [
                self._parse_xml_node(child)
                for child in node.childNodes
                if child.nodeType == child.ELEMENT_NODE
            ]
        elif is_nil == 'true':
            result = None
        else:
            child_nodes = [
                child
                for child in node.childNodes
                if child.nodeType == child.ELEMENT_NODE
            ]

            if child_nodes:
                result = dict([
                    (child.tagName, self._parse_xml_node(child))
                    for child in child_nodes
                ])
            else:
                result = self.get_xml_text(node.childNodes)

        return result


class CodebaseHQ(HostingService):
    """Repository hosting support for Codebase.

    Codebase is a repository hosting service that supports Subversion, Git,
    and Mercurial. It's available at https://codebasehq.com.

    This integration provides repository validation and file fetching. Due to
    API limitations, it does not support post-commit review at this time.
    """

    name = 'Codebase HQ'
    form = CodebaseHQForm
    auth_form = CodebaseHQAuthForm

    needs_authorization = True
    supports_repositories = True

    supported_scmtools = ['Git', 'Subversion', 'Mercurial']

    repository_fields = {
        'Git': {
            'path': 'git@codebasehq.com:%(domain)s/'
                    '%(codebasehq_project_name)s/'
                    '%(codebasehq_repo_name)s.git',
        },
        'Subversion': {
            'path': 'https://%(domain)s.codebasehq.com/'
                    '%(codebasehq_project_name)s/'
                    '%(codebasehq_repo_name)s.svn',
        },
        'Mercurial': {
            'path': 'https://%(domain)s.codebasehq.com/'
                    'projects/%(codebasehq_project_name)s/repositories/'
                    '%(codebasehq_repo_name)s/',
        },
    }

    #: A mapping of Codebase SCM types to SCMTool names.
    REPO_SCM_TOOL_MAP = {
        'git': 'Git',
        'svn': 'Subversion',
        'hg': 'Mercurial',
    }

    def __init__(self, *args, **kwargs):
        """Initialize the hosting service.

        Args:
            *args (tuple):
                Positional arguments for the parent constructor.

            **kwargs (dict):
                Keyword arguments for the parent constructor.
        """
        super(CodebaseHQ, self).__init__(*args, **kwargs)

        self.client = CodebaseHQClient(self)

    def authorize(self, username, password, credentials, *args, **kwargs):
        """Authorize an account for Codebase.

        Codebase usees HTTP Basic Auth with an API username (consisting of the
        Codebase team's domain and the account username) and an API key (for
        the password) for API calls, and a standard username/password for
        Subversion repository access. We need to store all of this.

        Args:
            username (unicode):
                The username to authorize.

            password (unicode):
                The API token used as a password.

            credentials (dict):
                Additional credentials from the authentication form.

            *args (tuple):
                Extra unused positional arguments.

            **kwargs (dict):
                Extra unused keyword arguments.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.
        """
        self.account.data.update({
            'domain': credentials['domain'],
            'api_key': encrypt_password(credentials['api_key']),
            'password': encrypt_password(password),
        })

        # Test the account to make sure the credentials are fine. Note that
        # we can only really sanity-check the API token, domain, and username
        # from here. There's no way good way to check the actual password,
        # which we only use for Subversion repositories.
        #
        # This will raise a suitable error message if authorization fails.
        try:
            self.client.api_get_public_keys(username)
        except AuthorizationError:
            raise AuthorizationError(
                ugettext('One or more of the credentials provided were not '
                         'accepted by Codebase.'))

        self.account.save()

    def is_authorized(self):
        """Return if the account has been authorized.

        This checks if all the modern authentication details are stored along
        with the account.

        Returns:
            bool:
            ``True`` if all required credentials are set for the account.
        """
        return (self.account.data.get('api_key') is not None and
                self.account.data.get('password') is not None and
                self.account.data.get('domain') is not None)

    def get_password(self):
        """Return the password for this account.

        This is used primarily for Subversion repositories, so that direct
        access can be performed in order to fetch properties and other
        information.

        This does not return the API key.

        Returns:
            unicode:
            The account password for repository access.
        """
        return decrypt_password(self.account.data['password'])

    def check_repository(self, codebasehq_project_name=None,
                         codebasehq_repo_name=None, tool_name=None,
                         *args, **kwargs):
        """Check the validity of a repository.

        This will perform an API request against Codebase to get information on
        the repository. This will throw an exception if the repository was not
        found, and return cleanly if it was found.

        Args:
            codebase_project_name (unicode):
                The name of the project on Codebase.

            codebasehq_repo_name (unicode):
                The name of the repository on Codebase.

            tool_name (unicode):
                The name of the SCMTool for the repository.

            *args (tuple):
                Extra unused positional arguments passed to this function.

            **kwargs (dict):
                Extra unused keyword arguments passed to this function.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository was not found.
        """
        # The form should enforce these values.
        assert codebasehq_project_name
        assert codebasehq_repo_name
        assert tool_name

        try:
            info = self.client.api_get_repository(codebasehq_project_name,
                                                  codebasehq_repo_name)
        except HostingServiceAPIError as e:
            logging.error('Error finding Codebase repository "%s" for '
                          'project "%s": %s',
                          codebasehq_repo_name, codebasehq_project_name,
                          e)

            raise RepositoryError(
                ugettext('A repository with this name and project was '
                         'not found.'))

        try:
            scm_type = info['repository']['scm']
        except KeyError:
            logging.error('Missing "scm" field for Codebase HQ repository '
                          'payload: %r',
                          info)

            raise RepositoryError(
                ugettext('Unable to determine the type of repository '
                         'from the Codebase API. Please report this.'))

        try:
            expected_tool_name = self.REPO_SCM_TOOL_MAP[scm_type]
        except KeyError:
            logging.error('Unexpected "scm" value "%s" for Codebase HQ '
                          'repository, using payload: %r',
                          scm_type, info)

            raise RepositoryError(
                ugettext('Unable to determine the type of repository '
                         'from the Codebase API. Please report this.'))

        if expected_tool_name != tool_name:
            raise RepositoryError(
                ugettext("The repository type doesn't match what you "
                         "selected. Did you mean %s?")
                % expected_tool_name)

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Returns the content of a file in a repository.

        This will perform an API request to fetch the contents of a file.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository containing the file.

            path (unicode):
                The path to the file in the repository.

            revision (unicode):
                The revision of the file in the repository.

            *args (tuple):
                Extra unused positional arguments passed to this function.

            **kwargs (dict):
                Extra unused keyword arguments passed to this function.

        Returns:
            byets:
            The content of the file in the repository.
        """
        try:
            return self.client.api_get_file(
                repository,
                repository.extra_data['codebasehq_project_name'],
                repository.extra_data['codebasehq_repo_name'],
                path, revision)
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                raise FileNotFoundError(path, revision)
            else:
                logging.warning('Failed to fetch file from Codebase HQ '
                                'repository %s: %s',
                                repository, e)
                raise

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        """Returns whether a given file exists.

        This will perform an API request to fetch the contents of a file,
        returning ``True`` if the content could be fetched.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository containing the file.

            path (unicode):
                The path to the file in the repository.

            revision (unicode):
                The revision of the file in the repository.

            *args (tuple):
                Extra unused positional arguments passed to this function.

            **kwargs (dict):
                Extra unused keyword arguments passed to this function.

        Returns:
            bool:
            ``True`` if the file exists in the repository.
        """
        try:
            self.client.api_get_file(
                repository,
                repository.extra_data['codebasehq_project_name'],
                repository.extra_data['codebasehq_repo_name'],
                path, revision)

            return True
        except HostingServiceAPIError:
            return False
