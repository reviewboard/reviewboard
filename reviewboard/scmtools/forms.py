from __future__ import unicode_literals

import logging
import sys
from itertools import chain

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import Select, model_to_dict
from django.utils import six
from django.utils.datastructures import MultiValueDict
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext, ugettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.filesystem import is_exe_in_path

from reviewboard.admin.form_widgets import (RelatedGroupWidget,
                                            RelatedUserWidget)
from reviewboard.admin.import_utils import has_module
from reviewboard.admin.validation import validate_bug_tracker
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            SSHKeyAssociationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.fake import FAKE_HOSTING_SERVICES
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (get_hosting_services,
                                             get_hosting_service)
from reviewboard.reviews.models import Group
from reviewboard.scmtools.errors import (AuthenticationError,
                                         RepositoryNotFoundError,
                                         SCMError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.fake import FAKE_SCMTOOLS
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.mixins import LocalSiteAwareModelFormMixin
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import (BadHostKeyError,
                                    SSHError,
                                    UnknownHostKeyError)


logger = logging.getLogger(__name__)


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


class BaseRepositorySubForm(forms.Form):
    """A sub-form used in the main repository configuration form.

    This provides some standard functionality for collecting information
    needed to configure a specific type of repository (one backed by a
    particular :py:class:`~reviewboard.scmtools.core.SCMTool` or
    :py:class:`~reviewboard.hostingsvcs.service.HostingService`). It takes
    care of basic form customization and loading, and must be subclassed for
    other operations.

    Third-parties will never need to subclass this directly. Instead, subclass
    one of:

    * :py:class:`~reviewboard.hostingsvcs.forms.HostingServiceForm`
    * :py:class:`~reviewboard.hostingsvcs.forms.HostingServiceAuthForm`

    Forms can provide a :py:class:`Meta` class that define
    :py:attr:`Meta.help_texts` and :py:attr:`Meta.labels` attributes. Each is
    a dictionary mapping field names to new content for those fields. See the
    classes above for examples.

    Version Added:
        3.0.16

    Attributes:
        local_site (reviewboard.site.models.LocalSite):
            The :term:`Local Site` that any queries or state should be bound
            to.

        repository (reviewboard.scmtools.models.Repository):
            The repository being configured. This is allowed to be ``None``,
            mainly for testing purposes, but will always have a value when
            constructed by :py:class:`RepositoryForm`.
    """

    # Turn off client-side validation, performing validation only server-side.
    use_required_attribute = False

    def __init__(self, *args, **kwargs):
        """Initialize the form.

        Subclasses should use this to alter the fields shown in the form, if
        needed.

        Args:
            *args (tuple):
                Additional positional arguments for the parent form.

            **kwargs (dict):
                Additional keyword arguments for the parent form.

        Keyword Args:
            repository (reviewboard.scmtools.models.Repository, optional):
                The repository that's being created or updated. This is
                allowed to be ``None``, mainly for testing purposes, but will
                always have a value when constructed by
                :py:class:`RepositoryForm`.

            local_site (reviewboard.site.models.LocalSite, optional):
                The :term:`Local Site` that any queries or state should be
                bound to.
        """
        # Pull these out of kwargs so that we can preserve *args calls
        # without problems.
        self.repository = kwargs.pop('repository', None)
        self.local_site = kwargs.pop('local_site', None)

        super(BaseRepositorySubForm, self).__init__(*args, **kwargs)

        # Allow the subclass to override help text and field labels.
        meta = getattr(self, 'Meta', None)

        if meta is not None:
            help_texts = getattr(meta, 'help_texts', {})
            labels = getattr(meta, 'labels', {})

            for field_name, help_text in six.iteritems(help_texts):
                self.fields[field_name].help_text = help_text

            for field_name, label in six.iteritems(labels):
                self.fields[field_name].label = label

    def get_initial_data(self):
        """Return initial data for the form.

        By default, this doesn't return any initial data. Subclasses can
        override this to return something suitable for the form.

        Generally, sensitive information, like passwords, should not be
        provided.

        Returns:
            dict:
            Initial data for the form.
        """
        return {}

    def load(self):
        """Load information for the form.

        By default, this will populate initial values returned in
        :py:meth:`get_initial_data`. Subclasses can override this to set
        other fields or state as needed.
        """
        for key, value in six.iteritems(self.get_initial_data()):
            self.fields[key].initial = value

    def save(self):
        """Save information from the form.

        Subclasses must override this.
        """
        raise NotImplementedError

    def get_field_data_from(self, obj, field_names=None, model_fields=None,
                            norm_key_func=None):
        """Return data from an object for use in the form's fields.

        This is a utility method that helps load in field data based on the
        attributes on an object and the object's ``extra_data`` field. It's
        most commonly going to be used for a subclass's :py:meth:`load` or
        :py:meth:`get_initial_data`.

        Args:
            obj (django.db.models.Model):
                The model object to load data from. This is expected to have
                an ``extra_data`` field.

            field_names (list of unicode, optional):
                A specific list of field names to load from the object. If
                not provided, this defaults to the form's list of field names.
                These do not all have to be present in the object.

            model_fields (set of unicode, optional):
                Names of fields that should be loaded directly from attributes
                on ``obj``, instead of the object's ``extra_data``.

            norm_key_func (callable, optional):
                A function that normalizes a key before looking up in the
                object's ``extra_data``. If not provided, this defaults to
                :py:meth:`~django.forms.forms.BaseForm.add_prefix`.

        Returns:
            dict:
            The loaded field data.
        """
        data = {}
        model_fields = set(model_fields or [])

        if field_names is None:
            field_names = six.iterkeys(self.fields)

        if norm_key_func is None:
            norm_key_func = self.add_prefix

        for key in field_names:
            if key in model_fields:
                data[key] = getattr(obj, key)
            else:
                norm_key = norm_key_func(key)

                if norm_key in obj.extra_data:
                    data[key] = obj.extra_data[norm_key]

        return data


class BaseRepositoryAuthSubForm(BaseRepositorySubForm):
    """Base class for any repository authentication forms.

    Third-parties will never need to subclass this directly. Instead, subclass
    one of:

    * :py:class:`~reviewboard.hostingsvcs.forms.HostingServiceAuthForm`
    * :py:class:`~reviewboard.scmtools.forms.BaseSCMToolAuthForm`
    """


class BaseRepositoryInfoSubForm(BaseRepositorySubForm):
    """Base class for any repository information forms.

    Third-parties will never need to subclass this directly. Instead, subclass
    one of:

    * :py:class:`~reviewboard.hostingsvcs.forms.HostingServiceForm`
    * :py:class:`~reviewboard.scmtools.forms.BaseSCMToolRepositoryForm`
    """


class SCMToolSubFormMixin(object):
    """Mixin class for SCMTool-specific subforms.

    This should only be used internally. SCMTools will want to subclass
    :py:class:`BaseSCMToolAuthForm`, :py:class:`BaseSCMToolRepositoryForm`,
    or one of their descendents.

    Version Added:
        3.0.16

    Attributes:
        scmtool_cls (type):
            The :py:class:`~reviewboard.scmtools.core.SCMTool` subclass used
            for this form.
    """

    #: A set of fields to save directly to the Repository model.
    #:
    #: This should only be set by internal classes.
    _MODEL_FIELDS = set()

    #: A set of fields to save in extra_data without an SCMTool ID prefix.
    #:
    #: This exists for backwards-compatibility with older configuration,
    #: and should only be set by internal classes.
    _PREFIXLESS_KEYS = set()

    def __init__(self, **kwargs):
        """Initialize the form.

        Subclasses should use this to alter the fields shown in the form, if
        needed, but not to set initial form field values from the repository,
        as those will be overridden.

        Args:
            **kwargs (dict):
                Additional keyword arguments for the parent form.

        Keyword Args:
            scmtool_cls (type):
                The subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`
                that this form represents.
        """
        scmtool_cls = kwargs.pop('scmtool_cls')
        self.scmtool_cls = scmtool_cls

        super(SCMToolSubFormMixin, self).__init__(**kwargs)

        for name, help_text in six.iteritems(scmtool_cls.field_help_text):
            if name in self.fields:
                self.fields[name].help_text = help_text

    def get_initial_data(self):
        """Return initial data for the form.

        This will load information from the repository's attributes and
        :py:attr:`~reviewboard.scmtools.models.Repository.extra_data` into the
        form's fields.

        Returns:
            dict:
            Initial data for the form.
        """
        def _norm_key(key):
            if key in self._PREFIXLESS_KEYS:
                return key

            return self.addprefix(key)

        return self.get_field_data_from(self.repository,
                                        model_fields=self._MODEL_FIELDS,
                                        norm_key_func=_norm_key)

    def save(self):
        """Save information to the repository.

        This will store the content of the fields in the repository.

        Subclasses will generally not need to override this.
        """
        repository = self.repository
        assert repository is not None

        for key, value in six.iteritems(self.cleaned_data):
            if key in self._MODEL_FIELDS:
                setattr(repository, key, value)
            elif key in self._PREFIXLESS_KEYS:
                repository.extra_data[key] = value
            else:
                repository.extra_data[self.add_prefix(key)] = value

    def __repr__(self):
        """Return a string representation of the form.

        Args:
            unicode:
            The string representation.
        """
        return '<%s (scmtool=%s)>' % (type(self).__name__,
                                      self.scmtool_cls.scmtool_id)


class BaseSCMToolAuthForm(SCMToolSubFormMixin, BaseRepositoryAuthSubForm):
    """Base class for SCMTool authentication forms.

    This is a blank form that can be subclassed and populated with fields for
    requesting authentication credentials for plain repositories.

    Any cleaned data fields named ``username`` or ``password`` will be set
    directly on the equivalent
    :py:class:`~reviewboard.scmtools.models.Repository` model fields.  Any
    other fields will be stored in :py:attr:`Repository.extra_data
    <reviewboard.scmtools.models.Repository.extra_data>`, using a key in the
    form of :samp:`<scmtoolid>_<fieldname>`.

    If an SCMTool uses a standard username/password, they're most likely
    going to want to use :py:class:`StandardSCMToolAuthForm` directly or as
    a parent class.

    Version Added:
        3.0.16
    """

    _MODEL_FIELDS = {'username', 'password'}


class BaseSCMToolRepositoryForm(SCMToolSubFormMixin,
                                BaseRepositoryInfoSubForm):
    """Base class for SCMTool repository forms.

    This is a blank form that can be subclassed and populated with fields for
    requesting information for plain repositories.

    Subclasses are required to provide a :guilabel:`Path` field, or to at least
    provide a suitable value in the cleaned data based on other fields.

    Any cleaned data fields named ``path``, ``mirror_path``, or
    ``raw_file_url`` will be set directly on the equivalent
    :py:class:`~reviewboard.scmtools.models.Repository` model fields. Any
    other fields will be stored in :py:attr:`Repository.extra_data
    <reviewboard.scmtools.models.Repository.extra_data>`, using a key in the
    form of :samp:`<scmtoolid>_<fieldname>`. The exception is the field
    ``use_ticket_auth``, which will be stored without an SCMTool ID prefix for
    legacy reasons.

    If an SCMTool wants to provide standard path/mirror path fields, they're
    most likely going to want to use :py:class:`StandardSCMToolRepositoryForm`
    directly or as a parent class.

    Version Added:
        3.0.16
    """

    _MODEL_FIELDS = {'path', 'mirror_path', 'raw_file_url'}
    _PREFIXLESS_KEYS = {'use_ticket_auth'}


class StandardSCMToolAuthForm(BaseSCMToolAuthForm):
    """A standard SCMTool authentication form.

    This provides standard :guilabel:`Username` and :guilabel:`Password`
    fields. These are optional by default. Subclasses can override them to make
    the fields required, remove them, or add additional authentication-related
    fields.

    See the documentation on the :py:class:`parent class <BaseSCMToolAuthForm>`
    to see how field data is stored.

    Version Added:
        3.0.16
    """

    username = forms.CharField(
        max_length=Repository._meta.get_field('username').max_length,
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'size': '30',
        }))

    password = forms.CharField(
        label=_('Password'),
        required=False,
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                'autocomplete': 'off',
                'size': '30',
            }))

    def clean_username(self):
        """Clean the username field.

        This will strip all whitespace from the field before returning it.

        Returns:
            unicode:
            The value provided in the field, with whitespace stripped.
        """
        return self.cleaned_data['username'].strip()

    def clean_password(self):
        """Clean the password field.

        This will strip all whitespace from the field before returning it.

        Returns:
            unicode:
            The value provided in the field, with whitespace stripped.
        """
        return self.cleaned_data['password'].strip()


