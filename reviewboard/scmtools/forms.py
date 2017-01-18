from __future__ import unicode_literals

import logging
import sys

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms.widgets import Select
from djblets.db.query import get_object_or_none
from django.utils import six
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from djblets.util.filesystem import is_exe_in_path

from reviewboard.admin.form_widgets import RelatedUserWidget
from reviewboard.admin.import_utils import has_module
from reviewboard.admin.validation import validate_bug_tracker
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            SSHKeyAssociationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.fake import FAKE_HOSTING_SERVICES
from reviewboard.hostingsvcs.forms import HostingServiceAuthForm
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (get_hosting_services,
                                             get_hosting_service)
from reviewboard.scmtools.errors import (AuthenticationError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.fake import FAKE_SCMTOOLS
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.site.validation import validate_review_groups, validate_users
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import (BadHostKeyError,
                                    UnknownHostKeyError)


class HostingAccountWidget(Select):
    """A widget for selecting and modifying an assigned hosting account.

    This presents a list of available hosting service accounts as a drop-down,
    and provides a link for editing the credentials of the selected account.
    """

    def render(self, *args, **kwargs):
        """Render the widget.

        Args:
            *args (tuple):
                Arguments for the render.

            **kwargs (dict):
                Keyword arguments for the render.

        Returns:
            django.utils.safestring.SafeText:
            The HTML for the widget.
        """
        html = super(HostingAccountWidget, self).render(*args, **kwargs)

        return mark_safe(html + (
            '<a href="#" id="repo-edit-hosting-credentials">'
            '<span class="rb-icon rb-icon-edit"></span> '
            '<span id="repo-edit-hosting-credentials-label">%s</span></a>'
            % _('Edit credentials')
        ))


class RepositoryForm(forms.ModelForm):
    """A form for creating and updating repositories.

    This form provides an interface for creating and updating repositories,
    handling the association with hosting services, linking accounts,
    dealing with SSH keys and SSL certificates, and more.
    """

    REPOSITORY_HOSTING_FIELDSET = _('Repository Hosting')
    REPOSITORY_INFO_FIELDSET = _('Repository Information')
    BUG_TRACKER_FIELDSET = _('Bug Tracker')
    SSH_KEY_FIELDSET = _('Review Board Server SSH Key')

    NO_HOSTING_SERVICE_ID = 'custom'
    NO_HOSTING_SERVICE_NAME = _('(None - Custom Repository)')

    NO_BUG_TRACKER_ID = 'none'
    NO_BUG_TRACKER_NAME = _('(None)')

    CUSTOM_BUG_TRACKER_ID = 'custom'
    CUSTOM_BUG_TRACKER_NAME = _('(Custom Bug Tracker)')

    IGNORED_SERVICE_IDS = ('none', 'custom')

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
                    "service. This username may be used as part of the "
                    "repository URL, depending on the hosting service and "
                    "plan."),
        queryset=HostingServiceAccount.objects.none(),
        widget=HostingAccountWidget())

    force_authorize = forms.BooleanField(
        label=_('Force reauthorization'),
        required=False,
        widget=forms.HiddenInput())

    # Repository Information fields
    tool = forms.ChoiceField(
        label=_("Repository type"),
        required=True)

    repository_plan = forms.ChoiceField(
        label=_('Repository plan'),
        required=True,
        help_text=_('The plan for your repository on this hosting service. '
                    'This must match what is set for your repository.'))

    password = forms.CharField(
        label=_('Password'),
        required=False,
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                'size': '30',
                'autocomplete': 'off',
            }))

    # Auto SSH key association field
    associate_ssh_key = forms.BooleanField(
        label=_('Associate my SSH key with the hosting service'),
        required=False,
        help_text=_('Add the Review Board public SSH key to the list of '
                    'authorized SSH keys on the hosting service.'))

    NO_KEY_HELP_FMT = (_('This repository type supports SSH key association, '
                         'but the Review Board server does not have an SSH '
                         'key. <a href="%s">Add an SSH key.</a>'))

    # Bug Tracker fields
    bug_tracker_use_hosting = forms.BooleanField(
        label=_("Use hosting service's bug tracker"),
        initial=False,
        required=False)

    bug_tracker_type = forms.ChoiceField(
        label=_("Type"),
        required=True,
        initial=NO_BUG_TRACKER_ID)

    bug_tracker_hosting_url = forms.CharField(
        label=_('URL'),
        required=True,
        widget=forms.TextInput(attrs={'size': 30}))

    bug_tracker_plan = forms.ChoiceField(
        label=_('Bug tracker plan'),
        required=True)

    bug_tracker_hosting_account_username = forms.CharField(
        label=_('Account username'),
        required=True,
        widget=forms.TextInput(attrs={'size': 30, 'autocomplete': 'off'}))

    bug_tracker = forms.CharField(
        label=_("Bug tracker URL"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=(
            _("The optional path to the bug tracker for this repository. The "
              "path should resemble: http://www.example.com/issues?id=%%s, "
              "where %%s will be the bug number.")
            % ()),  # We do this wacky formatting trick because otherwise
                    # xgettext gets upset that it sees a format string with
                    # positional arguments and will abort when trying to
                    # extract the message catalog.
        validators=[validate_bug_tracker])

    # Perforce-specific fields
    use_ticket_auth = forms.BooleanField(
        label=_("Use ticket-based authentication"),
        initial=False,
        required=False)

    # Access control fields
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=_('Users with access'),
        required=False,
        widget=RelatedUserWidget())

    def __init__(self, *args, **kwargs):
        self.local_site_name = kwargs.pop('local_site_name', None)

        super(RepositoryForm, self).__init__(*args, **kwargs)

        self.hostkeyerror = None
        self.certerror = None
        self.userkeyerror = None
        self.bug_tracker_host_error = None
        self.hosting_account_linked = False
        self.local_site = None
        self.repository_forms = {}
        self.bug_tracker_forms = {}
        self.hosting_auth_forms = {}
        self.hosting_service_info = {}
        self.tool_info = {
            'none': {
                'fields': ['raw_file_url', 'username', 'password',
                           'use_ticket_auth'],
            },
        }
        self.validate_repository = True
        self.cert = None

        # Determine the local_site that will be associated with any
        # repository coming from this form.
        #
        # We're careful to disregard any local_sites that are specified
        # from the form data. The caller needs to pass in a local_site_name
        # to ensure that it will be used.
        if self.local_site_name:
            self.local_site = LocalSite.objects.get(name=self.local_site_name)
        elif self.instance and self.instance.local_site:
            self.local_site = self.instance.local_site
            self.local_site_name = self.local_site.name
        elif self.fields['local_site'].initial:
            self.local_site = self.fields['local_site'].initial
            self.local_site_name = self.local_site.name

        self.fields['users'].widget.local_site_name = self.local_site_name

        # Grab the entire list of HostingServiceAccounts that can be
        # used by this form. When the form is actually being used by the
        # user, the listed accounts will consist only of the ones available
        # for the selected hosting service.
        hosting_accounts = HostingServiceAccount.objects.accessible(
            local_site=self.local_site)
        self.fields['hosting_account'].queryset = hosting_accounts

        hosting_accounts = list(hosting_accounts)

        # Standard forms don't support 'instance', so don't pass it through
        # to any created hosting service forms.
        if 'instance' in kwargs:
            kwargs.pop('instance')

        # Load the list of repository forms and hosting services.
        hosting_service_choices = []
        bug_tracker_choices = []

        hosting_services = set()

        for hosting_service in get_hosting_services():
            class_name = '%s.%s' % (hosting_service.__module__,
                                    hosting_service.__name__)
            hosting_services.add(class_name)

            auth_form_cls = hosting_service.auth_form or HostingServiceAuthForm

            if hosting_service.supports_repositories:
                hosting_service_choices.append((hosting_service.id,
                                                hosting_service.name))

            if hosting_service.supports_bug_trackers:
                bug_tracker_choices.append((hosting_service.id,
                                            hosting_service.name))

            self.bug_tracker_forms[hosting_service.id] = {}
            self.repository_forms[hosting_service.id] = {}
            self.hosting_service_info[hosting_service.id] = \
                self._get_hosting_service_info(hosting_service,
                                               hosting_accounts)

            try:
                if hosting_service.plans:
                    for type_id, info in hosting_service.plans:
                        form = info.get('form', None)

                        if form:
                            self._load_hosting_service(hosting_service.id,
                                                       hosting_service,
                                                       type_id,
                                                       info['name'],
                                                       form,
                                                       *args, **kwargs)
                elif hosting_service.form:
                    self._load_hosting_service(hosting_service.id,
                                               hosting_service,
                                               self.DEFAULT_PLAN_ID,
                                               self.DEFAULT_PLAN_NAME,
                                               hosting_service.form,
                                               *args, **kwargs)

                # Load the hosting service's custom authentication form.
                #
                # We start off constructing the form without any data. We
                # don't want to prematurely trigger any validation for forms
                # that we won't end up using (even if it matches the current
                # hosting time, as we still don't know if we need to link or
                # re-authorize an account). We'll replace this with a populated
                # form further below.
                #
                # Note that we do still need the form instantiated here, for
                # template rendering.
                self.hosting_auth_forms[hosting_service.id] = \
                    auth_form_cls(hosting_service_cls=hosting_service,
                                  local_site=self.local_site,
                                  prefix=hosting_service.id)
            except Exception as e:
                logging.error('Error loading hosting service %s: %s'
                              % (hosting_service.id, e),
                              exc_info=1)

        for class_name, cls in six.iteritems(FAKE_HOSTING_SERVICES):
            if class_name not in hosting_services:
                service_info = self._get_hosting_service_info(cls, [])
                service_info['fake'] = True
                self.hosting_service_info[cls.hosting_service_id] = \
                    service_info

                hosting_service_choices.append((cls.hosting_service_id,
                                                cls.name))

        # Build the list of hosting service choices, sorted, with
        # "None" being first.
        hosting_service_choices.sort(key=lambda x: x[1])
        hosting_service_choices.insert(0, (self.NO_HOSTING_SERVICE_ID,
                                           self.NO_HOSTING_SERVICE_NAME))
        self.fields['hosting_type'].choices = hosting_service_choices

        # Now do the same for bug trackers, but have separate None and Custom
        # entries.
        bug_tracker_choices.sort(key=lambda x: x[1])
        bug_tracker_choices.insert(0, (self.NO_BUG_TRACKER_ID,
                                       self.NO_BUG_TRACKER_NAME))
        bug_tracker_choices.insert(1, (self.CUSTOM_BUG_TRACKER_ID,
                                       self.CUSTOM_BUG_TRACKER_NAME))
        self.fields['bug_tracker_type'].choices = bug_tracker_choices

        # Load the list of SCM tools.
        available_scmtools = set()
        scmtool_choices = []

        # Tools are referred to by their numeric ID. We keep track of the last
        # used ID and will use it to generate further IDs if fake SCMTools are
        # to be displayed.
        last_tool_pk = 0

        for tool in Tool.objects.order_by('pk'):
            scmtool_choices.append((tool.pk, tool.name))
            available_scmtools.add(tool.class_name)

            tool_fields = ['username', 'password']

            if tool.supports_raw_file_urls:
                tool_fields.append('raw_file_url')

            if tool.supports_ticket_auth:
                tool_fields.append('use_ticket_auth')

            self.tool_info[tool.id] = {
                'fields': tool_fields,
                'help_text': tool.field_help_text,
            }

            last_tool_pk = tool.pk

        for pk, (class_name, name) in enumerate(six.iteritems(FAKE_SCMTOOLS),
                                                start=last_tool_pk + 1):
            if class_name not in available_scmtools:
                scmtool_choices.append((pk, name))

                self.tool_info[six.text_type(pk)] = {
                    'fields': [],
                    'help_text': {},
                    'fake': True,
                }

        self.fields['tool'].choices = scmtool_choices

        # Get the current SSH public key that would be used for repositories,
        # if one has been created.
        self.ssh_client = SSHClient(namespace=self.local_site_name)
        ssh_key = self.ssh_client.get_user_key()

        if ssh_key:
            self.public_key = self.ssh_client.get_public_key(ssh_key)
            self.public_key_str = '%s %s' % (
                ssh_key.get_name(),
                ''.join(six.text_type(self.public_key).splitlines())
            )
        else:
            self.public_key = None
            self.public_key_str = ''

        # If no SSH key has been created, disable the key association field.
        if not self.public_key:
            self.fields['associate_ssh_key'].help_text = \
                self.NO_KEY_HELP_FMT % local_site_reverse(
                    'settings-ssh',
                    local_site_name=self.local_site_name)
            self.fields['associate_ssh_key'].widget.attrs['disabled'] = \
                'disabled'

        if self.instance:
            self._populate_repository_info_fields()
            self._populate_hosting_service_fields()
            self._populate_bug_tracker_fields()

    def _get_hosting_service_info(self, hosting_service, hosting_accounts):
        """Return the information for a hosting service.

        Arguments:
            hosting_service (type):
                The hosting service class, which should be a subclass of
                :py:class:`~reviewboard.hostingsvcs.service.HostingService`.

            hosting_accounts (list):
                A list of the registered
                `py:class:`~reviewboard.hostingsvcs.models.HostingServiceAccount`s

        Returns:
            dict:
            Information about the hosting service.
        """
        return {
            'scmtools': hosting_service.supported_scmtools,
            'plans': [],
            'planInfo': {},
            'self_hosted': hosting_service.self_hosted,
            'needs_authorization': hosting_service.needs_authorization,
            'supports_bug_trackers': hosting_service.supports_bug_trackers,
            'supports_ssh_key_association':
                hosting_service.supports_ssh_key_association,
            'supports_two_factor_auth':
                hosting_service.supports_two_factor_auth,
            'needs_two_factor_auth_code': False,
            'accounts': [
                {
                    'pk': account.pk,
                    'hosting_url': account.hosting_url,
                    'username': account.username,
                    'is_authorized': account.is_authorized,
                }
                for account in hosting_accounts
                if account.service_name == hosting_service.id
            ],
        }

    def _load_hosting_service(self, hosting_service_id, hosting_service,
                              plan_type_id, plan_type_label, form_class,
                              *args, **kwargs):
        """Loads a hosting service form.

        The form will be instantiated and added to the list of forms to be
        rendered, cleaned, loaded, and saved.
        """
        plan_info = {}

        if hosting_service.supports_repositories:
            form = form_class(self.data or None)
            self.repository_forms[hosting_service_id][plan_type_id] = form

            if self.instance:
                form.load(self.instance)

        if hosting_service.supports_bug_trackers:
            form = form_class(self.data or None, prefix='bug_tracker')
            self.bug_tracker_forms[hosting_service_id][plan_type_id] = form

            plan_info['bug_tracker_requires_username'] = \
                hosting_service.get_bug_tracker_requires_username(plan_type_id)

            if self.instance:
                form.load(self.instance)

        hosting_info = self.hosting_service_info[hosting_service_id]
        hosting_info['planInfo'][plan_type_id] = plan_info
        hosting_info['plans'].append({
            'type': plan_type_id,
            'label': six.text_type(plan_type_label),
        })

    def _populate_repository_info_fields(self):
        """Populates auxiliary repository info fields in the form.

        Most of the fields under "Repository Info" are core model fields. This
        method populates things which are stored into extra_data.
        """
        self.fields['use_ticket_auth'].initial = \
            self.instance.extra_data.get('use_ticket_auth', False)
        self.fields['password'].initial = self.instance.password

    def _populate_hosting_service_fields(self):
        """Populates all the main hosting service fields in the form.

        This populates the hosting service type and the repository plan
        on the form. These are only set if operating on an existing
        repository.
        """
        hosting_account = self.instance.hosting_account

        if hosting_account:
            service = hosting_account.service
            self.fields['hosting_type'].initial = \
                hosting_account.service_name

            if service.plans:
                self.fields['repository_plan'].choices = [
                    (plan_id, info['name'])
                    for plan_id, info in service.plans
                ]

                repository_plan = \
                    self.instance.extra_data.get('repository_plan', None)

                if repository_plan:
                    self.fields['repository_plan'].initial = repository_plan

    def _populate_bug_tracker_fields(self):
        """Populates all the main bug tracker fields in the form.

        This populates the bug tracker type, plan, and other fields
        related to the bug tracker on the form.
        """
        data = self.instance.extra_data
        bug_tracker_type = data.get('bug_tracker_type', None)

        if (data.get('bug_tracker_use_hosting', False) and
            self.instance.hosting_account):
            # The user has chosen to use the hosting service's bug tracker. We
            # only care about the checkbox. Don't bother populating the form.
            self.fields['bug_tracker_use_hosting'].initial = True
        elif bug_tracker_type == self.NO_BUG_TRACKER_ID:
            # Do nothing.
            return
        elif (bug_tracker_type is not None and
              bug_tracker_type != self.CUSTOM_BUG_TRACKER_ID):
            # A bug tracker service or custom bug tracker was chosen.
            service = get_hosting_service(bug_tracker_type)

            if not service:
                return

            self.fields['bug_tracker_type'].initial = bug_tracker_type
            self.fields['bug_tracker_hosting_url'].initial = \
                data.get('bug_tracker_hosting_url', None)
            self.fields['bug_tracker_hosting_account_username'].initial = \
                data.get('bug_tracker-hosting_account_username', None)

            if service.plans:
                self.fields['bug_tracker_plan'].choices = [
                    (plan_id, info['name'])
                    for plan_id, info in service.plans
                ]

                self.fields['bug_tracker_plan'].initial = \
                    data.get('bug_tracker_plan', None)
        elif self.instance.bug_tracker:
            # We have a custom bug tracker. There's no point in trying to
            # reverse-match it, because we can potentially be wrong when a
            # hosting service has multiple plans with similar bug tracker
            # URLs, so just show it raw. Admins can migrate it if they want.
            self.fields['bug_tracker_type'].initial = \
                self.CUSTOM_BUG_TRACKER_ID

    def _clean_hosting_info(self):
        """Clean the hosting service information.

        If using a hosting service, this will validate that the data
        provided is valid on that hosting service. Then it will create an
        account and link it, if necessary, with the hosting service.
        """
        hosting_type = self.cleaned_data['hosting_type']

        if hosting_type == self.NO_HOSTING_SERVICE_ID:
            self.data['hosting_account'] = None
            self.cleaned_data['hosting_account'] = None
            return

        # This should have been caught during validation, so we can assume
        # it's fine.
        hosting_service_cls = get_hosting_service(hosting_type)
        assert hosting_service_cls

        # Validate that the provided tool is valid for the hosting service.
        tool_name = self.cleaned_data['tool'].name

        if tool_name not in hosting_service_cls.supported_scmtools:
            self.errors['tool'] = self.error_class([
                _('This tool is not supported on the given hosting service')
            ])
            return

        # Get some more information about the hosting ser
        plan = self.cleaned_data['repository_plan'] or self.DEFAULT_PLAN_ID

        # Verify that any hosting account passed in is allowed to work with
        # this type of account.
        hosting_account = self.cleaned_data['hosting_account']

        if (hosting_account and
            (hosting_account.service_name != hosting_type or
             hosting_account.local_site != self.local_site)):
            self.errors['hosting_account'] = self.error_class([
                _('This account is not compatible with this hosting '
                  'service configuration.')
            ])
            return

        # If we don't yet have an account, or we have one but it needs to
        # be re-authorized, then we need to go through the entire account
        # updating and authorization process.
        force_authorize = self.cleaned_data['force_authorize']

        if (self.data and
            (not hosting_account or
             not hosting_account.is_authorized or force_authorize)):

            # Rebuild the authentication form, but with data provided to
            # this form, so that we can link or re-authorize an account.
            auth_form = self.hosting_auth_forms[hosting_type]

            auth_form = auth_form.__class__(
                data=self.data,
                prefix=auth_form.prefix,
                hosting_service_cls=auth_form.hosting_service_cls,
                hosting_account=hosting_account,
                local_site=auth_form.local_site)
            self.hosting_auth_forms[hosting_type] = auth_form

            if not auth_form.is_valid():
                # Copy any errors to the main form, so it'll fail validation
                # and inform the user.
                self.errors.update(auth_form.errors)
                return

            repository_extra_data = self._build_repository_extra_data(
                hosting_service_cls, hosting_type, plan)

            try:
                hosting_account = auth_form.save(
                    extra_authorize_kwargs=repository_extra_data,
                    force_authorize=force_authorize)
            except ValueError as e:
                # There was an error with a value provided to the form from
                # The user. Bubble this up.
                self.errors['hosting_account'] = \
                    self.error_class([six.text_type(e)])
                return
            except TwoFactorAuthCodeRequiredError as e:
                self.errors['hosting_account'] = \
                    self.error_class([six.text_type(e)])
                hosting_info = self.hosting_service_info[hosting_type]
                hosting_info['needs_two_factor_auth_code'] = True
                return
            except AuthorizationError as e:
                self.errors['hosting_account'] = self.error_class([
                    _('Unable to link the account: %s') % e,
                ])
                return
            except Exception as e:
                logging.exception('Unexpected error when linking hosting '
                                  'service account on %s: %s',
                                  hosting_type, e)

                self.errors['hosting_account'] = self.error_class([
                    _('Unknown error when linking the account: %s. The '
                      'details of the failure are in the Review Board log '
                      'file.')
                    % e,
                ])
                return

            # Flag that we've linked the account. If there are any
            # validation errors, and this flag is set, we tell the user
            # that we successfully linked and they don't have to do it
            # again.
            self.hosting_account_linked = True

            # Set this back in the form, so the rest of the form has access.
            self.data['hosting_account'] = hosting_account
            self.cleaned_data['hosting_account'] = hosting_account

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
        field_vars.update(hosting_account.data)

        try:
            self.cleaned_data.update(hosting_service_cls.get_repository_fields(
                username=hosting_account.username,
                hosting_url=hosting_account.hosting_url,
                plan=plan,
                tool_name=tool_name,
                field_vars=field_vars))
        except KeyError as e:
            raise ValidationError([six.text_type(e)])

    def _clean_bug_tracker_info(self):
        """Clean the bug tracker information.

        This will figure out the defaults for all the bug tracker fields,
        based on the stored bug tracker settings.
        """
        use_hosting = self.cleaned_data['bug_tracker_use_hosting']
        plan = self.cleaned_data['bug_tracker_plan'] or self.DEFAULT_PLAN_ID
        bug_tracker_type = self.cleaned_data['bug_tracker_type']
        bug_tracker_url = ''

        if use_hosting:
            # We're using the main repository form fields instead of the
            # custom bug tracker fields.
            hosting_type = self.cleaned_data['hosting_type']

            if hosting_type == self.NO_HOSTING_SERVICE_ID:
                self.errors['bug_tracker_use_hosting'] = self.error_class([
                    _('A hosting service must be chosen in order to use this')
                ])
                return

            plan = self.cleaned_data['repository_plan'] or self.DEFAULT_PLAN_ID
            hosting_service_cls = get_hosting_service(hosting_type)

            # We already validated server-side that the hosting service
            # exists.
            assert hosting_service_cls

            if (hosting_service_cls.supports_bug_trackers and
                self.cleaned_data.get('hosting_account')):
                # We have a valid hosting account linked up, so we can
                # process this and copy over the account information.
                form = self.repository_forms[hosting_type][plan]
                hosting_account = self.cleaned_data['hosting_account']

                new_data = self.cleaned_data.copy()
                new_data.update(form.cleaned_data)
                new_data.update(hosting_account.data)
                new_data['hosting_account_username'] = hosting_account.username
                new_data['hosting_url'] = hosting_account.hosting_url

                bug_tracker_url = hosting_service_cls.get_bug_tracker_field(
                    plan, new_data)
        elif bug_tracker_type == self.CUSTOM_BUG_TRACKER_ID:
            # bug_tracker_url should already be in cleaned_data.
            return
        elif bug_tracker_type != self.NO_BUG_TRACKER_ID:
            # We're using a bug tracker of a certain type. We need to
            # get the right data, strip the prefix on the forms, and
            # build the bug tracker URL from that.
            hosting_service_cls = get_hosting_service(bug_tracker_type)

            if not hosting_service_cls:
                self.errors['bug_tracker_type'] = self.error_class([
                    _('This bug tracker type is not supported')
                ])
                return

            form = self.bug_tracker_forms[bug_tracker_type][plan]

            new_data = {
                'hosting_account_username':
                    self.cleaned_data['bug_tracker_hosting_account_username'],
                'hosting_url':
                    self.cleaned_data['bug_tracker_hosting_url'],
            }

            if form.is_valid():
                # Strip the prefix from each bit of cleaned data in the form.
                for key, value in six.iteritems(form.cleaned_data):
                    key = key.replace(form.prefix, '')
                    new_data[key] = value

            bug_tracker_url = hosting_service_cls.get_bug_tracker_field(
                plan, new_data)

        self.cleaned_data['bug_tracker'] = bug_tracker_url
        self.data['bug_tracker'] = bug_tracker_url

    def full_clean(self, *args, **kwargs):
        extra_cleaned_data = {}
        extra_errors = {}
        required_values = {}

        # Save the required values for all native fields, so that we can
        # restore them we've changed the values and processed forms.
        for field in six.itervalues(self.fields):
            required_values[field] = field.required

        if self.data:
            hosting_type = self._get_field_data('hosting_type')
            hosting_service = get_hosting_service(hosting_type)
            repository_plan = (self._get_field_data('repository_plan') or
                               self.DEFAULT_PLAN_ID)

            bug_tracker_use_hosting = \
                self._get_field_data('bug_tracker_use_hosting')

            # If using the hosting service's bug tracker, we want to ignore
            # the bug tracker form (which will be hidden) and just use the
            # hosting service's form.
            if bug_tracker_use_hosting:
                bug_tracker_type = hosting_type
                bug_tracker_service = hosting_service
                bug_tracker_plan = repository_plan
            else:
                bug_tracker_type = self._get_field_data('bug_tracker_type')
                bug_tracker_service = get_hosting_service(bug_tracker_type)
                bug_tracker_plan = (self._get_field_data('bug_tracker_plan') or
                                    self.DEFAULT_PLAN_ID)

            self.fields['bug_tracker_type'].required = \
                not bug_tracker_use_hosting

            self.fields['path'].required = \
                (hosting_type == self.NO_HOSTING_SERVICE_ID)

            # The repository plan will only be listed if the hosting service
            # lists some plans. Otherwise, there's nothing to require.
            for service, field in ((hosting_service, 'repository_plan'),
                                   (bug_tracker_service, 'bug_tracker_plan')):
                self.fields[field].required = service and service.plans

                if service:
                    self.fields[field].choices = [
                        (id, info['name'])
                        for id, info in service.plans or []
                    ]

            self.fields['bug_tracker_plan'].required = (
                self.fields['bug_tracker_plan'].required and
                not bug_tracker_use_hosting)

            # We want to show this as required (in the label), but not
            # actually require, since we use a blank entry as
            # "Link new account."
            self.fields['hosting_account'].required = False

            # Only require the bug tracker username if the bug tracker field
            # requires the username.
            self.fields['bug_tracker_hosting_account_username'].required = \
                (not bug_tracker_use_hosting and
                 bug_tracker_service and
                 bug_tracker_service.get_bug_tracker_requires_username(
                     bug_tracker_plan))

            # Only require a URL if the bug tracker is self-hosted and
            # we're not using the hosting service's bug tracker.
            self.fields['bug_tracker_hosting_url'].required = (
                not bug_tracker_use_hosting and
                bug_tracker_service and
                bug_tracker_service.self_hosted)

            # Validate the custom forms and store any data or errors for later.
            custom_form_info = [
                (hosting_type, repository_plan, self.repository_forms),
            ]

            if not bug_tracker_use_hosting:
                custom_form_info.append((bug_tracker_type, bug_tracker_plan,
                                         self.bug_tracker_forms))

            for service_type, plan, form_list in custom_form_info:
                if service_type not in self.IGNORED_SERVICE_IDS:
                    form = form_list[service_type][plan]
                    form.is_bound = True

                    if form.is_valid():
                        extra_cleaned_data.update(form.cleaned_data)
                    else:
                        extra_errors.update(form.errors)
        else:
            # Validate every hosting service form and bug tracker form and
            # store any data or errors for later.
            for form_list in (self.repository_forms, self.bug_tracker_forms):
                for plans in six.itervalues(form_list):
                    for form in six.itervalues(plans):
                        if form.is_valid():
                            extra_cleaned_data.update(form.cleaned_data)
                        else:
                            extra_errors.update(form.errors)

        self.subforms_valid = not extra_errors

        super(RepositoryForm, self).full_clean(*args, **kwargs)

        if self.is_valid():
            self.cleaned_data.update(extra_cleaned_data)
        else:
            self.errors.update(extra_errors)

        # Undo the required settings above. Now that we're done with them
        # for validation, we want to fix the display so that users don't
        # see the required states change.
        for field, required in six.iteritems(required_values):
            field.required = required

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
        if not self.errors and self.subforms_valid:
            try:
                self.local_site = self.cleaned_data['local_site']

                if self.local_site:
                    self.local_site_name = self.local_site.name
            except LocalSite.DoesNotExist as e:
                raise ValidationError([e])

            self._clean_hosting_info()
            self._clean_bug_tracker_info()

            validate_review_groups(self)
            validate_users(self)

            # The clean/validation functions could create new errors, so
            # skip validating the repository path if everything else isn't
            # clean. Also skip in the case where the user is hiding the
            # repository.
            if (not self.errors and
                not self.cleaned_data['reedit_repository'] and
                self.cleaned_data.get('visible', True) and
                self.validate_repository):
                self._verify_repository_path()

            self._clean_ssh_key_association()

        return super(RepositoryForm, self).clean()

    def _clean_ssh_key_association(self):
        hosting_type = self.cleaned_data['hosting_type']
        hosting_account = self.cleaned_data['hosting_account']

        # Don't proceed if there are already errors, or if not using hosting
        # (hosting type and account should be clean by this point)
        if (self.errors or hosting_type == self.NO_HOSTING_SERVICE_ID or
            not hosting_account):
            return

        hosting_service_cls = get_hosting_service(hosting_type)
        hosting_service = hosting_service_cls(hosting_account)

        # Check the requirements for SSH key association. If the requirements
        # are not met, do not proceed.
        if (not hosting_service_cls.supports_ssh_key_association or
            not self.cleaned_data['associate_ssh_key'] or
            not self.public_key):
            return

        if not self.instance.extra_data:
            # The instance is either a new repository or a repository that
            # was previously configured without a hosting service. In either
            # case, ensure the repository is fully initialized.
            repository = self.save(commit=False)
        else:
            repository = self.instance

        key = self.ssh_client.get_user_key()

        try:
            # Try to upload the key if it hasn't already been associated.
            if not hosting_service.is_ssh_key_associated(repository, key):
                hosting_service.associate_ssh_key(repository, key)
        except SSHKeyAssociationError as e:
            logging.warning('SSHKeyAssociationError for repository "%s" (%s)'
                            % (repository, e.message))
            raise ValidationError([
                _('Unable to associate SSH key with your hosting service. '
                  'This is most often the result of a problem communicating '
                  'with the hosting service. Please try again later or '
                  'manually upload the SSH key to your hosting service.')
            ])

    def clean_path(self):
        return self.cleaned_data['path'].strip()

    def clean_mirror_path(self):
        return self.cleaned_data['mirror_path'].strip()

    def clean_password(self):
        return self.cleaned_data['password'].strip()

    def clean_bug_tracker_base_url(self):
        return self.cleaned_data['bug_tracker_base_url'].rstrip('/')

    def clean_bug_tracker_hosting_url(self):
        """Validates that the bug tracker hosting url is valid.

        Note that bug tracker hosting url is whatever the bug hosting form
        (e.g BugzillaForm) specifies.

        cleaned_data['bug_tracker_hosting_url'] refers to a specific field
        in bug tracker description that only GitLab uses, and has quite a
        misleading name. It will not contain the base URL of the bug tracker
        in other cases.
        """
        bug_tracker_use_hosting = self.cleaned_data['bug_tracker_use_hosting']
        if not bug_tracker_use_hosting:
            bug_tracker_type = self.cleaned_data['bug_tracker_type']

            # If the validator exception was thrown, the form will
            # have at least one error present in the errors object. If errors
            # were detected, set an appropriate variable that is_valid()
            # method will check.
            if bug_tracker_type in self.bug_tracker_forms:
                field = self.bug_tracker_forms[bug_tracker_type].get('default')
                if field:
                    self.bug_tracker_host_error = (
                        hasattr(field, 'errors') and
                        len(field.errors) > 0)

        return self.cleaned_data['bug_tracker_hosting_url'].strip()

    def clean_hosting_type(self):
        """Validates that the hosting type represents a valid hosting service.

        This won't do anything if no hosting service is used.
        """
        hosting_type = self.cleaned_data['hosting_type']

        if hosting_type != self.NO_HOSTING_SERVICE_ID:
            hosting_service = get_hosting_service(hosting_type)

            if not hosting_service:
                raise ValidationError([_('Not a valid hosting service')])

        return hosting_type

    def clean_bug_tracker_type(self):
        """Validates that the bug tracker type represents a valid hosting
        service.

        This won't do anything if no hosting service is used.
        """
        bug_tracker_type = (self.cleaned_data['bug_tracker_type'] or
                            self.NO_BUG_TRACKER_ID)

        if bug_tracker_type not in self.IGNORED_SERVICE_IDS:
            hosting_service = get_hosting_service(bug_tracker_type)

            if (not hosting_service or
                not hosting_service.supports_bug_trackers):
                raise ValidationError([_('Not a valid hosting service')])

        return bug_tracker_type

    def clean_tool(self):
        """Checks the SCMTool used for this repository for dependencies.

        If one or more dependencies aren't found, they will be presented
        as validation errors.
        """
        errors = []
        tool = get_object_or_none(Tool, pk=self.cleaned_data['tool'])

        if not tool:
            raise ValidationError(['Invalid SCMTool.'])

        scmtool_class = tool.get_scmtool_class()

        for dep in scmtool_class.dependencies.get('modules', []):
            if not has_module(dep):
                errors.append(_('The Python module "%s" is not installed. '
                                'You may need to restart the server '
                                'after installing it.') % dep)

        for dep in scmtool_class.dependencies.get('executables', []):
            if not is_exe_in_path(dep):
                if sys.platform == 'win32':
                    exe_name = '%s.exe' % dep
                else:
                    exe_name = dep

                errors.append(_('The executable "%s" is not in the path.')
                              % exe_name)

        if errors:
            raise ValidationError(errors)

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
                not self.bug_tracker_host_error and
                not self.cleaned_data['reedit_repository'] and
                self.subforms_valid and
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
        repository.extra_data = {}

        bug_tracker_use_hosting = self.cleaned_data['bug_tracker_use_hosting']

        hosting_type = self.cleaned_data['hosting_type']
        service = get_hosting_service(hosting_type)

        if service:
            repository.username = ''
            repository.password = ''

            repository.extra_data.update({
                'repository_plan': self.cleaned_data['repository_plan'],
                'bug_tracker_use_hosting': bug_tracker_use_hosting,
            })

            if service.self_hosted:
                repository.extra_data['hosting_url'] = \
                    repository.hosting_account.hosting_url
        else:
            repository.username = self.cleaned_data['username'] or ''
            repository.password = self.cleaned_data['password'] or ''

        if self.cert:
            repository.extra_data['cert'] = self.cert

        if repository.tool.supports_ticket_auth:
            try:
                repository.extra_data['use_ticket_auth'] = \
                    self.cleaned_data['use_ticket_auth']
            except KeyError:
                pass

        if hosting_type in self.repository_forms:
            plan = (self.cleaned_data['repository_plan'] or
                    self.DEFAULT_PLAN_ID)
            self.repository_forms[hosting_type][plan].save(repository)

        if not bug_tracker_use_hosting:
            bug_tracker_type = self.cleaned_data['bug_tracker_type']

            if bug_tracker_type in self.bug_tracker_forms:
                plan = (self.cleaned_data['bug_tracker_plan'] or
                        self.DEFAULT_PLAN_ID)
                self.bug_tracker_forms[bug_tracker_type][plan].save(repository)
                repository.extra_data.update({
                    'bug_tracker_type': bug_tracker_type,
                    'bug_tracker_plan': plan,
                })

                bug_tracker_service = get_hosting_service(bug_tracker_type)
                assert bug_tracker_service

                if bug_tracker_service.self_hosted:
                    repository.extra_data['bug_tracker_hosting_url'] = \
                        self.cleaned_data['bug_tracker_hosting_url']

                if bug_tracker_service.get_bug_tracker_requires_username(plan):
                    repository.extra_data.update({
                        'bug_tracker-hosting_account_username':
                            self.cleaned_data[
                                'bug_tracker_hosting_account_username'],
                    })

        if commit:
            repository.save()

        return repository

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

        hosting_type = self.cleaned_data['hosting_type']
        hosting_service_cls = get_hosting_service(hosting_type)
        hosting_service = None
        plan = None

        if hosting_service_cls:
            hosting_service = hosting_service_cls(
                self.cleaned_data['hosting_account'])

            if hosting_service:
                plan = (self.cleaned_data['repository_plan'] or
                        self.DEFAULT_PLAN_ID)

        repository_extra_data = self._build_repository_extra_data(
            hosting_service, hosting_type, plan)

        while 1:
            # Keep doing this until we have an error we don't want
            # to ignore, or it's successful.
            try:
                if hosting_service:
                    hosting_service.check_repository(
                        path=path,
                        username=username,
                        password=password,
                        scmtool_class=scmtool_class,
                        tool_name=tool.name,
                        local_site_name=self.local_site_name,
                        plan=plan,
                        **repository_extra_data)
                else:
                    scmtool_class.check_repository(path, username, password,
                                                   self.local_site_name)

                # Success.
                break
            except BadHostKeyError as e:
                if self.cleaned_data['trust_host']:
                    try:
                        self.ssh_client.replace_host_key(e.hostname,
                                                         e.raw_expected_key,
                                                         e.raw_key)
                    except IOError as e:
                        raise ValidationError(e)
                else:
                    self.hostkeyerror = e
                    break
            except UnknownHostKeyError as e:
                if self.cleaned_data['trust_host']:
                    try:
                        self.ssh_client.add_host_key(e.hostname, e.raw_key)
                    except IOError as e:
                        raise ValidationError(e)
                else:
                    self.hostkeyerror = e
                    break
            except UnverifiedCertificateError as e:
                if self.cleaned_data['trust_host']:
                    try:
                        self.cert = scmtool_class.accept_certificate(
                            path,
                            username=username,
                            password=password,
                            local_site_name=self.local_site_name,
                            certificate=e.certificate)
                    except IOError as e:
                        raise ValidationError(e)
                else:
                    self.certerror = e
                    break
            except AuthenticationError as e:
                if 'publickey' in e.allowed_types and e.user_key is None:
                    self.userkeyerror = e
                    break

                raise ValidationError(e)
            except Exception as e:
                try:
                    text = six.text_type(e)
                except UnicodeDecodeError:
                    text = six.text_type(e, 'ascii', 'replace')

                if isinstance(e, HostingServiceError) and e.help_link:
                    text = format_html(_('{0} <a href="{1}">{2}</a>'),
                                       text, e.help_link, e.help_link_text)

                raise ValidationError(text)

    def _build_repository_extra_data(self, hosting_service, hosting_type,
                                     plan):
        """Builds extra repository data to pass to HostingService functions."""
        repository_extra_data = {}

        if hosting_service and hosting_type in self.repository_forms:
            repository_extra_data = \
                self.repository_forms[hosting_type][plan].cleaned_data

        return repository_extra_data

    def _get_field_data(self, field):
        return self[field].data or self.fields[field].initial

    class Meta:
        model = Repository
        widgets = {
            'path': forms.TextInput(attrs={'size': '60'}),
            'mirror_path': forms.TextInput(attrs={'size': '60'}),
            'raw_file_url': forms.TextInput(attrs={'size': '60'}),
            'bug_tracker': forms.TextInput(attrs={'size': '60'}),
            'name': forms.TextInput(attrs={'size': '30',
                                           'autocomplete': 'off'}),
            'username': forms.TextInput(attrs={'size': '30',
                                               'autocomplete': 'off'}),
            'review_groups': FilteredSelectMultiple(
                _('review groups with access'), False),
        }
