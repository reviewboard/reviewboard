import imp
import logging
import re
import sys

from django import forms
from django.contrib.admin.helpers import Fieldset
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from djblets.util.filesystem import is_exe_in_path

from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_services, \
                                            get_hosting_service
from reviewboard.scmtools import sshutils
from reviewboard.scmtools.errors import AuthenticationError, \
                                        BadHostKeyError, \
                                        UnknownHostKeyError, \
                                        UnverifiedCertificateError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.validation import validate_review_groups, validate_users


class RepositoryForm(forms.ModelForm):
    """A form for creating and updating repositories.

    This form provides an interface for creating and updating repositories,
    handling the association with hosting services, linking accounts,
    dealing with SSH keys and SSL certificates, and more.
    """

    # NOTE: The list of fields must match that of the corresponding
    #       bug tracker (not including the hosting_ and bug_tracker_
    #       prefixes), for hosting services matching bug trackers.
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

    FORMAT_STR_RE = re.compile(r'%\(([A-Za-z0-9_-]+)\)s')

    REPOSITORY_INFO_FIELDSET = _("Repository Information")
    NO_HOSTING_SERVICE_ID = 'custom'
    DEFAULT_PLAN_ID = 'default'
    DEFAULT_PLAN_NAME = _('Default')

    # Host trust state
    reedit_repository = forms.BooleanField(
        label=_("Re-edit repository"),
        required=False)

    trust_host = forms.BooleanField(
        label=_("I trust this host"),
        required=False)

    # Repository Hosting fields
    hosting_type = forms.ChoiceField(
        label=_("Hosting service"),
        required=True,
        initial=NO_HOSTING_SERVICE_ID)

    hosting_account = forms.ModelChoiceField(
        label=_('Account'),
        required=True,
        empty_label=_('<Link a new account>'),
        help_text=_("Link this repository to an account on the hosting "
                    "service."),
        queryset=HostingServiceAccount.objects.none())

    hosting_account_username = forms.CharField(
        label=_('Account username'),
        required=True,
        widget=forms.TextInput(attrs={'size': 30, 'autocomplete': 'off'}))

    hosting_account_password = forms.CharField(
        label=_('Account password'),
        required=True,
        widget=forms.PasswordInput(attrs={'size': 30, 'autocomplete': 'off'}))

    # Repository Information fields
    tool = forms.ModelChoiceField(
        label=_("Repository type"),
        required=True,
        empty_label=None,
        queryset=Tool.objects.all())

    repository_plan = forms.ChoiceField(
        label=_('Repository plan'),
        required=True)

    # Bug Tracker fields
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

    def __init__(self, *args, **kwargs):
        super(RepositoryForm, self).__init__(*args, **kwargs)

        self.hostkeyerror = None
        self.certerror = None
        self.userkeyerror = None
        self.hosting_account_linked = False
        self.local_site_name = None
        self.repository_forms = {}
        self.hosting_service_info = {}

        # Determine the local_site that will be associated with any
        # repository coming from this form.
        #
        # We're careful to disregard any local_sites that are specified
        # from the form data. The caller needs to pass in a local_site
        # as initial data to ensure that it will be used.
        if self.instance and self.instance.local_site:
            self.local_site_name = self.instance.local_site.name
        elif self.fields['local_site'].initial:
            self.local_site_name = self.fields['local_site'].initial.name

        if self.local_site_name:
            self.local_site = LocalSite.objects.get(name=self.local_site_name)
        else:
            self.local_site = None

        # Grab the entire list of HostingServiceAccounts that can be
        # used by this form. When the form is actually being used by the
        # user, the listed accounts will consist only of the ones available
        # for the selected hosting service.
        hosting_accounts = HostingServiceAccount.objects.accessible(
            local_site=self.local_site)
        self.fields['hosting_account'].queryset = hosting_accounts

        # Standard forms don't support 'instance', so don't pass it through
        # to any created hosting service forms.
        if 'instance' in kwargs:
            kwargs.pop('instance')

        # Load the list of repository forms and hosting services.
        hosting_service_choices = []

        for hosting_service_id, hosting_service in get_hosting_services():
            hosting_service_choices.append((hosting_service_id,
                                            hosting_service.name))

            self.repository_forms[hosting_service_id] = {}
            self.hosting_service_info[hosting_service_id] = {
                'scmtools': hosting_service.supported_scmtools,
                'plans': [],
                'accounts': [
                    {
                        'pk': account.pk,
                        'username': account.username,
                    }
                    for account in hosting_accounts
                    if account.service_name == hosting_service_id
                ],
            }

            try:
                if hosting_service.repository_plans:
                    for type_id, info in hosting_service.repository_plans:
                        repository_form = info.get('repository_form', None)

                        if repository_form:
                            self._load_repository_form(hosting_service_id,
                                                       type_id,
                                                       info['name'],
                                                       repository_form,
                                                       *args, **kwargs)
                elif hosting_service.repository_form:
                    self._load_repository_form(hosting_service_id,
                                               self.DEFAULT_PLAN_ID,
                                               self.DEFAULT_PLAN_NAME,
                                               hosting_service.repository_form,
                                               *args, **kwargs)
            except Exception, e:
                logging.error('Error loading hosting service %s: %s'
                              % (hosting_service_id, e),
                              exc_info=1)

        # Build the list of hosting service choices, sorted, with
        # "None" being first.
        hosting_service_choices.sort(key=lambda x: x[1])
        hosting_service_choices.insert(0, (self.NO_HOSTING_SERVICE_ID,
                                           _('(None - Custom Repository)')))
        self.fields['hosting_type'].choices = hosting_service_choices

        self.public_key = \
            sshutils.get_public_key(sshutils.get_user_key(self.local_site_name))

        self._populate_hosting_service_fields()
        self._populate_bug_tracker_fields()

    def _load_repository_form(self, hosting_service_id, repo_type_id,
                              repo_type_label, form_class, *args, **kwargs):
        """Loads a hosting service form.

        The form will be instantiated and added to the list of forms to be
        rendered, cleaned, loaded, and saved.
        """
        form = form_class(*args, **kwargs)

        self.repository_forms[hosting_service_id][repo_type_id] = form

        self.hosting_service_info[hosting_service_id]['plans'].append({
            'type': repo_type_id,
            'label': unicode(repo_type_label),
        })

        if self.instance:
            form.load(self.instance)

    def _populate_hosting_service_fields(self):
        """Populates all the main hosting service fields in the form.

        This populates the hosting service type and the repository plan
        on the form. These are only set if operating on an existing
        repository.
        """
        if self.instance:
            hosting_account = self.instance.hosting_account

            if hosting_account:
                self.fields['hosting_type'].initial = \
                    hosting_account.service_name

            repository_plan = self.instance.extra_data.get('repository_plan',
                                                           None)

            if repository_plan:
                self.fields['repository_plan'].initial = repository_plan

    def _populate_bug_tracker_fields(self):
        if not self.instance or not self.instance.bug_tracker:
            return

        # XXX
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
        """Clean the hosting service information.

        If using a hosting service, this will validate that the data
        provided is valid on that hosting service. Then it will create an
        account and link it, if necessary, with the hosting service.
        """
        hosting_type = self.cleaned_data['hosting_type']

        if hosting_type == 'custom':
            return

        # This should have been caught during validation, so we can assume
        # it's fine.
        hosting_service = get_hosting_service(hosting_type)
        assert hosting_service

        # Validate that the provided tool is valid for the hosting service.
        tool_name = self.cleaned_data['tool'].name

        if tool_name not in hosting_service.supported_scmtools:
            self.errors['tool'] = self.error_class([
                _('This tool is not supported on the given hosting service')
            ])
            return

        # Now make sure all the account info is correct.
        hosting_account = self.cleaned_data['hosting_account']
        username = self.cleaned_data['hosting_account_username']
        password = self.cleaned_data['hosting_account_password']

        if not hosting_account and not username:
            self.errors['hosting_account'] = self.error_class([
                _('An account must be linked in order to use this hosting '
                  'service'),
            ])
            return

        if not hosting_account:
            # See if this account with the supplied credentials already
            # exists. If it does, we don't want to create a new entry.
            try:
                hosting_account = HostingServiceAccount.objects.get(
                    service_name=hosting_type,
                    username=username,
                    local_site=self.local_site)
            except HostingServiceAccount.DoesNotExist:
                # That's fine. We're just going to create it later.
                pass

        # If the hosting account needs to authorize and link with an external
        # service, attempt to do so and watch for any errors.
        if not hosting_account and hosting_service.needs_authorization:
            hosting_account = HostingServiceAccount(service_name=hosting_type,
                                                    username=username)

            try:
                hosting_account.service.authorize(
                    username, password, local_site_name=self.local_site_name)

                # Flag that we've linked the account. If there are any
                # validation errors, and this flag is set, we tell the user
                # that we successfully linked and they don't have to do it
                # again.
                self.hosting_account_linked = True
            except AuthorizationError, e:
                self.errors['hosting_account'] = self.error_class([
                    _('Unable to link the account: %s') % e,
                ])
                return
            except Exception, e:
                self.errors['hosting_account'] = self.error_class([
                    _('Unknown error when linking the account: %s') % e,
                ])
                return

            hosting_account.save()

        self.data['hosting_account'] = hosting_account
        self.cleaned_data['hosting_account'] = hosting_account

        plan = self.cleaned_data.get('repository_plan', self.DEFAULT_PLAN_ID)

        # Set the main repository fields (Path, Mirror Path, etc.) based on
        # the field definitions in the hosting service.
        #
        # This will take into account the hosting service's form data for
        # the given repository plan, the main form data, and the hosting
        # account information.
        #
        # It's expected that the required fields will have validated by now.
        repository_form = self.repository_forms[hosting_type][plan]
        field_vars = repository_form.cleaned_data.copy()
        field_vars.update(self.cleaned_data)

        try:
            self.cleaned_data.update(hosting_service.get_repository_fields(
                plan, tool_name, field_vars))
        except KeyError, e:
            raise forms.ValidationError([unicode(e)])

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
        extra_cleaned_data = {}
        extra_errors = {}

        if self.data:
            hosting_type = self._get_field_data('hosting_type')
            hosting_service = get_hosting_service(hosting_type)

            bug_tracker_use_hosting = \
                self._get_field_data('bug_tracker_use_hosting')
            new_hosting_account = (
                hosting_type != self.NO_HOSTING_SERVICE_ID and
                not self._get_field_data('hosting_account'))

            self.fields['path'].required = \
                (hosting_type == self.NO_HOSTING_SERVICE_ID)
            self.fields['bug_tracker_type'].required = \
                not bug_tracker_use_hosting

            # The repository plan will only be listed if the hosting service
            # lists some plans. Otherwise, there's nothing to require.

            self.fields['repository_plan'].required = \
                (hosting_service and hosting_service.repository_plans)

            if hosting_service:
                self.fields['repository_plan'].choices = [
                    (id, info['name'])
                    for id, info in hosting_service.repository_plans
                ]

            # We want to show this as required (in the label), but not
            # actually require, since we use a blank entry as
            # "Link new account."
            self.fields['hosting_account'].required = False

            # Only require a username and password if not using an existing
            # hosting account.
            for field in ('hosting_account_username',
                          'hosting_account_password'):
                self.fields[field].required = new_hosting_account

            plan = (self._get_field_data('repository_plan') or
                    self.DEFAULT_PLAN_ID)

            if hosting_type in self.repository_forms:
                # Validate the hosting service form and store any
                # data or errors for later.
                form = self.repository_forms[hosting_type][plan]

                if not form.is_valid():
                    extra_cleaned_data.update(form.cleaned_data)
                else:
                    extra_errors.update(form.errors)
        else:
            # Validate every hosting service form and store any
            # data or errors for later.
            for plans in self.repository_forms.values():
                for form in plans:
                    if form.is_valid():
                        extra_cleaned_data.update(form.cleaned_data)
                    else:
                        extra_errors.update(form.errors)

        super(RepositoryForm, self).full_clean()

        if self.is_valid():
            self.cleaned_data.update(extra_cleaned_data)
        else:
            self.errors.update(extra_errors)

        # Undo the hosting account above. This is so that the field will
        # display correctly.
        self.fields['hosting_account'].required = True

    def clean(self):
        """Performs validation on the form.

        This will check the form fields for errors, calling out to the
        various clean_* methods.

        It will check the repository path to see if it represents
        a valid repository and if an SSH key or HTTPS certificate needs
        to be verified.

        This will also build repository and bug tracker URLs based on other
        fields set in the form.
        """
        if not self.errors:
            self._clean_hosting_info()
            self._clean_bug_tracker_info()

            validate_review_groups(self)
            validate_users(self)

            # The clean/validation functions could create new errors, so
            # skip validating the repository path if everything else isn't
            # clean.
            if not self.errors and not self.cleaned_data['reedit_repository']:
                self._verify_repository_path()

        return super(RepositoryForm, self).clean()

    def clean_path(self):
        return self.cleaned_data['path'].strip()

    def clean_mirror_path(self):
        return self.cleaned_data['mirror_path'].strip()

    def clean_bug_tracker_base_url(self):
        return self.cleaned_data['bug_tracker_base_url'].rstrip('/')

    def clean_hosting_type(self):
        """Validates that the hosting type represents a valid hosting service.

        This won't do anything if no hosting service is used.
        """
        hosting_type = self.cleaned_data['hosting_type']

        if hosting_type != self.NO_HOSTING_SERVICE_ID:
            hosting_service = get_hosting_service(hosting_type)

            if not hosting_service:
                raise forms.ValidationError(['Not a valid hosting service'])

        return hosting_type

    def clean_tool(self):
        """Checks the SCMTool used for this repository for dependencies.

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
        """Returns whether or not the form is valid.

        This will return True if the form fields are all valid, if there's
        no certificate error, host key error, and if the form isn't
        being re-displayed after canceling an SSH key or HTTPS certificate
        verification.

        This also takes into account the validity of the hosting service form
        for the selected hosting service and repository plan.
        """
        if not super(RepositoryForm, self).is_valid():
            return False

        hosting_type = self.cleaned_data['hosting_type']
        plan = self.cleaned_data['repository_plan'] or self.DEFAULT_PLAN_ID

        return (not self.hostkeyerror and
                not self.certerror and
                not self.userkeyerror and
                not self.cleaned_data['reedit_repository'] and
                (hosting_type not in self.repository_forms or
                 self.repository_forms[hosting_type][plan].is_valid()))

    def save(self, commit=True, *args, **kwargs):
        """Saves the repository.

        This will thunk out to the hosting service form to save any extra
        repository data used for the hosting service, and saves the
        repository plan, if any.
        """
        repository = super(RepositoryForm, self).save(commit=False,
                                                      *args, **kwargs)

        repository.extra_data['repository_plan'] = \
            self.cleaned_data['repository_plan']

        hosting_type = self.cleaned_data['hosting_type']
        plan = self.cleaned_data['repository_plan'] or self.DEFAULT_PLAN_ID

        if hosting_type in self.repository_forms:
            self.repository_forms[hosting_type][plan].save(repository)

        if commit:
            repository.save()

        return repository

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

        while 1:
            # Keep doing this until we have an error we don't want
            # to ignore, or it's successful.
            try:
                scmtool_class.check_repository(path, username, password,
                                               self.local_site_name)

                # Success.
                break
            except BadHostKeyError, e:
                if self.cleaned_data['trust_host']:
                    try:
                        sshutils.replace_host_key(e.hostname,
                                                  e.raw_expected_key,
                                                  e.raw_key,
                                                  self.local_site_name)
                    except IOError, e:
                        raise forms.ValidationError(e)
                else:
                    self.hostkeyerror = e
                    break
            except UnknownHostKeyError, e:
                if self.cleaned_data['trust_host']:
                    try:
                        sshutils.add_host_key(e.hostname, e.raw_key,
                                              self.local_site_name)
                    except IOError, e:
                        raise forms.ValidationError(e)
                else:
                    self.hostkeyerror = e
                    break
            except UnverifiedCertificateError, e:
                if self.cleaned_data['trust_host']:
                    try:
                        scmtool_class.accept_certificate(path,
                                                         self.local_site_name)
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

    def _get_field_data(self, field):
        return self[field].data or self.fields[field].initial

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
