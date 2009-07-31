import re

from django import forms
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _

from reviewboard.scmtools.models import Tool


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
                            '.cvs.sourceforge.net/cvsroot/'
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
        ('custom', {
            'label': _('Custom'),
            'fields': ['path', 'mirror_path'],
        }),

        # TODO: Add GitHub when we have remote Git support.
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
    ]

    BUG_TRACKER_FIELDS = [
        "bug_tracker_base_url", "bug_tracker_owner",
        "bug_tracker_project_name", "bug_tracker",
    ]

    FORMAT_STR_RE = re.compile(r'%\(([A-Za-z0-9_-]+)\)s')


    # Fields
    name = forms.CharField(
        label=_("Name"),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))

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

    path = forms.CharField(
        label=_("Path"),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_("This should be the path to the repository. For most "
                    "version control systems, this will be a URI of some "
                    "form or another. For CVS, this should be a pserver "
                    "path. For Perforce, this should be a port name. For "
                    "git, this should be the path to the .git repository "
                    "on the local disk."))

    mirror_path = forms.CharField(
        label=_("Mirror path"),
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}))

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

    bug_tracker = forms.CharField(
        label=_("Bug tracker URL"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_("This should be the full path to a bug in the bug tracker "
                    "for this repository, using '%s' in place of the bug ID."))

    username = forms.CharField(
        label=_("Username"),
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    password = forms.CharField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(attrs={'size': '30'}))

    encoding = forms.CharField(
        label=_("Encoding"),
        max_length=32,
        required=False,
        help_text=_("The encoding used for files in this repository. This is "
                    "an advanced setting and should only be used if you're "
                    "sure you need it."))


    def __init__(self, *args, **kwargs):
        super(RepositoryForm, self).__init__(*args, **kwargs)

        self.populate_hosting_service_fields()
        self.populate_bug_tracker_fields()

    def populate_hosting_service_fields(self):
        if (not self.instance or
            not self.instance.path or
            not self.instance.mirror_path):
            return

        tool_name = self.instance.tool.name

        for service_id, info in self.HOSTING_SERVICE_INFO.iteritems():
            if (service_id == 'custom' or tool_name not in info['tools']):
                continue

            field_info = info['tools'][tool_name]

            is_path_match, field_data = \
                self.match_url(self.instance.path,
                               field_info['path'],
                               info['fields'])

            if is_path_match:
                is_mirror_path_match = \
                    self.match_url(self.instance.mirror_path,
                                   field_info['mirror_path'], [])[0]

                if is_mirror_path_match:
                    self.fields['hosting_type'].initial = service_id

                    for key, value in field_data.iteritems():
                        self.fields[key].initial = value

                    break

    def populate_bug_tracker_fields(self):
        if not self.instance or not self.instance.bug_tracker:
            return

        for tracker_id, info in self.BUG_TRACKER_INFO.iteritems():
            if tracker_id == 'none':
                continue

            is_match, field_data = \
                self.match_url(self.instance.bug_tracker,
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

    def save(self, *args, **kwargs):
        self.save_hosting_info()
        self.save_bug_tracker_info()

        return super(RepositoryForm, self).save(*args, **kwargs)

    def save_hosting_info(self):
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

    def save_bug_tracker_info(self):
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

        self.cleaned_data['bug_tracker'] = info['format'] % field_data

    def full_clean(self):
        if self.data:
            hosting_type = (self['hosting_type'].data or
                            self.fields['hosting_type'].initial)
            use_hosting = (self['bug_tracker_use_hosting'].data or
                           self.fields['bug_tracker_use_hosting'].initial)

            self.fields['path'].required = (hosting_type == "custom")
            self.fields['bug_tracker_type'].required = not use_hosting

        return super(RepositoryForm, self).full_clean()

    def clean_bug_tracker_base_url(self):
        data = self.cleaned_data['bug_tracker_base_url']
        return data.rstrip("/")

    def match_url(self, url, format, fields):
        """Matches a URL against a format string.

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

        # A list of match groups to replace that we've already found.
        # re.sub will get angry if it sees two with the same name.
        found_groups = {}

        pattern = self.FORMAT_STR_RE.sub(replace_match_group, pattern)

        m = re.match(pattern, url)

        if not m:
            return False, {}

        field_data = {}

        for field in fields:
            field_data[field] = m.group(field)

        return True, field_data
