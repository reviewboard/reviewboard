import imp
import re
import sys

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _
from djblets.util.filesystem import is_exe_in_path

from reviewboard.scmtools import sshutils
from reviewboard.scmtools.errors import AuthenticationError, \
                                        BadHostKeyError, \
                                        UnknownHostKeyError, \
                                        UnverifiedCertificateError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.validation import validate_review_groups, validate_users


class RepositoryForm(forms.ModelForm):
    """
    A specialized form for RepositoryAdmin that makes the "password"
    field use a PasswordInput widget.
    """

    # NOTE: The list of fields must match that of the corresponding
    #       bug tracker (not including the hosting_ and bug_tracker_
    #       prefixes), for hosting services matching bug trackers.
    HOSTING_SERVICE_INFO = SortedDict([
        ('bitbucket', {
            'label': _('Bitbucket'),
            'fields': ['hosting_project_name', 'hosting_owner'],
            'tools': {
                'Mercurial': {
                    'path': 'http://bitbucket.org/%(hosting_owner)s/'
                            '%(hosting_project_name)s/',
                    'mirror_path': 'ssh://hg@bitbucket.org/'
                                   '%(hosting_owner)s/'
                                   '%(hosting_project_name)s/'
                },
            },
        }),
        ('fedorahosted', {
            'label': _('Fedora Hosted'),
            'fields': ['hosting_project_name'],
            'hidden_fields': ['raw_file_url', 'username', 'password'],
            'tools': {
                'Git': {
                    'path': 'git://git.fedorahosted.org/git/'
                            '%(hosting_project_name)s.git',
                    'mirror_path': 'git://git.fedorahosted.org/git/'
                                    '%(hosting_project_name)s.git',
                    'raw_file_url': 'http://git.fedorahosted.org/git/?p='
                                    '%(hosting_project_name)s.git;'
                                    'a=blob_plain;'
                                    'f=<filename>;h=<revision>'
                },
                'Mercurial': {
                    'path': 'http://hg.fedorahosted.org/hg/'
                            '%(hosting_project_name)s/',
                    'mirror_path': 'https://hg.fedorahosted.org/hg/'
                                   '%(hosting_project_name)s/'
                },
                'Subversion': {
                    'path': 'http://svn.fedorahosted.org/svn/'
                            '%(hosting_project_name)s/',
                    'mirror_path': 'https://svn.fedorahosted.org/svn/'
                                   '%(hosting_project_name)s/',
                },
            },
        }),
        ('github', {
            'label': _('GitHub'),
            'fields': ['hosting_project_name', 'hosting_owner'],
            'hidden_fields': ['raw_file_url','username', 'password'],
            'tools': {
                'Git': {
                    'path': 'git://github.com/%(hosting_owner)s/'
                            '%(hosting_project_name)s.git',
                    'mirror_path': 'git@github.com:%(hosting_owner)s/'
                                   '%(hosting_project_name)s.git',
                    'raw_file_url': 'http://github.com/api/v2/yaml/blob/show/'
                                    '%(hosting_owner)s/'
                                    '%(hosting_project_name)s/'
                                    '<revision>'
                },
            },
        }),
        ('github-private', {
            'label': _('GitHub (Private)'),
            'fields': ['hosting_project_name', 'hosting_owner', 'github_api_token'],
            'hidden_fields': ['raw_file_url', 'username', 'password'],
            'tools': {
                'Git': {
                    'path': 'git@github.com:%(hosting_owner)s/'
                            '%(hosting_project_name)s.git',
                    'mirror_path': '',
                    'raw_file_url': 'http://github.com/api/v2/yaml/blob/show/'
                                    '%(hosting_owner)s/'
                                    '%(hosting_project_name)s/'
                                    '<revision>'
                                    '?login=%(hosting_owner)s'
                                    '&token=%(github_api_token)s'
                },
            },
        }),
        ('github-private-org', {
            'label': _('GitHub (Private Organization)'),
            'fields': ['hosting_project_name', 'hosting_owner', 'github_api_token',
                       'username'],
            'hidden_fields': ['raw_file_url', 'password'],
            'tools': {
                'Git': {
                    'path': 'git@github.com:%(hosting_owner)s/'
                            '%(hosting_project_name)s.git',
                    'mirror_path': '',
                    'raw_file_url': 'http://github.com/api/v2/yaml/blob/show/'
                                    '%(hosting_owner)s/'
                                    '%(hosting_project_name)s/'
                                    '<revision>'
                                    '?login=%(username)s'
                                    '&token=%(github_api_token)s'
                },
            },
        }),
        ('gitorious', {
            'label': _('Gitorious'),
            'fields': ['project_slug', 'repository_name'],
            'hidden_fields': ['raw_file_url','username', 'password'],
            'tools': {
                'Git': {
                    'path': 'git://gitorious.org/%(project_slug)s/'
                            '%(repository_name)s.git',
                    'mirror_path': 'http://git.gitorious.org/%(project_slug)s/'
                                   '%(repository_name)s.git',
                    'raw_file_url': 'http://git.gitorious.org/%(project_slug)s/'
                                    '%(repository_name)s/blobs/raw/<revision>'
                },
            },
        }),
        ('googlecode', {
            'label': _('Google Code'),
            'fields': ['hosting_project_name'],
            'tools': {
                'Mercurial': {
                    'path': 'http://%(hosting_project_name)s'
                            '.googlecode.com/hg',
                    'mirror_path': 'https://%(hosting_project_name)s'
                                   '.googlecode.com/hg',
                },
                'Subversion': {
                    'path': 'http://%(hosting_project_name)s'
                            '.googlecode.com/svn',
                    'mirror_path': 'https://%(hosting_project_name)s'
                                   '.googlecode.com/svn',
                },
            },
        }),
        ('sourceforge', {
            'label': _('SourceForge'),
            'fields': ['hosting_project_name'],
            'tools': {
                'Bazaar': {
                    'path': 'bzr://%(hosting_project_name)s'
                            '.bzr.sourceforge.net/bzrroot/'
                            '%(hosting_project_name)s',
                    'mirror_path': 'bzr+ssh://%(hosting_project_name)s'
                                   '.bzr.sourceforge.net/bzrroot/'
                                   '%(hosting_project_name)s',
                },
                'CVS': {
                    'path': ':pserver:anonymous@%(hosting_project_name)s'
                            '.cvs.sourceforge.net:/cvsroot/'
                            '%(hosting_project_name)s',
                    'mirror_path': '%(hosting_project_name)s'
                                   '.cvs.sourceforge.net/cvsroot/'
                                   '%(hosting_project_name)s',
                },
                'Mercurial': {
                    'path': 'http://%(hosting_project_name)s'
                            '.hg.sourceforge.net:8000/hgroot/'
                            '%(hosting_project_name)s',
                    'mirror_path': 'ssh://%(hosting_project_name)s'
                                   '.hg.sourceforge.net/hgroot/'
                                   '%(hosting_project_name)s',
                },
                'Subversion': {
                    'path': 'http://%(hosting_project_name)s'
                            '.svn.sourceforge.net/svnroot/'
                            '%(hosting_project_name)s',
                    'mirror_path': 'https://%(hosting_project_name)s'
                                   '.svn.sourceforge.net/svnroot/'
                                   '%(hosting_project_name)s',
                },
                # TODO: Support Git
            },
        }),
        ('codebasehq', {
            'label': _('Codebase HQ'),
            'fields': ['hosting_project_name', 'codebase_group_name',
                       'codebase_repo_name', 'codebase_api_username',
                       'codebase_api_key'],
            'hidden_fields': ['username', 'password', 'raw_file_url'],
            'tools': {
                'Git': {
                    'username': '%(codebase_api_username)s',
                    'password': '%(codebase_api_key)s',
                    'path': 'git@codebasehq.com:%(codebase_group_name)s/'
                            '%(hosting_project_name)s/'
                            '%(codebase_repo_name)s.git',
                    'raw_file_url': 'https://api3.codebasehq.com/'
                                     '%(hosting_project_name)s/'
                                     '%(codebase_repo_name)s/blob/'
                                     '<revision>',
                },

                #
                # NOTE: Subversion doesn't work because it requires a
                #       standard username and password, not an API Username/token.
                #       We don't have a way of requesting that data just for this
                #       type.
                #
                #'Subversion': {
                #    'path': 'https://%(username)s@%(codebase_group_name)s/'
                #            '%(hosting_project_name)s/%(codebase_repo_name)s.svn',
                #},

                # NOTE: Mercurial doesn't work because they don't use HTTP Basic
                #       Auth for the authentication. A valid browser session cookie
                #       is needed instead.
                #
                #'Mercurial': {
                #    'username': '%(codebase_api_username)s',
                #    'password': '%(codebase_api_key)s',
                #    'path': 'https://%(codebase_group_name)s.codebasehq.com/'
                #            'projects/%(hosting_project_name)s/repositories/'
                #            '%(codebase_repo_name)s/'
                #},

                # TODO: Support Bazaar
            }
        }),
        ('custom', {
            'label': _('Custom'),
            'fields': ['path', 'mirror_path'],
        }),
    ])

    BUG_TRACKER_INFO = SortedDict([
        ('none', {
            'label': _('None'),
            'fields': [],
            'format': '',
        }),
        ('bitbucket', {
            'label': 'Bitbucket',
            'fields': ['bug_tracker_project_name', 'bug_tracker_owner'],
            'format': 'http://bitbucket.org/%(bug_tracker_owner)s/'
                      '%(bug_tracker_project_name)s/issue/%%s/',
        }),
        ('bugzilla', {
            'label': 'Bugzilla',
            'fields': ['bug_tracker_base_url'],
            'format': '%(bug_tracker_base_url)s/show_bug.cgi?id=%%s',
        }),
        ('fedorahosted', {
            'label': 'Fedora Hosted',
            'fields': ['bug_tracker_project_name'],
            'format': 'https://fedorahosted.org/%(bug_tracker_project_name)s'
                      '/ticket/%%s',
        }),
        ('github', {
            'label': 'GitHub',
            'fields': ['bug_tracker_project_name', 'bug_tracker_owner'],
            'format': 'http://github.com/%(bug_tracker_owner)s/'
                      '%(bug_tracker_project_name)s/issues#issue/%%s',
        }),
        ('github-private', {
            'label': 'GitHub (Private)',
            'fields': ['bug_tracker_project_name', 'bug_tracker_owner'],
            'format': 'http://github.com/%(bug_tracker_owner)s/'
                      '%(bug_tracker_project_name)s/issues#issue/%%s',
        }),
        ('googlecode', {
            'label': 'Google Code',
            'fields': ['bug_tracker_project_name'],
            'format': 'http://code.google.com/p/%(bug_tracker_project_name)s/'
                      'issues/detail?id=%%s',
        }),
        ('redmine', {
            'label': 'Redmine',
            'fields': ['bug_tracker_base_url'],
            'format': '%(bug_tracker_base_url)s/issues/%%s',
        }),
        ('sourceforge', {
            'label': 'SourceForge',
            'fields': [],
            'format': 'http://sourceforge.net/support/tracker.php?aid=%%s',
        }),
        ('trac', {
            'label': 'Trac',
            'fields': ['bug_tracker_base_url'],
            'format': '%(bug_tracker_base_url)s/ticket/%%s',
        }),
        ('custom', {
            'label': _('Custom'),
            'fields': ['bug_tracker'],
            'format': '%(bug_tracker)s',
        }),
    ])

    HOSTING_FIELDS = [
        "path", "mirror_path", "hosting_owner", "hosting_project_name",
        "github_api_token", "project_slug", "repository_name",
    ]

    BUG_TRACKER_FIELDS = [
        "bug_tracker_base_url", "bug_tracker_owner",
        "bug_tracker_project_name", "bug_tracker",
    ]

    FORMAT_STR_RE = re.compile(r'%\(([A-Za-z0-9_-]+)\)s')


    # Host trust state
    reedit_repository = forms.BooleanField(
        label=_("Re-edit repository"),
        required=False)

    trust_host = forms.BooleanField(
        label=_("I trust this host"),
        required=False)

    # Fields
    hosting_type = forms.ChoiceField(
        label=_("Hosting service"),
        required=True,
        choices=[(service_id, info['label'])
                 for service_id, info in HOSTING_SERVICE_INFO.iteritems()],
        initial="custom")

    hosting_owner = forms.CharField(
        label=_("Project's owner"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    hosting_project_name = forms.CharField(
        label=_("Project name"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    project_slug = forms.CharField(
        label=_("Project slug"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    repository_name = forms.CharField(
        label=_("Repository name"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    github_api_token = forms.CharField(
        label=_("API token"),
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('Your GitHub API token. This is needed in order to access '
                    'files on this repository. You can find this on your '
                    '<a href="http://github.com/account">Account</a> page '
                    'under "Account Admin."'))

    tool = forms.ModelChoiceField(
        label=_("Repository type"),
        required=True,
        empty_label=None,
        queryset=Tool.objects.all())

    bug_tracker_use_hosting = forms.BooleanField(
        label=_("Use hosting service's bug tracker"),
        required=False)

    bug_tracker_type = forms.ChoiceField(
        label=_("Type"),
        required=True,
        choices=[(tracker_id, info['label'])
                 for tracker_id, info in BUG_TRACKER_INFO.iteritems()],
        initial="none")

    bug_tracker_owner = forms.CharField(
        label=_("Bug Tracker's owner"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    bug_tracker_project_name = forms.CharField(
        label=_("Project name"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    bug_tracker_base_url = forms.CharField(
        label=_("Bug tracker URL"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_("This should be the path to the bug tracker for this "
                    "repository."))

    codebase_group_name = forms.CharField(
        label=_('Codebase HQ domain name'),
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The subdomain used to access your Codebase account'))

    codebase_repo_name = forms.CharField(
        label=_('Repository Short Name'),
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The short name of your repository. This can be found in '
                    'the "Repository Admin/Properties" page'))

    codebase_api_username = forms.CharField(
        label=_('API Username'),
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('Your Codebase API Username. You can find this in the '
                    'API Credentials section of the "My Profile" page at '
                    'http://&lt;groupname&gt;.codebasehq.com/settings/profile/'))

    codebase_api_key = forms.CharField(
        label=_('API Key'),
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={'size': '40'}))

    def __init__(self, *args, **kwargs):
        super(RepositoryForm, self).__init__(*args, **kwargs)

        self.hostkeyerror = None
        self.certerror = None
        self.userkeyerror = None

        local_site_name = None

        if self.instance and self.instance.local_site:
            local_site_name = self.instance.local_site.name
        elif self.fields['local_site'].initial:
            local_site_name = self.fields['local_site'].initial.name

        self.public_key = \
            sshutils.get_public_key(sshutils.get_user_key(local_site_name))

        self._populate_hosting_service_fields()
        self._populate_bug_tracker_fields()

    def _populate_hosting_service_fields(self):
        if (not self.instance or
            not self.instance.path):
            return

        tool_name = self.instance.tool.name

        for service_id, info in self.HOSTING_SERVICE_INFO.iteritems():
            if (service_id == 'custom' or tool_name not in info['tools']):
                continue

            field_info = info['tools'][tool_name]

            is_path_match, field_data = \
                self._match_url(self.instance.path,
                                field_info['path'],
                                info['fields'])

            if not is_path_match:
                continue

            if ('mirror_path' in field_info and
                not self._match_url(self.instance.mirror_path,
                                    field_info['mirror_path'], [])[0]):
                continue

            all_extras_match = True

            for extra_field, value in field_info.iteritems():
                if extra_field not in ('path', 'mirror_path'):
                    is_match, extra_field_data = \
                        self._match_url(getattr(self.instance, extra_field),
                                        value,
                                        info['fields'])

                    if not is_match:
                        all_extras_match = False
                        break

                    field_data.update(extra_field_data)

            if not all_extras_match:
                continue

            # It all matched.
            self.fields['hosting_type'].initial = service_id

            for key, value in field_data.iteritems():
                self.fields[key].initial = value

            break

    def _populate_bug_tracker_fields(self):
        if not self.instance or not self.instance.bug_tracker:
            return

        for tracker_id, info in self.BUG_TRACKER_INFO.iteritems():
            if tracker_id == 'none':
                continue

            is_match, field_data = \
                self._match_url(self.instance.bug_tracker,
                                info['format'], info['fields'])

            if is_match:
                self.fields['bug_tracker_type'].initial = tracker_id

                for key, value in field_data.iteritems():
                    self.fields[key].initial = value

                # Figure out whether this matches the hosting service.
                if tracker_id == self.fields['hosting_type'].initial:
                    is_match = True

                    for field in info['fields']:
                        hosting_field = field.replace("bug_tracker_",
                                                      "hosting_")

                        if (self.fields[hosting_field].initial !=
                               self.fields[field].initial):
                            is_match = False
                            break

                    if is_match:
                        self.fields['bug_tracker_use_hosting'].initial = True

                break

    def _clean_hosting_info(self):
        hosting_type = self.cleaned_data['hosting_type']

        if hosting_type == 'custom':
            return

        # Should be caught during validation.
        assert hosting_type in self.HOSTING_SERVICE_INFO
        info = self.HOSTING_SERVICE_INFO[hosting_type]

        tool_name = self.cleaned_data['tool'].name
        assert tool_name in info['tools']

        field_data = {}

        for field in info['fields']:
            field_data[field] = self.cleaned_data[field]

        for field, value in info['tools'][tool_name].iteritems():
            self.cleaned_data[field] = value % field_data
            self.data[field] = value % field_data

    def _clean_bug_tracker_info(self):
        use_hosting = self.cleaned_data['bug_tracker_use_hosting']
        bug_tracker_type = self.cleaned_data['bug_tracker_type']

        if bug_tracker_type == 'none' and not use_hosting:
            self.instance.bug_tracker = ""
            return

        if use_hosting:
            match_type = self.cleaned_data['hosting_type']
        else:
            match_type = bug_tracker_type

        assert match_type in self.BUG_TRACKER_INFO
        info = self.BUG_TRACKER_INFO[match_type]

        field_data = {}

        for field in info['fields']:
            src_field = field

            if use_hosting:
                src_field = src_field.replace("bug_tracker_", "hosting_")

            field_data[field] = self.cleaned_data[src_field]

        bug_tracker_url = info['format'] % field_data
        self.cleaned_data['bug_tracker'] = bug_tracker_url
        self.data['bug_tracker'] = bug_tracker_url

    def full_clean(self):
        if self.data:
            hosting_type = (self['hosting_type'].data or
                            self.fields['hosting_type'].initial)
            use_hosting = (self['bug_tracker_use_hosting'].data or
                           self.fields['bug_tracker_use_hosting'].initial)

            self.fields['path'].required = (hosting_type == "custom")
            self.fields['bug_tracker_type'].required = not use_hosting

        return super(RepositoryForm, self).full_clean()

    def clean(self):
        """
        Performs validation on the form.

        This will check the form fields for errors, calling out to the
        various clean_* methods.

        It will check the repository path to see if it represents
        a valid repository and if an SSH key or HTTPS certificate needs
        to be verified.

        This will also build repository and bug tracker URLs based on other
        fields set in the form.
        """
        self._clean_hosting_info()
        self._clean_bug_tracker_info()

        validate_review_groups(self)
        validate_users(self)

        if not self.cleaned_data['reedit_repository']:
            self._verify_repository_path()

        return super(RepositoryForm, self).clean()

    def clean_path(self):
        return self.cleaned_data['path'].strip()

    def clean_mirror_path(self):
        return self.cleaned_data['mirror_path'].strip()

    def clean_bug_tracker_base_url(self):
        data = self.cleaned_data['bug_tracker_base_url']
        return data.rstrip("/")

    def clean_tool(self):
        """
        Checks the SCMTool used for this repository for dependencies.

        If one or more dependencies aren't found, they will be presented
        as validation errors.
        """
        tool = self.cleaned_data['tool']
        scmtool_class = tool.get_scmtool_class()

        errors = []

        for dep in scmtool_class.dependencies.get('modules', []):
            try:
                imp.find_module(dep)
            except ImportError:
                errors.append('The Python module "%s" is not installed.'
                              'You may need to restart the server '
                              'after installing it.' % dep)

        for dep in scmtool_class.dependencies.get('executables', []):
            if not is_exe_in_path(dep):
                if sys.platform == 'win32':
                    exe_name = '%s.exe' % dep
                else:
                    exe_name = dep

                errors.append('The executable "%s" is not in the path.' %
                              exe_name)

        if errors:
            raise forms.ValidationError(errors)

        return tool

    def is_valid(self):
        """
        Returns whether or not the form is valid.

        This will return True if the form fields are all valid, if there's
        no certificate error, host key error, and if the form isn't
        being re-displayed after canceling an SSH key or HTTPS certificate
        verification.
        """
        return (super(RepositoryForm, self).is_valid() and
                not self.hostkeyerror and
                not self.certerror and
                not self.userkeyerror and
                not self.cleaned_data['reedit_repository'])

    def _match_url(self, url, format, fields):
        """
        Matches a URL against a format string.

        This will determine if the URL can be represented by the format
        string. If so, the URL will parsed for the list of fields and
        returned.

        The result is in the form of (bool, field_dict).
        """
        def replace_match_group(m):
            name = m.group(1)

            if name in found_groups:
                return r'(?P=%s)' % name
            else:
                found_groups[name] = True
                return r'(?P<%s>[A-Za-z0-9:/._-]+)' % name

        # First, transform our Python format-style pattern to a regex.
        pattern = format.replace("%%s", "%s")
        pattern = pattern.replace("?", "\?")
        pattern = pattern.replace("+", "\+")

        # A list of match groups to replace that we've already found.
        # re.sub will get angry if it sees two with the same name.
        found_groups = {}

        pattern = self.FORMAT_STR_RE.sub(replace_match_group, pattern)

        m = re.match(pattern, url)

        if not m:
            return False, {}

        field_data = {}

        for field in fields:
            try:
                field_data[field] = m.group(field)
            except IndexError:
                pass

        return True, field_data

    def _verify_repository_path(self):
        """
        Verifies the repository path to check if it's valid.

        This will check if the repository exists and if an SSH key or
        HTTPS certificate needs to be verified.
        """
        tool = self.cleaned_data.get('tool', None)

        if not tool:
            # This failed validation earlier, so bail.
            return

        scmtool_class = tool.get_scmtool_class()

        path = self.cleaned_data.get('path', '')
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']

        if not path:
            self._errors['path'] = self.error_class(
                ['Repository path cannot be empty'])
            return

        local_site_name = None

        if self.cleaned_data['local_site']:
            try:
                local_site = self.cleaned_data['local_site']
                local_site_name = local_site.name
            except LocalSite.DoesNotExist, e:
                raise forms.ValidationError(e)

        while 1:
            # Keep doing this until we have an error we don't want
            # to ignore, or it's successful.
            try:
                scmtool_class.check_repository(path, username, password,
                                               local_site_name)

                # Success.
                break
            except BadHostKeyError, e:
                if self.cleaned_data['trust_host']:
                    try:
                        sshutils.replace_host_key(e.hostname,
                                                  e.raw_expected_key,
                                                  e.raw_key,
                                                  local_site_name)
                    except IOError, e:
                        raise forms.ValidationError(e)
                else:
                    self.hostkeyerror = e
                    break
            except UnknownHostKeyError, e:
                if self.cleaned_data['trust_host']:
                    try:
                        sshutils.add_host_key(e.hostname, e.raw_key,
                                              local_site_name)
                    except IOError, e:
                        raise forms.ValidationError(e)
                else:
                    self.hostkeyerror = e
                    break
            except UnverifiedCertificateError, e:
                if self.cleaned_data['trust_host']:
                    try:
                        scmtool_class.accept_certificate(path, local_site_name)
                    except IOError, e:
                        raise forms.ValidationError(e)
                else:
                    self.certerror = e
                    break
            except AuthenticationError, e:
                if 'publickey' in e.allowed_types and e.user_key is None:
                    self.userkeyerror = e
                    break

                raise forms.ValidationError(e)
            except Exception, e:
                try:
                    text = unicode(e)
                except UnicodeDecodeError:
                    text = str(e).decode('ascii', 'replace')
                raise forms.ValidationError(text)

    class Meta:
        model = Repository
        widgets = {
            'path': forms.TextInput(attrs={'size': '60'}),
            'mirror_path': forms.TextInput(attrs={'size': '60'}),
            'raw_file_url': forms.TextInput(attrs={'size': '60'}),
            'bug_tracker': forms.TextInput(attrs={'size': '60'}),
            'username': forms.TextInput(attrs={'size': '30',
                                               'autocomplete': 'off'}),
            'password': forms.PasswordInput(attrs={'size': '30',
                                                   'autocomplete': 'off'}),
            'users': FilteredSelectMultiple(_('users with access'), False),
            'review_groups': FilteredSelectMultiple(
                _('review groups with access'), False),
        }
