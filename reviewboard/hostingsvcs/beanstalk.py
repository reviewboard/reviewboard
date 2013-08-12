from urllib import quote
from urllib2 import HTTPError, URLError

from django import forms
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.crypto import decrypt_password, encrypt_password
from reviewboard.scmtools.errors import FileNotFoundError


class BeanstalkForm(HostingServiceForm):
    beanstalk_account_domain = forms.CharField(
        label=_('Beanstalk account domain'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('This is the <tt>domain</tt> part of '
                    '<tt>domain.beanstalkapp.com</tt>'))

    beanstalk_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class Beanstalk(HostingService):
    """Hosting service support for Beanstalk.

    Beanstalk is a source hosting service that supports Git and Subversion
    repositories. It's available at http://beanstalkapp.com/.
    """
    name = 'Beanstalk'

    needs_authorization = True
    supports_bug_trackers = False
    supports_repositories = True
    supported_scmtools = ['Git', 'Subversion']

    form = BeanstalkForm
    repository_fields = {
        'Git': {
            'path': 'git@%(beanstalk_account_domain)s'
                    '.beanstalkapp.com:/%(beanstalk_repo_name)s.git',
            'mirror_path': 'https://%(beanstalk_account_domain)s'
                           '.git.beanstalkapp.com/%(beanstalk_repo_name)s.git',
        },
        'Subversion': {
            'path': 'https://%(beanstalk_account_domain)s'
                    '.svn.beanstalkapp.com/%(beanstalk_repo_name)s/',
        },
    }

    def check_repository(self, beanstalk_account_domain=None,
                         beanstalk_repo_name=None, *args, **kwargs):
        """Checks the validity of a repository.

        This will perform an API request against Beanstalk to get
        information on the repository. This will throw an exception if
        the repository was not found, and return cleanly if it was found.
        """
        self._api_get_repository(beanstalk_account_domain, beanstalk_repo_name)

    def authorize(self, username, password, hosting_url,
                  local_site_name=None, *args, **kwargs):
        """Authorizes the Beanstalk repository.

        Beanstalk uses HTTP Basic Auth for the API, so this will store the
        provided password, encrypted, for use in later API requests.
        """
        self.account.data['password'] = encrypt_password(password)
        self.account.save()

    def is_authorized(self):
        """Determines if the account has supported authorization tokens.

        This just checks if there's a password set on the account.
        """
        return self.account.data.get('password', None) is not None

    def get_file(self, repository, path, revision, base_commit_id=None,
                 *args, **kwargs):
        """Fetches a file from Beanstalk.

        This will perform an API request to fetch the contents of a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        revision = self._normalize_revision(repository, path, revision,
                                            base_commit_id)

        try:
            node_data = self._api_get_node(repository, path, revision,
                                           contents=True)
            return node_data['contents']
        except (HTTPError, URLError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, base_commit_id=None,
                        *args, **kwargs):
        """Determines if a file exists.

        This will perform an API request to fetch the metadata for a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        try:
            revision = self._normalize_revision(repository, path, revision,
                                                base_commit_id)

            self._api_get_node(repository, path, revision)

            return True
        except (HTTPError, URLError, FileNotFoundError):
            return False

    def _normalize_revision(self, repository, path, revision, base_commit_id):
        if base_commit_id:
            revision = base_commit_id
        elif repository.tool.name == 'Git':
            raise FileNotFoundError(
                path,
                revision,
                detail='The necessary revision information needed to find '
                       'this file was not provided. Use RBTools 0.5.2 or '
                       'newer.')

        return revision

    def _api_get_repository(self, account_domain, repository_name):
        url = self._build_api_url(account_domain,
                                  'repositories/%s.json' % repository_name)

        return self._api_get(url)

    def _api_get_node(self, repository, path, revision, contents=False):
        if contents:
            contents_str = '1'
        else:
            contents_str = '0'

        url = self._build_api_url(
            self._get_repository_account_domain(repository),
            'repositories/%s/node.json?path=%s&revision=%s&contents=%s'
            % (repository.extra_data['beanstalk_repo_name'],
               quote(path), quote(revision), contents_str))

        return self._api_get(url)

    def _build_api_url(self, account_domain, url):
        return 'https://%s.beanstalkapp.com/api/%s' % (account_domain, url)

    def _get_repository_account_domain(self, repository):
        return repository.extra_data['beanstalk_account_domain']

    def _api_get(self, url):
        try:
            data, headers = self._http_get(
                url,
                username=self.account.username,
                password=decrypt_password(self.account.data['password']))
            return simplejson.loads(data)
        except HTTPError, e:
            data = e.read()

            try:
                rsp = simplejson.loads(data)
            except:
                rsp = None

            if rsp and 'errors' in rsp:
                raise Exception('; '.join(rsp['errors']))
            else:
                raise Exception(str(e))
