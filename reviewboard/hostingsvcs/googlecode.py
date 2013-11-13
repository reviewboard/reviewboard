from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class GoogleCodeForm(HostingServiceForm):
    googlecode_project_name = forms.CharField(
        label=_('Project name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GoogleCode(HostingService):
    name = 'Google Code'
    form = GoogleCodeForm
    supported_scmtools = ['Mercurial', 'Subversion']
    supports_repositories = True
    supports_bug_trackers = True
    repository_fields = {
        'Mercurial': {
            'path': 'http://%(googlecode_project_name)s'
                    '.googlecode.com/hg',
            'mirror_path': 'https://%(googlecode_project_name)s'
                           '.googlecode.com/hg',
        },
        'Subversion': {
            'path': 'http://%(googlecode_project_name)s'
                    '.googlecode.com/svn',
            'mirror_path': 'https://%(googlecode_project_name)s'
                           '.googlecode.com/svn',
        },
    }
    bug_tracker_field = 'http://code.google.com/p/' \
                        '%(googlecode_project_name)s/' \
                        'issues/detail?id=%%s'
