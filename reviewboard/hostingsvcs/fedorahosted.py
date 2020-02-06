from __future__ import unicode_literals

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
    """Hosting service support for fedorahosted.org.

    This was a hosting service for Git, Mercurial, and Subversion provided
    by Fedora. This service was retired on March 1st, 2017.

    Deprecated:
        3.0.17:
        This service will no longer appear as an option when configuring a
        repository.
    """

    name = 'Fedora Hosted'
    visible = False

    form = FedoraHostedForm
    supports_repositories = True
    supports_bug_trackers = True
    supported_scmtools = ['Git', 'Mercurial', 'Subversion']
    repository_fields = {
        'Git': {
            'path': 'git://git.fedorahosted.org/git/'
                    '%(fedorahosted_repo_name)s.git',
            'raw_file_url': 'http://git.fedorahosted.org/cgit/'
                            '%(fedorahosted_repo_name)s.git/blob/'
                            '<filename>?id=<revision>'
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
    bug_tracker_field = \
        'https://fedorahosted.org/%(fedorahosted_repo_name)s/ticket/%%s'