class StandardSCMToolRepositoryForm(BaseSCMToolRepositoryForm):
    """A standard SCMTool repository form.

    This provides standard :guilabel:`Path` and :guilabel:`Mirror Path` fields,
    as well as optional fields for :guilabel:`Raw File URL Mask` (if
    :py:class:`SCMTool.raw_file_url
    <reviewboard.scmtools.core.SCMTool.supports_raw_file_urls>` is set) and
    :guilabel:`Use ticket-based authentication` <if
    :py:class:`SCMTool.raw_file_url
    <reviewboard.scmtools.core.SCMTool.supports_ticket_auth>` is set). These
    two optional fields are provided for legacy purposes, but will be removed
    in the future, so subclasses should explicitly provide them if needed.

    Subclasses can override any of the form's fields, remove them, or add
    additional fields needed to identify repositories.

    If a :guilabel:`Path` field is not appropriate for the type of repository,
    then it's still up to the subclass to provide a suitable ``path`` value
    in the cleaned data that uniquely identifies the repository.

    See the documentation on the :py:class:`parent class
    <BaseSCMToolRepositoryForm>` to see how field data is stored.

    Version Added:
        3.0.16
    """

    path = forms.CharField(
        label=_('Path'),
        max_length=Repository._meta.get_field('path').max_length,
        widget=forms.TextInput(attrs={'size': 60}))

    mirror_path = forms.CharField(
        label=_('Mirror Path'),
        required=False,
        max_length=Repository._meta.get_field('mirror_path').max_length,
        widget=forms.TextInput(attrs={'size': 60}))

    raw_file_url = forms.CharField(
        label=_('Raw File URL Mask'),
        max_length=Repository._meta.get_field('raw_file_url').max_length,
        required=False,
        widget=forms.TextInput(attrs={'size': 60}),
        help_text=_("A URL mask used to check out a particular revision of a "
                    "file using HTTP. This is needed for repository types "
                    "that can't access remote files natively. "
                    "Use <tt>&lt;revision&gt;</tt> and "
                    "<tt>&lt;filename&gt;</tt> in the URL in place of the "
                    "revision and filename parts of the path."))

    use_ticket_auth = forms.BooleanField(
        label=_('Use ticket-based authentication'),
        initial=False,
        required=False)

    def __init__(self, **kwargs):
        """Initialize the form.

        This will set the appropriate fields on the form based on the
        capabilities on the :py:class:`~reviewboard.scmtools.core.SCMTool`,
        as per the class's documentation.

        Args:
            **kwargs (dict):
                Additional keyword arguments for the parent form.
        """
        super(StandardSCMToolRepositoryForm, self).__init__(**kwargs)

        if not self.scmtool_cls.supports_raw_file_urls:
            del self.fields['raw_file_url']

        if not self.scmtool_cls.supports_ticket_auth:
            del self.fields['use_ticket_auth']

    def clean_path(self):
        """Clean the Path field.

        This will strip all whitespace from the field before returning it.

        Returns:
            unicode:
            The value provided in the field, with whitespace stripped.
        """
        path = self.cleaned_data['path'].strip()

        if not path:
            raise ValidationError(ugettext('Repository path cannot be empty'))

        return path

    def clean_mirror_path(self):
        """Clean the Mirror Path field.

        This will strip all whitespace from the field before returning it.

        Returns:
            unicode:
            The value provided in the field, with whitespace stripped.
        """
        return self.cleaned_data['mirror_path'].strip()

    def clean_raw_file_url(self):
        """Clean the Raw File URL Mask field.

        This will strip all whitespace from the field before returning it.

        Returns:
            unicode:
            The value provided in the field, with whitespace stripped.
        """
        return self.cleaned_data['raw_file_url'].strip()


