from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class GitoriousForm(HostingServiceForm):
    gitorious_project_name = forms.CharField(
        label=_('Project name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    gitorious_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class Gitorious(HostingService):
    name = 'Gitorious'
    form = GitoriousForm
    supported_scmtools = ['Git']
    supports_repositories = True
    repository_fields = {
        'Git': {
            'path': 'git://gitorious.org/%(gitorious_project_name)s/'
                    '%(gitorious_repo_name)s.git',
            'mirror_path': 'https://gitorious.org/'
                           '%(gitorious_project_name)s/'
                           '%(gitorious_repo_name)s.git',
            'raw_file_url': 'https://gitorious.org/'
                            '%(gitorious_project_name)s/'
                            '%(gitorious_repo_name)s/blobs/raw/<revision>'
        },
    }
