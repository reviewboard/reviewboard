from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class CodebaseHQForm(HostingServiceForm):
    codebasehq_project_name = forms.CharField(
        label=_('Project name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    codebasehq_group_name = forms.CharField(
        label=_('Codebase HQ domain name'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The subdomain used to access your Codebase account'))

    codebasehq_repo_name = forms.CharField(
        label=_('Repository short name'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The short name of your repository. This can be found in '
                    'the "Repository Admin/Properties" page'))

    codebasehq_api_username = forms.CharField(
        label=_('API username'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_(
            'Your Codebase API Username. You can find this in the '
            'API Credentials section of the "My Profile" page at '
            'http://&lt;groupname&gt;.codebasehq.com/settings/profile/'))

    codebasehq_api_key = forms.CharField(
        label=_('API key'),
        max_length=40,
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))


class CodebaseHQ(HostingService):
    name = 'Codebase HQ'
    form = CodebaseHQForm
    supports_repositories = True
    supported_scmtools = ['Git']
    repository_fields = {
        'Git': {
            'username': '%(codebasehq_api_username)s',
            'password': '%(codebasehq_api_key)s',
            'path': 'git@codebasehq.com:%(codebasehq_group_name)s/'
                    '%(codebasehq_project_name)s/'
                    '%(codebasehq_repo_name)s.git',
            'raw_file_url': 'https://api3.codebasehq.com/'
                            '%(codebasehq_project_name)s/'
                            '%(codebasehq_repo_name)s/blob/'
                            '<revision>',
        },

        #
        # NOTE: Subversion doesn't work because it requires a
        #       standard username and password, not an API Username/token.
        #       We don't have a way of requesting that data just for this
        #       type.
        #
        #'Subversion': {
        #    'path': 'https://%(username)s@%(codebasehq_group_name)s/'
        #            '%(codebasehq_project_name)s/'
        #            '%(codebasehq_repo_name)s.svn',
        #},

        # NOTE: Mercurial doesn't work because they don't use HTTP Basic
        #       Auth for the authentication. A valid browser session cookie
        #       is needed instead.
        #
        #'Mercurial': {
        #    'username': '%(codebasehq_api_username)s',
        #    'password': '%(codebasehq_api_key)s',
        #    'path': 'https://%(codebasehq_group_name)s.codebasehq.com/'
        #            'projects/%(codebasehq_project_name)s/repositories/'
        #            '%(codebasehq_repo_name)s/'
        #},

        # TODO: Support Bazaar
    }
