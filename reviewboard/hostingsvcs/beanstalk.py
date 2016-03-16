from __future__ import unicode_literals

import json
import os

from django import forms
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import quote
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
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
                    '.beanstalkapp.com:/%(beanstalk_account_domain)s/'
                    '%(beanstalk_repo_name)s.git',
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

    def get_password(self):
        """Returns the password for this account.

        This is needed for API calls and for Subversion.
        """
        return decrypt_password(self.account.data['password'])

    def get_file(self, repository, path, revision, base_commit_id=None,
                 *args, **kwargs):
        """Fetches a file from Beanstalk.

        This will perform an API request to fetch the contents of a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        try:
            return self._api_get_node(repository, path, revision,
                                      base_commit_id, contents=True)
        except (HTTPError, URLError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, base_commit_id=None,
                        *args, **kwargs):
        """Determines if a file exists.

        This will perform an API request to fetch the metadata for a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        try:
            self._api_get_node(repository, path, revision, base_commit_id)

            return True
        except (HTTPError, URLError, FileNotFoundError):
            return False

    def _api_get_repository(self, account_domain, repository_name):
        url = self._build_api_url(account_domain,
                                  'repositories/%s.json' % repository_name)

        return self._api_get(url)

    def _api_get_node(self, repository, path, revision, base_commit_id,
                      contents=False):
        # Unless we're fetching raw content, we optimistically want to
        # grab the metadata for the file. That's going to be a lot smaller
        # than the file contents in most cases. However, we can only do that
        # with a base_commit_id. If we don't have that, we fall back on
        # fetching the full file contents.
        is_git = (repository.tool.name == 'Git')

        if is_git and (contents or not base_commit_id):
            url_path = ('blob?id=%s&name=%s'
                        % (quote(revision), quote(os.path.basename(path))))
            raw_content = True
        else:
            if is_git:
                expected_revision = base_commit_id
            else:
                expected_revision = revision

            url_path = ('node.json?path=%s&revision=%s'
                        % (quote(path), quote(expected_revision)))

            if contents:
                url_path += '&contents=true'

            raw_content = False

        url = self._build_api_url(
            self._get_repository_account_domain(repository),
            'repositories/%s/%s'
            % (repository.extra_data['beanstalk_repo_name'], url_path))

        result = self._api_get(url, raw_content=raw_content)

        if not raw_content and contents:
            result = result['contents']

        return result

    def _build_api_url(self, account_domain, url):
        return 'https://%s.beanstalkapp.com/api/%s' % (account_domain, url)

    def _get_repository_account_domain(self, repository):
        return repository.extra_data['beanstalk_account_domain']

    def _api_get(self, url, raw_content=False):
        try:
            data, headers = self.client.http_get(
                url,
                username=self.account.username,
                password=self.get_password())

            if raw_content:
                return data
            else:
                return json.loads(data)
        except HTTPError as e:
            data = e.read()

            try:
                rsp = json.loads(data)
            except:
                rsp = None

            if rsp and 'errors' in rsp:
                raise Exception('; '.join(rsp['errors']))
            else:
                raise Exception(six.text_type(e))