class RepositoryForm(LocalSiteAwareModelFormMixin, forms.ModelForm):
    """A form for creating and updating repositories.

    This form provides an interface for creating and updating repositories,
    handling the association with hosting services, linking accounts,
    dealing with SSH keys and SSL certificates, and more.

    Configuration details are collected primarily through subforms provided
    by SCMTools and Hosting Services.
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

    _SCMTOOL_PREFIXLESS_FIELDS = (BaseSCMToolAuthForm._MODEL_FIELDS |
                                  BaseSCMToolAuthForm._PREFIXLESS_KEYS |
                                  BaseSCMToolRepositoryForm._MODEL_FIELDS |
                                  BaseSCMToolRepositoryForm._PREFIXLESS_KEYS)

    # Turn off client-side validation, performing validation only server-side.
    use_required_attribute = False

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
        queryset=(
            HostingServiceAccount.objects
            .accessible(filter_local_site=False)
        ),
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

    # Access control fields
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=_('Users with access'),
        required=False,
        widget=RelatedUserWidget())

    review_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(visible=True).order_by('name'),
        label=_('Groups with access'),
        required=False,
        widget=RelatedGroupWidget(invite_only=True))

    def __init__(self, data=None, *args, **kwargs):
        """Initialize the repository configuration form.

        This will set up the initial state for the form, locating any
        tools and hosting services that can be shown and setting up the
        configuration and authentication forms they provide.

        Args:
            data (dict, optional):
                The posted form data.

            *args (tuple):
                Positional arguments to pass to the parent class.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        from reviewboard.hostingsvcs.forms import HostingServiceAuthForm

        # Django's admin UI will pass RepositoryForm an immutable QueryDict
        # as the POST data. This normally makes sense for 99.9% of forms, but
        # this form is a bit special.
        #
        # Certain fields need to be updated when we calculate some data so
        # that we can set better defaults if the form doesn't fully save. For
        # instance, if we successfully link a new account but fail to validate
        # a repository, we want the default account to be the newly-linked
        # account, and this requires being able to modify self.data.
        if isinstance(data, MultiValueDict):
            data = data.dict()

        super(RepositoryForm, self).__init__(data, *args, **kwargs)

        self.hostkeyerror = None
        self.certerror = None
        self.userkeyerror = None
        self.form_validation_error = None

        self.hosting_account_linked = False
        self.hosting_bug_tracker_forms = {}
        self.hosting_auth_forms = {}
        self.hosting_repository_forms = {}
        self.hosting_service_info = {}

        self.tool_models_by_id = {}
        self.scmtool_auth_forms = {}
        self.scmtool_repository_forms = {}
        self.scmtool_info = {}

        self.subforms_cleaned_data = None
        self.subforms_errors = None
        self.subforms_valid = False

        self.cert = None

        # Create some aliases for the current Local Site and name handled by
        # the LocalSiteAwareModelFormMixin. This may be a Local Site bound to
        # the form or one specified in form data (in which case it would have
        # already been checked for access rights).
        if self.cur_local_site is not None:
            self.local_site = self.cur_local_site
        else:
            self.local_site = None

        # Grab the entire list of HostingServiceAccounts that can be
        # used by this form. When the form is actually being used by the
        # user, the listed accounts will consist only of the ones available
        # for the selected hosting service.
        #
        # These will be fed into auth forms. We don't modify the queryset here,
        # since the LocalSiteAwareModelFormMixin will manage that for us.
        hosting_accounts = list(
            HostingServiceAccount.objects
            .accessible(local_site=self.cur_local_site)
        )

        # Standard forms don't support 'instance', so don't pass it through
        # to any created hosting service forms.
        if 'instance' in kwargs:
            kwargs.pop('instance')

        # Set some fields based on the instance. We only want to work with
        # fields here that aren't dependent on any loaded hosting service or
        # SCMTool forms or state.
        instance = self.instance
        cur_hosting_service_cls = None

        if instance:
            cur_scmtool_cls = instance.scmtool_class
            cur_hosting_service_cls = type(instance.hosting_service)

            if cur_scmtool_cls is not None:
                self.fields['tool'].initial = cur_scmtool_cls.scmtool_id

            self._populate_hosting_service_fields()
            self._populate_bug_tracker_fields()

            # If the repository is public, but has access lists set (which
            # could happen prior to 3.0.16 if setting an access list and then
            # unchecking the Public Access checkbox), make sure we're not
            # reflecting those access lists here in the UI so there isn't any
            # confusion when toggling that checkbox. We want them to start
            # fresh.
            #
            # Saving will also clear out any access lists if set to public.
            if instance.public:
                # Note that because we loaded from an instance, the populated
                # values are in self.initial and not in field.initial.
                self.initial['users'] = []
                self.initial['review_groups'] = []

        # Load the list of repository forms and hosting services.
        hosting_service_choices = []
        bug_tracker_choices = []

        hosting_services = set()

        for hosting_service in get_hosting_services():
            if (not hosting_service.visible and
                hosting_service is not cur_hosting_service_cls):
                # We don't want to show this service as an option.
                continue

            hosting_service_id = hosting_service.hosting_service_id
            class_name = '%s.%s' % (hosting_service.__module__,
                                    hosting_service.__name__)
            hosting_services.add(class_name)

            auth_form_cls = hosting_service.auth_form or HostingServiceAuthForm

            if hosting_service.supports_repositories:
                hosting_service_choices.append(
                    (hosting_service_id, hosting_service.name)
                )

            if hosting_service.supports_bug_trackers:
                bug_tracker_choices.append(
                    (hosting_service_id, hosting_service.name)
                )

            self.hosting_bug_tracker_forms[hosting_service_id] = {}
            self.hosting_repository_forms[hosting_service_id] = {}
            self.hosting_service_info[hosting_service_id] = \
                self._get_hosting_service_info(
                    hosting_service=hosting_service,
                    hosting_accounts=hosting_accounts,
                    is_instance_service=(hosting_service is
                                         cur_hosting_service_cls))

            try:
                if hosting_service.plans:
                    for type_id, info in hosting_service.plans:
                        form = info.get('form', None)

                        if form:
                            self._load_hosting_service(
                                hosting_service_id=hosting_service_id,
                                hosting_service=hosting_service,
                                plan_type_id=type_id,
                                plan_type_label=info['name'],
                                form_class=form)
                elif hosting_service.form:
                    self._load_hosting_service(
                        hosting_service_id=hosting_service_id,
                        hosting_service=hosting_service,
                        plan_type_id=self.DEFAULT_PLAN_ID,
                        plan_type_label=self.DEFAULT_PLAN_NAME,
                        form_class=hosting_service.form)

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
                self.hosting_auth_forms[hosting_service_id] = \
                    auth_form_cls(hosting_service_cls=hosting_service,
                                  repository=instance,
                                  local_site=self.local_site,
                                  prefix=hosting_service_id)
            except Exception as e:
                logging.exception('Error loading hosting service %s: %s',
                                  hosting_service_id, e)

        for class_name, cls in six.iteritems(FAKE_HOSTING_SERVICES):
            if class_name not in hosting_services:
                service_info = self._get_hosting_service_info(cls)
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
        hosting_type_value = self['hosting_type'].value()
        tool_value = self['tool'].value()

        for tool in Tool.objects.all():
            try:
                scmtool_cls = tool.scmtool_class
            except Exception as e:
                # The SCMTool registration exists in the database, but might
                # not be installed anymore. Skip it.
                logger.exception('Unable to load SCMTool "%s" (ID %s) for '
                                 'repository form: %s',
                                 tool.class_name, tool.pk, e)
                continue

            scmtool_id = tool.scmtool_id
            is_tool_active = (tool_value == scmtool_id and
                              hosting_type_value == self.NO_HOSTING_SERVICE_ID)

            try:
                self._load_scmtool(scmtool_cls=scmtool_cls,
                                   is_active=is_tool_active)
            except Exception as e:
                logging.exception('Error loading SCMTool %s: %s',
                                  tool.class_name, e)
                continue

            self.tool_models_by_id[scmtool_id] = tool
            self.scmtool_info[scmtool_id] = self._get_scmtool_info(scmtool_cls)
            scmtool_choices.append((scmtool_id, tool.name))
            available_scmtools.add(scmtool_id)

        # Create placeholders for any SCMTools we want to list that aren't
        # currently installed.
        for scmtool_id, name in six.iteritems(FAKE_SCMTOOLS):
            if scmtool_id not in available_scmtools:
                scmtool_choices.append((scmtool_id, name))
                self.scmtool_info[scmtool_id] = {
                    'name': name,
                    'fake': True,
                }

        scmtool_choices.sort(key=lambda x: x[1])
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

        # Set a label for the "public" checkbox that better describes its
        # impact on the repository, given the settings on the server or
        # Local Site.
        if instance:
            instance_local_site = self.local_site or instance.local_site
        else:
            instance_local_site = self.local_site

        if instance_local_site and not instance_local_site.public:
            public_label = (ugettext('Accessible to all users on %s')
                            % instance_local_site.name)
            public_help_text = (
                ugettext(
                    'Review requests and files on this repository will be '
                    'visible to anyone on %s. Uncheck this box to grant '
                    'access only to specific users and/or to users who are '
                    'members of specific invite-only review groups.')
                % instance_local_site.name)
        elif not instance_local_site or instance_local_site.public:
            siteconfig = SiteConfiguration.objects.get_current()

            if siteconfig.get('auth_require_sitewide_login'):
                public_label = ugettext('Accessible to all logged-in users')
                public_help_text = ugettext(
                    'Review requests and files on this repository will be '
                    'visible to any logged-in users. Uncheck this box to '
                    'grant access only to specific users and/or to users '
                    'who are members of specific invite-only review groups.')
            else:
                public_label = ugettext('Accessible to everyone')
                public_help_text = ugettext(
                    'Review requests and files on this repository will be '
                    'visible to any anonymous or logged-in users. Uncheck '
                    'this box to grant access only to specific users and/or '
                    'to users who are members of specific invite-only '
                    'review groups.')

        self.fields['public'].label = public_label
        self.fields['public'].help_text = public_help_text

    @property
    def local_site_name(self):
        """The name of the current Local Site for this form.

        This will be ``None`` if no Local Site is assigned.
        """
        if self.local_site is None:
            return None

        return self.local_site.name

    def iter_subforms(self, bound_only=False, with_auth_forms=False):
        """Iterate through all subforms matching the given criteria.

        This allows callers to easily retrieve all the subforms available
        to the repository form, optionally limiting those to subforms with
        data bound.

        By default, this does not include authentication forms, as those are
        treated specially and should generally not be operated upon in the
        same way as repository and bug tracker subforms.

        The defaults may change, so callers should be explicit about the
        results they want.

        Args:
            bound_only (bool, optional):
                Whether to limit results to bound subforms (those that have
                been populated with data from a form submission).

            with_auth_forms (bool, optional):
                Whether to include authentication forms in the results.

        Yields:
            django.forms.Form:
            Each subform matching the criteria.
        """
        subform_lists = []

        if with_auth_forms:
            subform_lists += [
                six.itervalues(self.scmtool_auth_forms),
                six.itervalues(self.hosting_auth_forms),
            ]

        subform_lists.append(six.itervalues(self.scmtool_repository_forms))
        subform_lists += [
            six.itervalues(plan_forms)
            for plan_forms in chain(
                six.itervalues(self.hosting_repository_forms),
                six.itervalues(self.hosting_bug_tracker_forms))
        ]

        subforms = chain.from_iterable(subform_lists)

        if bound_only:
            subforms = (
                subform
                for subform in subforms
                if subform.is_bound
            )

        return subforms

    def get_repository_already_exists(self):
        """Return whether a repository with these details already exists.

        This will validate the form before returning a result. Callers are
        encouraged to call :py:meth:`is_valid` themselves before calling this.

        Returns:
            bool:
            ``True`` if a repository already exists with this name or path.
            ``False`` if one does not exist.
        """
        if self.is_valid():
            return False

        return (
            Repository.NAME_CONFLICT_ERROR in self.errors.get('name', []) or
            Repository.PATH_CONFLICT_ERROR in self.errors.get('path', [])
        )

    def _get_scmtool_info(self, scmtool_cls):
        """Return the information for a SCMTool.

        Args:
            scmtool_cls (type):
                The SCMTool class, which should be a subclass of
                :py:class:`~reviewboard.scmtools.core.SCMTool`.

        Returns:
            dict:
            Information about the SCMTool.
        """
        info = {}

        for attr in ('name',
                     'supports_pending_changesets',
                     'supports_post_commit'):
            info[attr] = getattr(scmtool_cls, attr)

        return info

    def _get_hosting_service_info(self, hosting_service, hosting_accounts=[],
                                  is_instance_service=False):
        """Return the information for a hosting service.

        Args:
            hosting_service (type):
                The hosting service class, which should be a subclass of
                :py:class:`~reviewboard.hostingsvcs.service.HostingService`.

            hosting_accounts (list of reviewboard.hostingsvcs.models.
                              HostingServiceAccount, optional):
                A list of the registered
                :py:class:`~reviewboard.hostingsvcs.models.
                HostingServiceAccount`s.

            is_active (boolean, optional):
                Whether this hosting service is currently active, based on
                an existing repository being configured.

        Returns:
            dict:
            Information about the hosting service.
        """
        visible_scmtools = hosting_service.visible_scmtools

        if visible_scmtools is None:
            # visible_scmtools will be None if it just supports all SCMTools.
            # This is a design quirk that works around lack of classproperties,
            # which we'd otherwise use to alias supported_scmtools by default.
            scmtools = hosting_service.supported_scmtools
        elif (is_instance_service and
              self.instance.scmtool_class is not None and
              visible_scmtools != hosting_service.supported_scmtools):
            # Some supported SCMTools aren't shown by default. Want to show
            # only the visible SCMTools, plus whichever one this repository
            # is currently backed by (which likely has only legacy support).
            scmtools = (visible_scmtools +
                        [self.instance.scmtool_class.scmtool_id])
        else:
            scmtools = visible_scmtools

        return {
            'scmtools': sorted(scmtools),
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
                if account.service_name == hosting_service.hosting_service_id
            ],
        }

    def _load_scmtool(self, scmtool_cls, is_active):
        """Load forms for a SCMTool.

        This will construct and store the authentication and repository
        information forms. If this is the active SCMTool for the repository,
        then the forms will be loaded with the current data either passed
        to the main form or from the state in the current repository.

        Args:
            scmtool_cls (type):
                The subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`
                that owns these forms.

            is_active (bool):
                Whether this is the active SCMTool for the repository. This
                is only set if working with a plain repository, not one
                backed by a hosting service.
        """
        repository = self.instance
        scmtool_id = scmtool_cls.scmtool_id
        form_kwargs = {
            'local_site': self.local_site,
            'prefix': scmtool_id,
            'repository': repository,
        }

        if is_active:
            initial = model_to_dict(
                repository,
                fields=BaseSCMToolRepositoryForm._MODEL_FIELDS)
            form_kwargs['initial'] = initial

            if self.data:
                data = self.data.copy()

                # We might get form data without prefixes for some fields, such
                # as "path". While the repository page itself will send data
                # with prefixed keys, API consumers and those automating the
                # repository page won't. Look for those keys and convert them
                # to prefixed versions.
                #
                # We'll prioritize any bound form data, and will fall back to
                # initial data if not otherwise found. This ensures we have
                # values for fields like 'path' and 'mirror_path' included.
                for key in self._SCMTOOL_PREFIXLESS_FIELDS:
                    prefixed_key = '%s-%s' % (scmtool_id, key)

                    if not data.get(prefixed_key):
                        if key in data:
                            value = data.pop(key)
                        elif key in initial:
                            value = initial[key]
                        else:
                            continue

                        data[prefixed_key] = value

                form_kwargs['data'] = data

        auth_form = scmtool_cls.create_auth_form(**form_kwargs)
        repo_form = scmtool_cls.create_repository_form(**form_kwargs)

        if is_active:
            auth_form.load()
            repo_form.load()

        # Store these last, in case one of the forms raises an exception.
        # want consistent state.
        self.scmtool_auth_forms[scmtool_id] = auth_form
        self.scmtool_repository_forms[scmtool_id] = repo_form

    def _load_hosting_service(self, hosting_service_id, hosting_service,
                              plan_type_id, plan_type_label, form_class):
        """Load a hosting service form.

        The form will be instantiated and added to the list of forms to be
        rendered, cleaned, loaded, and saved.

        Args:
            hosting_service_id (unicode):
                The ID of the hosting service to load.

            hosting_service (type):
                The hosting service class. This will be a subclass of
                :py:class:`~reviewboard.hostingsvcs.service.HostingService`.

            plan_type_id (unicode):
                The ID of the hosting plan pertaining to the forms to load.

            plan_type_label (unicode):
                The label shown for the hosting plan.

            form_class (type):
                The hosting service form to use for this plan. This will be
                a subclass of
                :py:class:`~reviewboard.hostingsvcs.forms.HostingServiceForm`.
        """
        repository = self.instance
        plan_info = {}

        if hosting_service.supports_repositories:
            # We only want to load repository data into the form if it's meant
            # for this form. Check the hosting service ID and plan against
            # what's in the submitted form data.
            if (self.data and
                self.data.get('hosting_type') == hosting_service_id and
                (not hosting_service.plans or
                 self.data.get('repository_plan') == plan_type_id)):
                repo_form_data = self.data
            else:
                repo_form_data = None

            form = form_class(data=repo_form_data,
                              repository=repository,
                              hosting_service_cls=hosting_service,
                              local_site=self.local_site)
            self.hosting_repository_forms[hosting_service_id][plan_type_id] = \
                form

            if self.instance:
                form.load(repository)

        if hosting_service.supports_bug_trackers:
            # We only want to load repository data into the form if it's meant
            # for this form. Check the hosting service ID and plan against
            # what's in the submitted form data.
            if (self.data and
                self.data.get('bug_tracker_type') == hosting_service_id and
                not self.data.get('bug_tracker_use_hosting', False) and
                (not hosting_service.plans or
                 self.data.get('bug_tracker_plan') == plan_type_id)):
                bug_tracker_form_data = self.data
            else:
                bug_tracker_form_data = None

            form = form_class(data=bug_tracker_form_data,
                              repository=repository,
                              hosting_service_cls=hosting_service,
                              local_site=self.local_site,
                              prefix='bug_tracker')
            plan_forms = self.hosting_bug_tracker_forms[hosting_service_id]
            plan_forms[plan_type_id] = form

            plan_info['bug_tracker_requires_username'] = \
                hosting_service.get_bug_tracker_requires_username(plan_type_id)

            if self.instance:
                form.load(repository)

        hosting_info = self.hosting_service_info[hosting_service_id]
        hosting_info['planInfo'][plan_type_id] = plan_info
        hosting_info['plans'].append({
            'type': plan_type_id,
            'label': six.text_type(plan_type_label),
        })

    def _populate_hosting_service_fields(self):
        """Populates all the main hosting service fields in the form.

        This populates the hosting service type and the repository plan
        on the form. These are only set if operating on an existing
        repository.
        """
        # NOTE: This method *cannot* access anything in the loaded forms or
        #       hosting_service_info attributes.
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
        # NOTE: This method *cannot* access anything in the loaded forms or
        #       hosting_service_info attributes.
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
        tool = self.cleaned_data['tool']
        scmtool_id = tool.scmtool_id

        if (tool.name not in hosting_service_cls.supported_scmtools and
            scmtool_id not in hosting_service_cls.supported_scmtools):
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
                repository=self.instance,
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
                    force_authorize=force_authorize,
                    trust_host=self.cleaned_data['trust_host'])
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
            except UnverifiedCertificateError as e:
                self.certerror = e
                return
            except Exception as e:
                error = six.text_type(e)

                if error.endswith('.'):
                    error = error[:-1]

                self.errors['hosting_account'] = self.error_class([
                    _('Unexpected error when linking the account: %s. '
                      'Additional details may be found in the Review Board '
                      'log file.')
                    % error,
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
        repository_form = self.hosting_repository_forms[hosting_type][plan]
        field_vars = repository_form.cleaned_data.copy()
        field_vars.update(self.cleaned_data)
        field_vars.update(hosting_account.data)

        try:
            self.subforms_cleaned_data.update(
                hosting_service_cls.get_repository_fields(
                    username=hosting_account.username,
                    hosting_url=hosting_account.hosting_url,
                    plan=plan,
                    tool_name=tool.name,
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
                form = self.hosting_repository_forms[hosting_type][plan]

                if not form.is_valid():
                    # Skip the rest of this. There's no sense building a URL if
                    # the form's going to display errors.
                    return

                hosting_account = self.cleaned_data['hosting_account']

                new_data = self.cleaned_data.copy()
                new_data.update(form.cleaned_data)
                new_data.update(hosting_account.data)
                new_data['hosting_account_username'] = hosting_account.username
                new_data['hosting_url'] = hosting_account.hosting_url

                try:
                    bug_tracker_url = \
                        hosting_service_cls.get_bug_tracker_field(plan,
                                                                  new_data)
                except KeyError as e:
                    raise ValidationError([six.text_type(e)])
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

            form = self.hosting_bug_tracker_forms[bug_tracker_type][plan]

            if not form.is_valid():
                # Skip the rest of this. There's no sense building a URL if
                # the form's going to display errors.
                return

            new_data = dict({
                key: self.cleaned_data['bug_tracker_%s' % key]
                for key in ('hosting_account_username', 'hosting_url')
            }, **{
                # Strip the prefix from each bit of cleaned data in the form.
                key.replace(form.prefix, ''): value
                for key, value in six.iteritems(form.cleaned_data)
            })

            try:
                bug_tracker_url = hosting_service_cls.get_bug_tracker_field(
                    plan, new_data)
            except KeyError as e:
                raise ValidationError([six.text_type(e)])

        self.cleaned_data['bug_tracker'] = bug_tracker_url
        self.data['bug_tracker'] = bug_tracker_url

    def full_clean(self, *args, **kwargs):
        subforms_cleaned_data = {}
        subforms_errors = {}
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
            with_auth_forms = (hosting_type == self.NO_HOSTING_SERVICE_ID)

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
        else:
            with_auth_forms = True

        # Validate the subforms that the repository form is currently working
        # with, and store any data or errors for later.
        #
        # Note that we're not going to validate hosting service authentication
        # forms, which is why we compute with_auth_forms above based on
        # whether a hosting service is selected. We handle those specially in
        # _clean_hosting_info().
        for subform in self.iter_subforms(bound_only=bool(self.data),
                                          with_auth_forms=with_auth_forms):
            if subform.is_valid():
                subforms_cleaned_data.update(subform.cleaned_data)
            else:
                subforms_errors.update(subform.errors)

        self.subforms_cleaned_data = subforms_cleaned_data
        self.subforms_errors = subforms_errors
        self.subforms_valid = not subforms_errors

        super(RepositoryForm, self).full_clean(*args, **kwargs)

        if self.is_valid():
            self.cleaned_data.update(subforms_cleaned_data)
        else:
            self.errors.update(subforms_errors)

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
        try:
            if not self.errors and self.subforms_valid:
                if not self.limited_to_local_site:
                    try:
                        self.local_site = self.cleaned_data['local_site']
                    except LocalSite.DoesNotExist as e:
                        raise ValidationError(six.text_type(e))

                self._clean_hosting_info()
                self._clean_bug_tracker_info()

                # The clean/validation functions could create new errors, so
                # skip validating the repository path if everything else isn't
                # clean. Also skip in the case where the user is hiding the
                # repository.
                if (not self.errors and
                    not self.cleaned_data['reedit_repository'] and
                    self.cleaned_data.get('visible', True)):
                    try:
                        self._verify_repository_path()
                    except ValidationError as e:
                        # We may not be re-raising this exception, which would
                        # cause the exception to be stored in the attribute
                        # in the parent try/except handler. We still want to
                        # store it, so just do that explicitly here.
                        self.form_validation_error = e

                        if e.code == 'cert_unverified':
                            self.certerror = e.params['exception']
                        elif e.code in ('host_key_invalid',
                                        'host_key_unverified'):
                            self.hostkeyerror = e.params['exception']
                        elif e.code == 'missing_ssh_key':
                            self.userkeyerror = e.params['exception']
                        else:
                            raise

                self._clean_ssh_key_association()

                if self.cleaned_data['public']:
                    # Clear out any access lists that may have been set
                    # before. This ensures we don't run into trouble saving
                    # repositories later if a removed user remains in a list.
                    self.cleaned_data.update({
                        'review_groups': [],
                        'users': [],
                    })

            if self.certerror:
                # In the case where there's a certificate error on a hosting
                # service, we'll bail out of the validation process before
                # computing any of the derived fields (like path). This results
                # in the "I trust this host" prompt being shown at the top, but
                # a spurious "Please correct the error below" error shown when
                # no errors are visible. We therefore want to clear out the
                # errors and let the certificate error show on its own. If the
                # user then chooses to trust the cert, the regular verification
                # will run its course.
                self.errors.clear()

            return super(RepositoryForm, self).clean()
        except ValidationError as e:
            # Store this so that the true cause of any ValidationError
            # terminating form cleaning can be looked up. Note that in newer
            # versions of Django, this information is available natively.
            self.form_validation_error = e
            raise

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

    def clean_bug_tracker_base_url(self):
        return self.cleaned_data['bug_tracker_base_url'].rstrip('/')

    def clean_bug_tracker_hosting_url(self):
        """Clean the bug tracker hosting URL.

        This will strip all whitespace from the URL.

        Returns:
            unicode:
            The hosting URL with whitespace stripped.
        """
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
        """Check the SCMTool used for this repository.

        This will ensure the selected SCMTool is valid and that its
        dependencies all exist.

        Returns:
            reviewboard.scmtools.models.Tool:
            The Tool model entry to assign to the repository.

        Raises:
            django.core.exceptions.ValidationError:
                The tool was invalid, or one of its dependencies was missing.
        """
        errors = []
        scmtool_id = self.cleaned_data['tool']

        try:
            tool = self.tool_models_by_id[scmtool_id]
        except KeyError:
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

    def clean_extra_data(self):
        """Clean the extra_data field.

        This will ensure that the field is always a dictionary.

        Returns:
            dict:
            The extra_data dictionary.

        Raises:
            django.core.exceptions.ValidationError:
                The value was not a dictionary.
        """
        extra_data = self.cleaned_data['extra_data'] or {}

        if not isinstance(extra_data, dict):
            raise ValidationError(ugettext(
                'This must be a JSON object/dictionary.'))

        return extra_data

    def is_valid(self):
        """Return whether or not the form is valid.

        This will return True if the form fields are all valid, if there's
        no certificate error, host key error, and if the form isn't
        being re-displayed after canceling an SSH key or HTTPS certificate
        verification.

        This also takes into account the validity of any relevant subforms.

        Returns:
            bool:
            ``True`` if the form is valid. ``False`` if it is not.
        """
        return (super(RepositoryForm, self).is_valid() and
                not self.hostkeyerror and
                not self.certerror and
                not self.userkeyerror and
                not self.cleaned_data['reedit_repository'] and
                self.subforms_valid)

    def save(self, commit=True):
        """Save the repository.

        This will save some of the general information for the repository and
        the hosting service (if selected), and use the subforms to save the
        rest.

        This must be called after :py:meth:`is_valid`.

        Args:
            commit (bool, optional):
                Whether to save the repository to the database.

                If ``False``, the repository will be constructed but not saved.
                It is then the responsibility of the caller to call
                :py:meth:`Repository.save()
                <reviewboard.scmtools.models.Repository.save>` and
                :py:meth:`save_m2m`.

        Returns:
            reviewboard.scmtools.models.Repository:
            The resulting repository.

        Raises:
            ValueError:
                The form had pending errors, and could not be saved.
        """
        # Before we make any changes, we want to see if the hosting service
        # or SCMTool have changed. These will determine whether we need to
        # clear out some old extra_data state.
        old_hosting_service = self.instance.hosting_service
        old_scmtool_cls = self.instance.scmtool_class

        extra_data = self.cleaned_data['extra_data']
        hosting_type = self.cleaned_data['hosting_type']
        tool = self.cleaned_data['tool']
        scmtool_id = tool.scmtool_id
        repository_plan = self.cleaned_data.get('repository_plan')
        bug_tracker_plan = self.cleaned_data.get('bug_tracker_plan')

        extra_data_prefixes_to_remove = ['bug_tracker_', 'bug_tracker-']

        if old_hosting_service is not None:
            old_hosting_type = old_hosting_service.hosting_service_id
            old_repository_plan = \
                self.instance.extra_data.get('repository_plan')

            if (hosting_type != old_hosting_type or
                repository_plan != old_repository_plan):
                extra_data_prefixes_to_remove.append('%s_' % old_hosting_type)

        if old_scmtool_cls is not None:
            old_scmtool_id = old_scmtool_cls.scmtool_id

            if old_scmtool_id != scmtool_id:
                extra_data_prefixes_to_remove.append('%s_' % old_scmtool_id)

        # Start removing the keys we don't want.
        for key in ('cert',
                    'hosting_url',
                    'repository_plan',
                    'use_ticket_auth'):
            extra_data.pop(key, None)

        extra_data_prefixes_to_remove = tuple(extra_data_prefixes_to_remove)

        if extra_data_prefixes_to_remove:
            for key in list(six.iterkeys(extra_data)):
                if key.startswith(extra_data_prefixes_to_remove):
                    del extra_data[key]

        # We can now start populating the repository's fields.
        repository = super(RepositoryForm, self).save(commit=False)
        repository.tool = tool
        repository.path = self.cleaned_data['path']
        repository.mirror_path = self.cleaned_data.get('mirror_path', '')
        repository.raw_file_url = self.cleaned_data.get('raw_file_url', '')

        bug_tracker_use_hosting = self.cleaned_data['bug_tracker_use_hosting']

        if hosting_type == self.NO_HOSTING_SERVICE_NAME:
            service = None
        else:
            service = get_hosting_service(hosting_type)

        if service is not None:
            repository.username = ''
            repository.password = ''

            repository.extra_data.update({
                'repository_plan': repository_plan,
                'bug_tracker_use_hosting': bug_tracker_use_hosting,
            })

            if service.self_hosted:
                repository.extra_data['hosting_url'] = \
                    repository.hosting_account.hosting_url

            if hosting_type in self.hosting_repository_forms:
                plan = repository_plan or self.DEFAULT_PLAN_ID
                self.hosting_repository_forms[hosting_type][plan].save(
                    repository)
        else:
            self.scmtool_auth_forms[scmtool_id].save()
            self.scmtool_repository_forms[scmtool_id].save()

        if self.cert:
            repository.extra_data['cert'] = self.cert

        if not bug_tracker_use_hosting:
            bug_tracker_type = self.cleaned_data['bug_tracker_type']

            if bug_tracker_type in self.hosting_bug_tracker_forms:
                plan = bug_tracker_plan or self.DEFAULT_PLAN_ID
                self.hosting_bug_tracker_forms[bug_tracker_type][plan].save(
                    repository)
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
            self.save_m2m()

        return repository

    def _verify_repository_path(self):
        """Verify the repository path to check if it's valid.

        This will check if the repository exists and is accessible, and
        confirm whether the SSH key or HTTPS certificate needs to be manually
        verified by the administrator.

        Raises:
            django.core.exceptions.ValidationError:
                The repository information fails to pass validation. Details
                and explicit error codes will be in the exception.
        """
        tool = self.cleaned_data.get('tool')

        if not tool:
            # This failed validation earlier, so bail.
            return

        scmtool_class = tool.get_scmtool_class()
        subforms_cleaned_data = self.subforms_cleaned_data
        path = subforms_cleaned_data.get('path')
        username = subforms_cleaned_data.get('username')
        password = subforms_cleaned_data.get('password')
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
        else:
            # For plain repositories, a SCMTool can specify that it prefers
            # using a Mirror Path instead of a Path for all communication and
            # repository validation. This is available for historical reasons.
            # We'll check for that only if we're not using a hosting service
            # (which should have its own custom repository checks).
            if scmtool_class.prefers_mirror_path:
                path = subforms_cleaned_data.get('mirror_path') or path

        if not path:
            # This may have been caught during form validation, but it depends
            # on the subform, so check again.
            self._errors['path'] = self.error_class([
                ugettext('The repository path cannot be empty')
            ])
            return

        repository_extra_data = self._build_repository_extra_data(
            hosting_service, hosting_type, plan)

        local_site_name = self.local_site_name

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
                        local_site_name=local_site_name,
                        plan=plan,
                        **repository_extra_data)
                else:
                    scmtool_class.check_repository(path, username, password,
                                                   local_site_name)

                # Success.
                break
            except RepositoryNotFoundError as e:
                raise ValidationError(six.text_type(e),
                                      code='repository_not_found')
            except BadHostKeyError as e:
                if not self.cleaned_data['trust_host']:
                    raise ValidationError(
                        six.text_type(e),
                        code='host_key_invalid',
                        params={
                            'exception': e,
                        })

                try:
                    self.ssh_client.replace_host_key(e.hostname,
                                                     e.raw_expected_key,
                                                     e.raw_key)
                except IOError as e:
                    raise ValidationError(six.text_type(e),
                                          code='replace_host_key_failed')
            except UnknownHostKeyError as e:
                if not self.cleaned_data['trust_host']:
                    raise ValidationError(
                        six.text_type(e),
                        code='host_key_unverified',
                        params={
                            'exception': e,
                        })

                try:
                    self.ssh_client.add_host_key(e.hostname, e.raw_key)
                except IOError as e:
                    raise ValidationError(six.text_type(e),
                                          code='add_host_key_failed')
            except UnverifiedCertificateError as e:
                if not self.cleaned_data['trust_host']:
                    raise ValidationError(
                        six.text_type(e),
                        code='cert_unverified',
                        params={
                            'exception': e,
                        })

                try:
                    self.cert = scmtool_class.accept_certificate(
                        path,
                        username=username,
                        password=password,
                        local_site_name=local_site_name,
                        certificate=e.certificate)
                except IOError as e:
                    raise ValidationError(six.text_type(e),
                                          code='accept_cert_failed')
            except AuthenticationError as e:
                if 'publickey' in e.allowed_types and e.user_key is None:
                    raise ValidationError(
                        six.text_type(e),
                        code='missing_ssh_key',
                        params={
                            'exception': e,
                        })

                raise ValidationError(six.text_type(e),
                                      code='repo_auth_failed')
            except Exception as e:
                logging.exception(
                    'Unexpected exception while verifying repository path for '
                    'hosting service %r using plan %r and tool %r: %s',
                    hosting_service, plan, tool, e)

                try:
                    text = six.text_type(e)
                except UnicodeDecodeError:
                    text = six.text_type(e, 'ascii', 'replace')

                if isinstance(e, HostingServiceError):
                    code = 'unexpected_hosting_service_failure'
                elif isinstance(e, SSHError):
                    code = 'unexpected_ssh_failure'
                elif isinstance(e, SCMError):
                    code = 'unexpected_scm_failure'
                else:
                    code = 'unexpected_failure'

                if getattr(e, 'help_link', None):
                    text = format_html(_('{0} <a href="{1}">{2}</a>'),
                                       text, e.help_link,
                                       e.help_link_text)

                raise ValidationError(text, code=code)

    def _build_repository_extra_data(self, hosting_service, hosting_type,
                                     plan):
        """Builds extra repository data to pass to HostingService functions."""
        repository_extra_data = {}

        if hosting_service and hosting_type in self.hosting_repository_forms:
            repository_extra_data = \
                self.hosting_repository_forms[hosting_type][plan].cleaned_data

        return repository_extra_data

    def _get_field_data(self, field):
        return self[field].data or self.fields[field].initial

    class Meta:
        model = Repository
        widgets = {
            'bug_tracker': forms.TextInput(attrs={'size': '60'}),
            'name': forms.TextInput(attrs={'size': '30',
                                           'autocomplete': 'off'}),
            'review_groups': FilteredSelectMultiple(
                _('review groups with access'), False),
        }
        fields = '__all__'
        exclude = ('username', 'password', 'path', 'mirror_path',
                   'raw_file_url', 'tool')
