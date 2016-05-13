from __future__ import unicode_literals

from django import forms

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class TestServiceForm(HostingServiceForm):
    test_repo_name = forms.CharField(
        label='Repository name',
        max_length=64,
        required=True)


class TestService(HostingService):
    name = 'Test Service'
    form = TestServiceForm
    needs_authorization = True
    supports_repositories = True
    supports_bug_trackers = True
    supports_two_factor_auth = True
    has_repository_hook_instructions = True
    supported_scmtools = ['Git']
    bug_tracker_field = ('http://example.com/%(hosting_account_username)s/'
                         '%(test_repo_name)s/issue/%%s')
    repository_fields = {
        'Git': {
            'path': 'http://example.com/%(test_repo_name)s/',
        },
    }

    def authorize(self, username, password, hosting_url, local_site_name=None,
                  two_factor_auth_code=None, *args, **kwargs):
        if username == 'baduser':
            raise AuthorizationError('The username is very very bad.')
        elif username == '2fa-user' and two_factor_auth_code != '123456':
            raise TwoFactorAuthCodeRequiredError('Enter your 2FA code.')

        self.account.data.update({
            'username': username,
            'password': password,
            'hosting_url': hosting_url,
            'local_site_name': local_site_name,
        })

    def is_authorized(self):
        return (self.account.username != 'baduser' and
                'password' in self.account.data)

    def check_repository(self, *args, **kwargs):
        pass


class SelfHostedTestService(TestService):
    name = 'Self-Hosted Test'
    self_hosted = True
    bug_tracker_field = '%(hosting_url)s/%(test_repo_name)s/issue/%%s'
    repository_fields = {
        'Git': {
            'path': '%(hosting_url)s/%(test_repo_name)s/',
            'mirror_path': 'git@%(hosting_domain)s:%(test_repo_name)s/',
        },
    }
