from __future__ import unicode_literals

import json
import logging
import os
from collections import defaultdict

from django import forms
from django.conf.urls import patterns, url
from django.http import HttpResponse
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import quote
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from reviewboard.admin.server import get_server_url
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_review_request_id)
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

    repository_url_patterns = patterns(
        '',
        url(r'^hooks/post-receive/$',
            'reviewboard.hostingsvcs.beanstalk.process_post_receive_hook'),
    )

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


@require_POST
def process_post_receive_hook(request, *args, **kwargs):
    """Closes review requests as submitted automatically after a push."""
    try:
        server_url = get_server_url(request=request)

        # Check if it's a git or an SVN repository and close accordingly.
        if 'payload' in request.POST:
            payload = json.loads(request.POST['payload'])
            close_git_review_requests(payload, server_url)
        else:
            payload = json.loads(request.POST['commit'])
            close_svn_review_request(payload, server_url)

    except KeyError as e:
        logging.error('There is no JSON payload in the POST request.: %s', e)
        return HttpResponse(status=415)

    except ValueError as e:
        logging.error('The payload is not in JSON format: %s', e)
        return HttpResponse(status=415)

    return HttpResponse()


def close_git_review_requests(payload, server_url):
    """Closes all review requests for the git repository.

    A git payload may contain multiple commits. If a commit's commit
    message does not contain a review request ID, it closes based on
    it's commit id.
    """
    review_id_to_commits_map = defaultdict(list)
    branch_name = payload.get('branch')

    if not branch_name:
        return review_id_to_commits_map

    commits = payload.get('commits', [])

    for commit in commits:
        commit_hash = commit.get('id')
        commit_message = commit.get('message')
        review_request_id = get_review_request_id(commit_message, server_url,
                                                  commit_hash)
        commit_entry = '%s (%s)' % (branch_name, commit_hash[:7])
        review_id_to_commits_map[review_request_id].append(commit_entry)

    close_all_review_requests(review_id_to_commits_map)


def close_svn_review_request(payload, server_url):
    """Closes the review request for an SVN repository.

    The SVN payload may contains one commit. If a commit's commit
    message does not contain a review request ID, it does not close
    any review request.
    """
    review_id_to_commits_map = defaultdict(list)
    commit_message = payload.get('message')
    branch_name = payload.get('changeset_url', 'SVN Repository')
    revision = '%s %d' % ('Revision: ', payload.get('revision'))
    review_request_id = get_review_request_id(commit_message, server_url,
                                              None)
    commit_entry = '%s (%s)' % (branch_name, revision)
    review_id_to_commits_map[review_request_id].append(commit_entry)
    close_all_review_requests(review_id_to_commits_map)
