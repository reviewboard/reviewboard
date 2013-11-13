from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class SourceForgeForm(HostingServiceForm):
    sourceforge_project_name = forms.CharField(
        label=_('Project name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class SourceForge(HostingService):
    name = 'SourceForge'
    form = SourceForgeForm
    supports_repositories = True
    supports_bug_trackers = True
    supported_scmtools = ['Bazaar', 'CVS', 'Mercurial', 'Subversion']
    repository_fields = {
        'Bazaar': {
            'path': 'bzr://%(sourceforge_project_name)s'
                    '.bzr.sourceforge.net/bzrroot/'
                    '%(sourceforge_project_name)s',
            'mirror_path': 'bzr+ssh://%(sourceforge_project_name)s'
                           '.bzr.sourceforge.net/bzrroot/'
                           '%(sourceforge_project_name)s',
        },
        'CVS': {
            'path': ':pserver:anonymous@%(sourceforge_project_name)s'
                    '.cvs.sourceforge.net:/cvsroot/'
                    '%(sourceforge_project_name)s',
            'mirror_path': '%(sourceforge_project_name)s'
                           '.cvs.sourceforge.net/cvsroot/'
                           '%(sourceforge_project_name)s',
        },
        'Mercurial': {
            'path': 'http://%(sourceforge_project_name)s'
                    '.hg.sourceforge.net:8000/hgroot/'
                    '%(sourceforge_project_name)s',
            'mirror_path': 'ssh://%(sourceforge_project_name)s'
                           '.hg.sourceforge.net/hgroot/'
                           '%(sourceforge_project_name)s',
        },
        'Subversion': {
            'path': 'http://%(sourceforge_project_name)s'
                    '.svn.sourceforge.net/svnroot/'
                    '%(sourceforge_project_name)s',
            'mirror_path': 'https://%(sourceforge_project_name)s'
                           '.svn.sourceforge.net/svnroot/'
                           '%(sourceforge_project_name)s',
        },
        # TODO: Support Git
    }
    bug_tracker_field = 'http://sourceforge.net/support/tracker.php?aid=%%s'
