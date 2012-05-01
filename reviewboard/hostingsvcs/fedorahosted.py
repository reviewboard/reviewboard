from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class FedoraHostedForm(HostingServiceForm):
    fedorahosted_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class FedoraHosted(HostingService):
    name = 'Fedora Hosted'
    repository_form = FedoraHostedForm
    supported_scmtools = ['Git', 'Mercurial', 'Subversion']
    repository_fields = {
        'Git': {
            'path': 'git://git.fedorahosted.org/git/'
                    '%(fedorahosted_repo_name)s.git',
            'mirror_path': 'git://git.fedorahosted.org/git/'
                            '%(fedorahosted_repo_name)s.git',
            'raw_file_url': 'http://git.fedorahosted.org/git/?p='
                            '%(fedorahosted_repo_name)s.git;'
                            'a=blob_plain;'
                            'f=<filename>;h=<revision>'
        },
        'Mercurial': {
            'path': 'http://hg.fedorahosted.org/hg/'
                    '%(fedorahosted_repo_name)s/',
            'mirror_path': 'https://hg.fedorahosted.org/hg/'
                           '%(fedorahosted_repo_name)s/'
        },
        'Subversion': {
            'path': 'http://svn.fedorahosted.org/svn/'
                    '%(fedorahosted_repo_name)s/',
            'mirror_path': 'https://svn.fedorahosted.org/svn/'
                           '%(fedorahosted_repo_name)s/',
        },
    }
