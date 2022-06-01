"""Administration form for authentication settings."""

import logging

from django import forms
from django.utils.translation import gettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.accounts.forms.auth import LegacyAuthModuleSettingsForm
from reviewboard.admin.siteconfig import load_site_config


logger = logging.getLogger(__name__)


class AuthenticationSettingsForm(SiteSettingsForm):
    """Authentication settings for Review Board.

    Attributes:
        auth_backend_forms (dict):
            A mapping of authentication backend IDs to settings form
            instances.
    """

    CUSTOM_AUTH_ID = 'custom'
    CUSTOM_AUTH_CHOICE = (CUSTOM_AUTH_ID, _('Legacy Authentication Module'))

    auth_anonymous_access = forms.BooleanField(
        label=_('Allow anonymous read-only access'),
        help_text=_('If checked, users will be able to view review requests '
                    'and diffs without logging in.'),
        required=False)

    auth_backend = forms.ChoiceField(
        label=_('Authentication Method'),
        choices=(),
        help_text=_('The method Review Board should use for authenticating '
                    'users.'),
        required=True,
        widget=forms.Select(attrs={
            'data-subform-group': 'auth-backend',
        }))

    def __init__(self, siteconfig, *args, **kwargs):
        """Initialize the settings form.

        This will load the list of available authentication backends and
        their settings forms, allowing the browser to show the appropriate
        settings form based on the selected backend.

        Args:
            siteconfig (djblets.siteconfig.models.SiteConfiguration):
                The site configuration handling the server's settings.

            *args (tuple):
                Additional positional arguments for the parent class.

            **kwargs (dict):
                Additional keyword arguments for the parent class.
        """
        super(AuthenticationSettingsForm, self).__init__(siteconfig,
                                                         *args, **kwargs)

        from reviewboard.accounts.backends import auth_backends

        self.auth_backend_forms = {}

        cur_auth_backend = (self['auth_backend'].data or
                            self.fields['auth_backend'].initial)

        if cur_auth_backend == self.CUSTOM_AUTH_ID:
            custom_auth_form = LegacyAuthModuleSettingsForm(siteconfig,
                                                            *args, **kwargs)
        else:
            custom_auth_form = LegacyAuthModuleSettingsForm(siteconfig)

        self.auth_backend_forms[self.CUSTOM_AUTH_ID] = custom_auth_form

        backend_choices = []
        builtin_auth_choice = None

        for backend in auth_backends:
            backend_id = backend.backend_id

            try:
                if backend.settings_form:
                    if cur_auth_backend == backend_id:
                        backend_form = backend.settings_form(siteconfig,
                                                             *args, **kwargs)
                    else:
                        backend_form = backend.settings_form(siteconfig)

                    self.auth_backend_forms[backend_id] = backend_form
                    backend_form.load()

                choice = (backend_id, backend.name)

                if backend_id == 'builtin':
                    builtin_auth_choice = choice
                else:
                    backend_choices.append(choice)
            except Exception as e:
                logger.exception('Error loading authentication backend %s: %s',
                                 backend_id, e)

        backend_choices.sort(key=lambda x: x[1])
        backend_choices.insert(0, builtin_auth_choice)
        backend_choices.append(self.CUSTOM_AUTH_CHOICE)
        self.fields['auth_backend'].choices = backend_choices

        from reviewboard.accounts.sso.backends import sso_backends

        self.sso_backend_forms = {}

        form_fields = self.Meta.fieldsets[0]['fields']

        for backend in sso_backends:
            backend_id = backend.backend_id

            if backend.settings_form:
                field_id = '%s_enabled' % backend_id

                try:
                    available, reason = backend.is_available()
                except Exception as e:
                    available = False
                    reason = str(e)

                self.fields[field_id] = forms.BooleanField(
                    label=_('Enable %s Authentication') % backend.name,
                    disabled=not available,
                    help_text=reason or '',
                    required=False)

                if field_id not in form_fields:
                    form_fields.append(field_id)

                form = backend.settings_form(siteconfig, *args, **kwargs)
                form.load()
                self.sso_backend_forms[backend_id] = form

        self.load()

    def load(self):
        """Load settings from the form.

        This will populate initial fields based on the site configuration.
        """
        super(AuthenticationSettingsForm, self).load()

        self.fields['auth_anonymous_access'].initial = \
            not self.siteconfig.get('auth_require_sitewide_login')

    def save(self):
        """Save the form.

        This will write the new configuration to the database. It will then
        force a site configuration reload.
        """
        self.siteconfig.set('auth_require_sitewide_login',
                            not self.cleaned_data['auth_anonymous_access'])

        auth_backend = self.cleaned_data['auth_backend']

        if auth_backend in self.auth_backend_forms:
            self.auth_backend_forms[auth_backend].save()

        for form, enable_field_id in self._iter_sso_backend_forms():
            if self[enable_field_id].data:
                form.save()

        super(AuthenticationSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    def is_valid(self):
        """Return whether the form is valid.

        This will check the validity of the fields on this form and on
        the selected authentication backend's settings form.

        Returns:
            bool:
            ``True`` if the main settings form and authentication backend's
            settings form is valid. ``False`` if either form is invalid.
        """
        if not super(AuthenticationSettingsForm, self).is_valid():
            return False

        backend_id = self.cleaned_data['auth_backend']
        backend_form = self.auth_backend_forms[backend_id]

        if not backend_form.is_valid():
            return False

        for form, enable_field_id in self._iter_sso_backend_forms():
            if (self.cleaned_data[enable_field_id] and
                not form.is_valid()):
                return False

        return True

    def full_clean(self):
        """Clean and validate all form fields.

        This will clean and validate both this form and the selected
        authentication backend's settings form (or all settings forms, if this
        form has not been POSTed to).

        Raises:
            django.core.exceptions.ValidationError:
                One or more fields failed validation.
        """
        super(AuthenticationSettingsForm, self).full_clean()

        if self.data:
            # Note that this isn't validated yet, but that's okay given our
            # usage. It's a bit of a hack though.
            auth_backend = (self['auth_backend'].data or
                            self.fields['auth_backend'].initial)

            if auth_backend in self.auth_backend_forms:
                self.auth_backend_forms[auth_backend].full_clean()

            for form, enable_field_id in self._iter_sso_backend_forms():
                if (self[enable_field_id].data or
                    self.fields[enable_field_id].initial):
                    form.full_clean()
        else:
            for form in self.auth_backend_forms.values():
                form.full_clean()

            for form in self.sso_backend_forms.values():
                form.full_clean()

    def _iter_sso_backend_forms(self):
        """Yield the SSO backend forms.

        Yields:
            tuple:
            A 2-tuple of the SSO backend form and the name of the form field
            to enable that backend.
        """
        for sso_backend_id, form in self.sso_backend_forms.items():
            enable_field_id = '%s_enabled' % sso_backend_id

            yield form, enable_field_id

    class Meta:
        title = _('Authentication Settings')
        save_blacklist = ('auth_anonymous_access',)

        subforms = (
            {
                'subforms_attr': 'auth_backend_forms',
                'controller_field': 'auth_backend',
            },
            {
                'subforms_attr': 'sso_backend_forms',
                'controller_field': None,
                'enable_checkbox': True,
            },
        )

        fieldsets = (
            {
                'classes': ('wide',),
                'fields': ['auth_anonymous_access', 'auth_backend'],
            },
        )
