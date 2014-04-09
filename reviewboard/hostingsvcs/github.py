import httplib
import logging
import urllib2
import uuid

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            InvalidPlanError,
                                            RepositoryError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
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
                                 '%(github_public_repo_name)s/issues#issue/%%s',
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
    supports_repositories = True
    supports_bug_trackers = True
    supports_two_factor_auth = True
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

    def check_repository(self, plan=None, *args, **kwargs):
        """Checks the validity of a repository.

        This will perform an API request against GitHub to get
        information on the repository. This will throw an exception if
        the repository was not found, and return cleanly if it was found.
        """
        try:
            repo_info = self._api_get_repository(
                self._get_repository_owner_raw(plan, kwargs),
                self._get_repository_name_raw(plan, kwargs))
        except Exception, e:
            if str(e) == 'Not Found':
                if plan in ('public', 'private'):
                    raise RepositoryError(
                        _('A repository with this name was not found, or your '
                          'user may not own it.'))
                elif plan == 'public-org':
                    raise RepositoryError(
                        _('A repository with this organization or name was not '
                          'found.'))
                elif plan == 'private-org':
                    raise RepositoryError(
                        _('A repository with this organization or name was '
                          'not found, or your user may not have access to '
                          'it.'))

            raise

        if 'private' in repo_info:
            is_private = repo_info['private']

            if is_private and plan in ('public', 'public-org'):
                raise RepositoryError(
                    _('This is a private repository, but you have selected '
                      'a public plan.'))
            elif not is_private and plan in ('private', 'private-org'):
                raise RepositoryError(
                    _('This is a public repository, but you have selected '
                      'a private plan.'))

    def authorize(self, username, password, hosting_url,
                  two_factor_auth_code=None, local_site_name=None,
                  *args, **kwargs):
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        site_base_url = '%s%s' % (
            site.domain,
            local_site_reverse('root', local_site_name=local_site_name))

        site_url = '%s://%s' % (siteconfig.get('site_domain_method'),
                                site_base_url)

        note = 'Access for Review Board (%s - %s)' % (
            site_base_url,
            uuid.uuid4().hex[:7])

        try:
            body = {
                'scopes': [
                    'user',
                    'repo',
                ],
                'note': note,
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

            headers = {}

            if two_factor_auth_code:
                headers['X-GitHub-OTP'] = two_factor_auth_code

            rsp, headers = self._json_post(
                url=self.get_api_url(hosting_url) + 'authorizations',
                username=username,
                password=password,
                headers=headers,
                body=simplejson.dumps(body))
        except (urllib2.HTTPError, urllib2.URLError), e:
            data = e.read()

            try:
                rsp = simplejson.loads(data)
            except:
                rsp = None

            if rsp and 'message' in rsp:
                response_info = e.info()
                x_github_otp = response_info.get('X-GitHub-OTP', '')

                if x_github_otp.startswith('required;'):
                    raise TwoFactorAuthCodeRequiredError(
                        _('Enter your two-factor authentication code '
                          'and re-enter your password to link your account. '
                          'This code will be sent to you by GitHub.'))

                raise AuthorizationError(rsp['message'])
            else:
                raise AuthorizationError(str(e))

        self._save_auth_data(rsp)

    def is_authorized(self):
        return ('authorization' in self.account.data and
                'token' in self.account.data['authorization'])

    def get_reset_auth_token_requires_password(self):
        """Returns whether or not resetting the auth token requires a password.

        A password will be required if not using a GitHub client ID or
        secret.
        """
        if not self.is_authorized():
            return True

        app_info = self.account.data['authorization']['app']
        client_id = app_info.get('client_id', '')
        has_client = (client_id.strip('0') != '')

        return (not has_client or
                (not (hasattr(settings, 'GITHUB_CLIENT_ID') and
                      hasattr(settings, 'GITHUB_CLIENT_SECRET'))))

    def reset_auth_token(self, password=None, two_factor_auth_code=None):
        """Resets the authorization token for the linked account.

        This will attempt to reset the token in a few different ways,
        depending on how the token was granted.

        Tokens linked to a registered GitHub OAuth app can be reset without
        requiring any additional credentials.

        Tokens linked to a personal account (which is the case on most
        installations) require a password and possibly a two-factor auth
        code. Callers should call get_reset_auth_token_requires_password()
        before determining whether to pass a password, and should pass
        a two-factor auth code if this raises TwoFactorAuthCodeRequiredError.
        """
        if self.is_authorized():
            token = self.account.data['authorization']['token']
        else:
            token = None

        if self.get_reset_auth_token_requires_password():
            assert password

            if self.account.local_site:
                local_site_name = self.account.local_site.name
            else:
                local_site_name = None

            if token:
                try:
                    self._delete_auth_token(
                        self.account.data['authorization']['id'],
                        password=password,
                        two_factor_auth_code=two_factor_auth_code)
                except HostingServiceError, e:
                    # If we get a Not Found, then the authorization was
                    # probably already deleted.
                    if str(e) != 'Not Found':
                        raise

                self.account.data['authorization'] = ''
                self.account.save()

            # This may produce errors, which we want to bubble up.
            self.authorize(self.account.username, password,
                           self.account.hosting_url,
                           two_factor_auth_code=two_factor_auth_code,
                           local_site_name=local_site_name)
        else:
            # We can use the new API for resetting the token without
            # re-authenticating.
            auth_data = self._reset_authorization(
                settings.GITHUB_CLIENT_ID,
                settings.GITHUB_CLIENT_SECRET,
                token)
            self._save_auth_data(auth_data)

    def get_file(self, repository, path, revision, *args, **kwargs):
        url = self._build_api_url(self._get_repo_api_url(repository),
                                  'git/blobs/%s' % revision)

        try:
            return self._http_get(url, headers={
                'Accept': self.RAW_MIMETYPE,
            })[0]
        except (urllib2.URLError, urllib2.HTTPError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        url = self._build_api_url(self._get_repo_api_url(repository),
                                  'git/blobs/%s' % revision)

        try:
            self._http_get(url, headers={
                'Accept': self.RAW_MIMETYPE,
            })

            return True
        except (urllib2.URLError, urllib2.HTTPError):
            return False

    def _reset_authorization(self, client_id, client_secret, token):
        """Resets the authorization info for an OAuth app-linked token.

        If the token is associated with a registered OAuth application,
        its token will be reset, without any authentication details required.
        """
        url = '%sapplications/%s/tokens/%s' % (
            self.get_api_url(self.account.hosting_url),
            client_id,
            token)

        # Allow any errors to bubble up
        return self._api_post(url=url,
                              username=client_id,
                              password=client_secret)

    def _delete_auth_token(self, auth_id, password, two_factor_auth_code=None):
        """Requests that an authorization token be deleted.

        This will delete the authorization token with the given ID. It
        requires a password and, depending on the settings, a two-factor
        authentication code to perform the deletion.
        """
        headers = {}

        if two_factor_auth_code:
            headers['X-GitHub-OTP'] = two_factor_auth_code

        url = self._build_api_url(
            '%sauthorizations/%s' % (
                self.get_api_url(self.account.hosting_url),
                auth_id))

        self._api_delete(url=url,
                         headers=headers,
                         username=self.account.username,
                         password=password)

    def _save_auth_data(self, auth_data):
        """Saves authorization data sent from GitHub."""
        self.account.data['authorization'] = auth_data
        self.account.save()

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

    def _build_api_url(self, *api_paths):
        return '%s?access_token=%s' % (
            '/'.join(api_paths),
            self.account.data['authorization']['token'])

    def _get_repo_api_url(self, repository):
        plan = repository.extra_data['repository_plan']

        return self._get_repo_api_url_raw(
            self._get_repository_owner_raw(plan, repository.extra_data),
            self._get_repository_name_raw(plan, repository.extra_data))

    def _get_repo_api_url_raw(self, owner, repo_name):
        return '%srepos/%s/%s' % (self.get_api_url(self.account.hosting_url),
                                   owner, repo_name)

    def _get_repository_owner_raw(self, plan, extra_data):
        if plan in ('public', 'private'):
            return self.account.username
        elif plan in ('public-org', 'private-org'):
            return self.get_plan_field(plan, extra_data, 'name')
        else:
            raise InvalidPlanError(plan)

    def _get_repository_name_raw(self, plan, extra_data):
        return self.get_plan_field(plan, extra_data, 'repo_name')

    def _api_get_repository(self, owner, repo_name):
        return self._api_get(self._build_api_url(
            self._get_repo_api_url_raw(owner, repo_name)))

    def _api_get(self, url, *args, **kwargs):
        try:
            data, headers = self._json_get(url, *args, **kwargs)
            return data
        except (urllib2.URLError, urllib2.HTTPError), e:
            self._check_api_error(e)

    def _api_post(self, url, *args, **kwargs):
        try:
            data, headers = self._json_post(url, *args, **kwargs)
            return data
        except (urllib2.URLError, urllib2.HTTPError), e:
            self._check_api_error(e)

    def _api_delete(self, url, *args, **kwargs):
        try:
            data, headers = self._json_delete(url, *args, **kwargs)
            return data
        except (urllib2.URLError, urllib2.HTTPError), e:
            self._check_api_error(e)

    def _check_api_error(self, e):
        data = e.read()

        try:
            rsp = simplejson.loads(data)
        except:
            rsp = None

        if rsp and 'message' in rsp:
            response_info = e.info()
            x_github_otp = response_info.get('X-GitHub-OTP', '')

            if x_github_otp.startswith('required;'):
                raise TwoFactorAuthCodeRequiredError(
                    _('Enter your two-factor authentication code. '
                      'This code will be sent to you by GitHub.'))

            if e.code == 401:
                raise AuthorizationError(rsp['message'])

            raise HostingServiceError(rsp['message'])
        else:
            raise HostingServiceError(str(e))
