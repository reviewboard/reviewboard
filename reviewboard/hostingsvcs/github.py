import httplib
import logging
import urllib2

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            SSHKeyAssociationError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.site.urlresolvers import local_site_reverse


class GitHubPublicForm(HostingServiceForm):
    github_public_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;username&gt;/&lt;repo_name&gt;/'))


class GitHubPrivateForm(HostingServiceForm):
    github_private_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;username&gt;/&lt;repo_name&gt;/'))


class GitHubPublicOrgForm(HostingServiceForm):
    github_public_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the organization. This is the '
                    '&lt;org_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))

    github_public_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))


class GitHubPrivateOrgForm(HostingServiceForm):
    github_private_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the organization. This is the '
                    '&lt;org_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))

    github_private_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))


class GitHub(HostingService):
    name = _('GitHub')
    plans = [
        ('public', {
            'name': _('Public'),
            'form': GitHubPublicForm,
            'repository_fields': {
                'Git': {
                    'path': 'git://github.com/%(hosting_account_username)s/'
                            '%(github_public_repo_name)s.git',
                    'mirror_path': 'git@github.com:'
                                   '%(hosting_account_username)s/'
                                   '%(github_public_repo_name)s.git',
                }
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(hosting_account_username)s/'
                                 '%(github_public_repo_name)s/'
                                 'issues#issue/%%s',
        }),
        ('public-org', {
            'name': _('Public Organization'),
            'form': GitHubPublicOrgForm,
            'repository_fields': {
                'Git': {
                    'path': 'git://github.com/%(github_public_org_name)s/'
                            '%(github_public_org_repo_name)s.git',
                    'mirror_path': 'git@github.com:%(github_public_org_name)s/'
                                   '%(github_public_org_repo_name)s.git',
                }
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(github_public_org_name)s/'
                                 '%(github_public_org_repo_name)s/'
                                 'issues#issue/%%s',
        }),
        ('private', {
            'name': _('Private'),
            'form': GitHubPrivateForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@github.com:%(hosting_account_username)s/'
                            '%(github_private_repo_name)s.git',
                    'mirror_path': '',
                },
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(hosting_account_username)s/'
                                 '%(github_private_repo_name)s/'
                                 'issues#issue/%%s',
        }),
        ('private-org', {
            'name': _('Private Organization'),
            'form': GitHubPrivateOrgForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@github.com:%(github_private_org_name)s/'
                            '%(github_private_org_repo_name)s.git',
                    'mirror_path': '',
                },
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(github_private_org_name)s/'
                                 '%(github_private_org_repo_name)s/'
                                 'issues#issue/%%s',
        }),
    ]

    needs_authorization = True
    supports_bug_trackers = True
    supports_post_commit = True
    supports_repositories = True
    supports_ssh_key_association = True
    supported_scmtools = ['Git']

    # This should be the prefix for every field on the plan forms.
    plan_field_prefix = 'github'

    RAW_MIMETYPE = 'application/vnd.github.v3.raw'

    def get_api_url(self, hosting_url):
        """Returns the API URL for GitHub.

        This can be overridden to provide more advanced lookup (intended
        for the GitHub Enterprise support).
        """
        assert not hosting_url
        return 'https://api.github.com/'

    def get_plan_field(self, plan, plan_data, name):
        """Returns the value of a field for plan-specific data.

        This takes into account the plan type and hosting service ID.
        """
        key = '%s_%s_%s' % (self.plan_field_prefix, plan.replace('-', '_'),
                            name)
        return plan_data[key]

    def authorize(self, username, password, hosting_url,
                  local_site_name=None, *args, **kwargs):
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        site_url = '%s://%s%s' % (
            siteconfig.get('site_domain_method'),
            site.domain,
            local_site_reverse('root', local_site_name=local_site_name))

        try:
            body = {
                'scopes': [
                    'user',
                    'repo',
                ],
                'note': 'Access for Review Board',
                'note_url': site_url,
            }

            # If the site is using a registered GitHub application,
            # send it in the requests. This will gain the benefits of
            # a GitHub application, such as higher rate limits.
            if (hasattr(settings, 'GITHUB_CLIENT_ID') and
                hasattr(settings, 'GITHUB_CLIENT_SECRET')):
                body.update({
                    'client_id': settings.GITHUB_CLIENT_ID,
                    'client_secret': settings.GITHUB_CLIENT_SECRET,
                })

            rsp, headers = self._json_post(
                url=self.get_api_url(hosting_url) + 'authorizations',
                username=username,
                password=password,
                body=simplejson.dumps(body))
        except (urllib2.HTTPError, urllib2.URLError), e:
            data = e.read()

            try:
                rsp = simplejson.loads(data)
            except:
                rsp = None

            if rsp and 'message' in rsp:
                raise AuthorizationError(rsp['message'])
            else:
                raise AuthorizationError(str(e))

        self.account.data['authorization'] = rsp
        self.account.save()

    def is_authorized(self):
        return ('authorization' in self.account.data and
                'token' in self.account.data['authorization'])

    def get_file(self, repository, path, revision, *args, **kwargs):
        url = self._build_api_url(repository, 'git/blobs/%s' % revision)

        try:
            return self._http_get(url, headers={
                'Accept': self.RAW_MIMETYPE,
            })[0]
        except (urllib2.URLError, urllib2.HTTPError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        url = self._build_api_url(repository, 'git/blobs/%s' % revision)

        try:
            self._http_get(url, headers={
                'Accept': self.RAW_MIMETYPE,
            })

            return True
        except (urllib2.URLError, urllib2.HTTPError):
            return False

    def get_branches(self, repository):
        results = []

        url = self._build_api_url(repository, 'git/refs/heads')
        try:
            rsp = self._api_get(url)
        except Exception, e:
            logging.warning('Failed to fetch commits from %s: %s',
                            url, e)
            return results

        for ref in rsp:
            refname = ref['ref']

            if not refname.startswith('refs/heads/'):
                continue

            name = refname.split('/')[-1]
            results.append(Branch(name, ref['object']['sha'],
                                  default=(name == 'master')))

        return results

    def get_commits(self, repository, start=None):
        results = []

        resource = 'commits'
        url = self._build_api_url(repository, resource)
        if start:
            url += '&sha=%s' % start

        try:
            rsp = self._api_get(url)
        except Exception, e:
            logging.warning('Failed to fetch commits from %s: %s',
                            url, e)
            return results

        for item in rsp:
            commit = Commit(
                item['commit']['author']['name'],
                item['sha'],
                item['commit']['committer']['date'],
                item['commit']['message'])
            if item['parents']:
                commit.parent = item['parents'][0]['sha']

            results.append(commit)

        return results

    def get_change(self, repository, revision):
        # Step 1: fetch the commit itself that we want to review, to get
        # the parent SHA and the commit message. Hopefully this information
        # is still in cache so we don't have to fetch it again.
        commit = cache.get(repository.get_commit_cache_key(revision))
        if commit:
            author_name = commit.author_name
            date = commit.date
            parent_revision = commit.parent
            message = commit.message
        else:
            url = self._build_api_url(repository, 'commits')
            url += '&sha=%s' % revision

            commit = self._api_get(url)[0]

            author_name = commit['commit']['author']['name']
            date = commit['commit']['committer']['date'],
            parent_revision = commit['parents'][0]['sha']
            message = commit['commit']['message']

        # Step 2: fetch the "compare two commits" API to get the diff.
        url = self._build_api_url(
            repository, 'compare/%s...%s' % (parent_revision, revision))
        comparison = self._api_get(url)

        tree_sha = comparison['base_commit']['commit']['tree']['sha']
        files = comparison['files']

        # Step 3: fetch the tree for the original commit, so that we can get
        # full blob SHAs for each of the files in the diff.
        url = self._build_api_url(repository, 'git/trees/%s' % tree_sha)
        url += '&recursive=1'
        tree = self._api_get(url)

        file_shas = {}
        for file in tree['tree']:
            file_shas[file['path']] = file['sha']

        diff = []

        for file in files:
            filename = file['filename']
            status = file['status']
            patch = file['patch']

            diff.append('diff --git a/%s b/%s' % (filename, filename))

            if status == 'modified':
                old_sha = file_shas[filename]
                new_sha = file['sha']
                diff.append('index %s..%s 100644' % (old_sha, new_sha))
                diff.append('--- a/%s' % filename)
                diff.append('+++ b/%s' % filename)
            elif status == 'added':
                new_sha = file['sha']

                diff.append('new file mode 100644')
                diff.append('index %s..%s' % ('0' * 40, new_sha))
                diff.append('--- /dev/null')
                diff.append('+++ b/%s' % filename)
            elif status == 'removed':
                old_sha = file_shas[filename]

                diff.append('deleted file mode 100644')
                diff.append('index %s..%s' % (old_sha, '0' * 40))
                diff.append('--- a/%s' % filename)
                diff.append('+++ /dev/null')

            diff.append(patch)

        diff = '\n'.join(diff)

        # Make sure there's a trailing newline
        if not diff.endswith('\n'):
            diff += '\n'

        commit = Commit(author_name, revision, date, message, parent_revision)
        commit.diff = diff
        return commit

    def is_ssh_key_associated(self, repository, key):
        if not key:
            return False

        formatted_key = self._format_public_key(key)

        # The key might be a deploy key (associated with a repository) or a
        # user key (associated with the currently authorized user account),
        # so check both.
        deploy_keys_url = self._build_api_url(repository, 'keys')
        api_url = self.get_api_url(self.account.hosting_url)
        user_keys_url = ('%suser/keys?access_token=%s'
                         % (api_url,
                            self.account.data['authorization']['token']))

        for url in (deploy_keys_url, user_keys_url):
            keys_resp = self._key_association_api_call(self._json_get, url)

            keys = [
                item['key']
                for item in keys_resp
                if 'key' in item
            ]

            if formatted_key in keys:
                return True

        return False

    def associate_ssh_key(self, repository, key, *args, **kwargs):
        url = self._build_api_url(repository, 'keys')

        if key:
            post_data = {
                'key': self._format_public_key(key),
                'title': 'Review Board (%s)' %
                         Site.objects.get_current().domain,
            }

            self._key_association_api_call(self._http_post, url,
                                           content_type='application/json',
                                           body=simplejson.dumps(post_data))

    def _key_association_api_call(self, instance_method, *args,
                                  **kwargs):
        """Returns response of API call, or raises SSHKeyAssociationError.

        The `instance_method` should be one of the HostingService http methods
        (e.g. _http_post, _http_get, etc.)
        """
        try:
            response, headers = instance_method(*args, **kwargs)
            return response
        except (urllib2.HTTPError, urllib2.URLError), e:
            try:
                rsp = simplejson.loads(e.read())
                status_code = e.code
            except:
                rsp = None
                status_code = None

            if rsp and status_code:
                api_msg = self._get_api_error_message(rsp, status_code)
                raise SSHKeyAssociationError('%s (%s)' % (api_msg, e))
            else:
                raise SSHKeyAssociationError(str(e))

    def _format_public_key(self, key):
        """Return the server's SSH public key as a string (if it exists)

        The key is formatted for POSTing to GitHub's API.
        """
        # Key must be prepended with algorithm name
        return '%s %s' % (key.get_name(), key.get_base64())

    def _get_api_error_message(self, rsp, status_code):
        """Return the error(s) reported by the GitHub API, as a string

        See: http://developer.github.com/v3/#client-errors
        """
        if 'message' not in rsp:
            msg = _('Unknown GitHub API Error')
        elif 'errors' in rsp and status_code == httplib.UNPROCESSABLE_ENTITY:
            errors = [e['message'] for e in rsp['errors'] if 'message' in e]
            msg = '%s: (%s)' % (rsp['message'], ', '.join(errors))
        else:
            msg = rsp['message']

        return msg

    def _http_get(self, url, *args, **kwargs):
        data, headers = super(GitHub, self)._http_get(url, *args, **kwargs)
        self._check_rate_limits(headers)
        return data, headers

    def _http_post(self, url, *args, **kwargs):
        data, headers = super(GitHub, self)._http_post(url, *args, **kwargs)
        self._check_rate_limits(headers)
        return data, headers

    def _check_rate_limits(self, headers):
        rate_limit_remaining = headers.get('X-RateLimit-Remaining', None)

        try:
            if (rate_limit_remaining is not None and
                int(rate_limit_remaining) <= 100):
                logging.warning('GitHub rate limit for %s is down to %s',
                                self.account.username, rate_limit_remaining)
        except ValueError:
            pass

    def _build_api_url(self, repository, api_path):
        return '%s%s?access_token=%s' % (
            self._get_repo_api_url(repository),
            api_path,
            self.account.data['authorization']['token'])

    def _get_repo_api_url(self, repository):
        plan = repository.extra_data['repository_plan']

        if plan in ('public', 'private'):
            owner = self.account.username
        elif plan in ('public-org', 'private-org'):
            owner = self.get_plan_field(plan, repository.extra_data, 'name')
        else:
            raise KeyError('%s is not a valid plan for this hosting service'
                           % plan)

        return '%srepos/%s/%s/' % (
            self.get_api_url(self.account.hosting_url),
            owner,
            self.get_plan_field(plan, repository.extra_data, 'repo_name'))

    def _api_get(self, url):
        try:
            data, headers = self._http_get(url)
            return simplejson.loads(data)
        except (urllib2.URLError, urllib2.HTTPError), e:
            data = e.read()

            try:
                rsp = simplejson.loads(data)
            except:
                rsp = None

            if rsp and 'message' in rsp:
                raise Exception(rsp['message'])
            else:
                raise Exception(str(e))
