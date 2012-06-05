from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class BitbucketForm(HostingServiceForm):
    bitbucket_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class Bitbucket(HostingService):
    name = 'Bitbucket'
    form = BitbucketForm
    supports_repositories = True
    supports_bug_trackers = True
    supported_scmtools = ['Mercurial']
    repository_fields = {
        'Mercurial': {
            'path': 'http://bitbucket.org/%(hosting_account_username)s/'
                    '%(bitbucket_repo_name)s/',
            'mirror_path': 'ssh://hg@bitbucket.org/'
                           '%(hosting_account_username)s/'
                           '%(bitbucket_repo_name)s/'
        },
    }
    bug_tracker_field = 'http://bitbucket.org/%(hosting_account_username)s/' \
                        '%(bitbucket_repo_name)s/issue/%%s/'
