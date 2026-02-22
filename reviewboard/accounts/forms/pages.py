"""Forms for user accounts."""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import TYPE_CHECKING
from urllib.parse import unquote

from django import forms
from django.contrib import messages
from django.contrib.auth.views import RedirectURLMixin
from django.forms import widgets
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from djblets.avatars.forms import (
    AvatarSettingsForm as DjbletsAvatarSettingsForm)
from djblets.configforms.forms import ConfigPageForm
from djblets.forms.fields import TimeZoneField
from djblets.privacy.consent.forms import ConsentConfigPageFormMixin
from djblets.siteconfig.models import SiteConfiguration
from oauth2_provider.models import AccessToken

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.avatars import avatar_services
from reviewboard.oauth.features import oauth2_service_feature
from reviewboard.oauth.models import Application
from reviewboard.reviews.models import Group
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.themes.ui.registry import ui_theme_registry

if TYPE_CHECKING:
    from typing import Any


logger = logging.getLogger(__name__)


class AccountPageForm(ConfigPageForm):
    """Base class for a form on the My Account page.

    AccountPageForms belong to AccountPages, and will be displayed on the
    My Account page for a user.

    A simple form presents fields that can be filled out and posted.
    More advanced forms can supply their own template or even their own
    JavaScript models and views.
    """

    #: Features required for a form to be displayed.
    required_features = []

    def is_visible(self):
        """Return whether or not the form should be rendered.

        This is a base implementation that takes into account a set of required
        features.

        Returns
            bool:
            Whether or not the form should be rendered.
        """
        return all(feature.is_enabled() for feature in self.required_features)


class AccountSettingsForm(AccountPageForm):
    """Form for the Settings page for an account."""

    form_id = 'settings'
    form_title = _('Settings')

    timezone = TimeZoneField(
        label=_('Time zone'),
        required=True,
        help_text=_("The time zone you're in."))

    syntax_highlighting = forms.BooleanField(
        label=_('Enable syntax highlighting in the diff viewer'),
        required=False)
    open_an_issue = forms.BooleanField(
        label=_('Always open an issue when comment box opens'),
        required=False)

    default_use_rich_text = forms.BooleanField(
        label=_('Always use Markdown for text fields'),
        required=False)

    should_send_email = forms.BooleanField(
        label=_('Get e-mail notification for review requests and reviews'),
        required=False)

    should_send_own_updates = forms.BooleanField(
        label=_('Get e-mail notifications for my own activity'),
        required=False)

    enable_desktop_notifications = forms.BooleanField(
        label=_('Show desktop notifications'),
        required=False)

    def load(self):
        """Load data for the form."""
        profile = self.user.get_profile()

        siteconfig = SiteConfiguration.objects.get_current()
        diffviewer_syntax_highlighting = siteconfig.get(
            'diffviewer_syntax_highlighting')

        self.set_initial({
            'open_an_issue': profile.open_an_issue,
            'syntax_highlighting': (profile.syntax_highlighting and
                                    diffviewer_syntax_highlighting),
            'timezone': profile.timezone,
            'default_use_rich_text': profile.should_use_rich_text,
            'should_send_email': profile.should_send_email,
            'should_send_own_updates': profile.should_send_own_updates,
            'enable_desktop_notifications':
                profile.should_enable_desktop_notifications,
        })

        if not diffviewer_syntax_highlighting:
            self.fields['syntax_highlighting'].widget.attrs.update({
                'disabled': True,
            })

    def save(self):
        """Save the form."""
        profile = self.user.get_profile()
        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.get('diffviewer_syntax_highlighting'):
            profile.syntax_highlighting = \
                self.cleaned_data['syntax_highlighting']

        profile.open_an_issue = self.cleaned_data['open_an_issue']
        profile.default_use_rich_text = \
            self.cleaned_data['default_use_rich_text']
        profile.timezone = self.cleaned_data['timezone']
        profile.should_send_email = self.cleaned_data['should_send_email']
        profile.should_send_own_updates = \
            self.cleaned_data['should_send_own_updates']
        profile.settings['enable_desktop_notifications'] = \
            self.cleaned_data['enable_desktop_notifications']
        profile.save(update_fields=(
            'default_use_rich_text',
            'open_an_issue',
            'settings',
            'should_send_email',
            'should_send_own_updates',
            'syntax_highlighting',
            'timezone',
        ))

        messages.add_message(self.request, messages.INFO,
                             _('Your settings have been saved.'))

    class Meta:
        fieldsets = (
            (_('General Settings'), {
                'fields': ('form_target',
                           'timezone',
                           'syntax_highlighting',
                           'open_an_issue',
                           'default_use_rich_text'),
            }),
            (_('Notifications'), {
                'fields': ('should_send_email',
                           'should_send_own_updates',
                           'enable_desktop_notifications'),
            })
        )


class ThemeForm(AccountPageForm):
    """Form for controlling the themes of Review Board.

    Version Added:
        7.0
    """

    form_id = 'theme'
    form_title = _('Theme')

    ui_theme = forms.ChoiceField(
        label=_('Default appearance'),
        choices=[],
        widget=forms.widgets.RadioSelect())

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the form.

        This will populate the theme choices with the available settings for
        the install.

        Args:
            *args (tuple):
                Positional arguments for the parent form.

            **kwargs (dict):
                Keyword arguments for the parent form.
        """
        super().__init__(*args, **kwargs)

        default_theme = ui_theme_registry.get_theme('default')

        self.fields['ui_theme'].choices = [
            ('default', _('Default appearance (%(theme_name)s)') % {
                'theme_name': default_theme.name,
            }),
            *[
                (theme.theme_id, theme.name)
                for theme in ui_theme_registry
                if theme is not default_theme
            ],
        ]

    def load(self):
        """Load settings for the form.

        This will convert stored profile settings into initial form data.
        """
        profile = self.user.get_profile()

        self.set_initial({
            'ui_theme': profile.ui_theme_id,
        })

    def save(self) -> None:
        """Save the form values to the profile.

        This will convert the user-provided form data to stored profile
        settings, and then notify the user the settings have been saved.
        """
        profile = self.user.get_profile()

        profile.ui_theme_id = self.cleaned_data['ui_theme'] or 'default'

        profile.save(update_fields=('settings',))

        messages.add_message(self.request, messages.INFO,
                             _('Your appearance settings have been saved.'))


class AvatarSettingsForm(DjbletsAvatarSettingsForm):
    """A form for configuring the avatar for a user.

    This form will only be shown when avatars are enabled for the server.
    """

    avatar_service_registry = avatar_services

    def is_visible(self):
        """Return whether or not to show the avatar settings form.

        Returns:
            bool:
            Whether or not to show the avatar settings form.
        """
        return (super(AvatarSettingsForm, self).is_visible() and
                self.avatar_service_registry.avatars_enabled and
                len(self.avatar_service_registry.enabled_services) > 0)


class APITokensForm(AccountPageForm):
    """Form for showing a user's API tokens."""

    form_id = 'api_tokens'
    form_title = _('API Tokens')
    save_label = None

    js_view_class = 'RB.APITokensView'

    def get_js_view_data(self):
        """Get data to pass to the JavaScript view."""
        # Fetch the list of the user's API tokens, globally.
        api_tokens = self.user.webapi_tokens.all()

        # Group the API tokens by LocalSite or the global site.
        serialized_api_tokens = OrderedDict()
        serialized_api_tokens[''] = \
            self._serialize_api_tokens(None, api_tokens)

        for local_site in self.page.config_view.ordered_user_local_sites:
            serialized_api_tokens[local_site.name] = \
                self._serialize_api_tokens(local_site, api_tokens)

        return {
            'apiTokens': serialized_api_tokens,
        }

    def _serialize_api_tokens(self, local_site, api_tokens):
        if local_site:
            local_site_prefix = local_site_reverse(
                'root',
                local_site_name=local_site.name)[1:]
        else:
            local_site_prefix = None

        return {
            'localSitePrefix': local_site_prefix,
            'tokens': [
                {
                    'deprecated': api_token.is_deprecated(),
                    'expired': api_token.is_expired(),
                    'expires': api_token.expires,
                    'id': api_token.pk,
                    'invalidDate': api_token.invalid_date,
                    'invalidReason': api_token.invalid_reason,
                    'lastUpdated': api_token.last_updated,
                    'lastUsed': api_token.last_used,
                    'note': api_token.note,
                    'policy': api_token.policy,
                    'timeAdded': api_token.time_added,
                    'tokenValue': api_token.token,
                    'valid': api_token.valid,
                }
                for api_token in api_tokens
                if api_token.local_site == local_site
            ]
        }


class ChangePasswordForm(AccountPageForm):
    """Form for changing a user's password."""

    form_id = 'change_password'
    form_title = _('Change Password')
    save_label = _('Change Password')

    old_password = forms.CharField(
        label=_('Current password'),
        required=True,
        widget=widgets.PasswordInput())
    password1 = forms.CharField(
        label=_('New password'),
        required=True,
        widget=widgets.PasswordInput())
    password2 = forms.CharField(
        label=_('New password (confirm)'),
        required=True,
        widget=widgets.PasswordInput())

    def is_visible(self):
        """Return whether or not the "change password" form should be shown.

        Returns:
            bool:
            Whether or not the form will be rendered.
        """
        return (super(ChangePasswordForm, self).is_visible() and
                get_enabled_auth_backends()[0].supports_change_password)

    def clean_old_password(self):
        """Validate the 'old_password' field.

        This checks to make sure the old password is correct when changing the
        password.
        """
        backend = get_enabled_auth_backends()[0]

        password = self.cleaned_data['old_password']

        try:
            is_authenticated = backend.authenticate(
                request=None,
                username=self.user.username,
                password=password)
        except Exception as e:
            logger.exception('Error when calling authenticate for auth '
                             'backend %r: %s',
                             backend, e)
            raise forms.ValidationError(_('Unexpected error when validating '
                                          'the password. Please contact the '
                                          'administrator.'))

        if not is_authenticated:
            raise forms.ValidationError(_('This password is incorrect'))

    def clean_password2(self):
        """Validate the 'password2' field.

        This makes sure that the two password fields match.
        """
        p1 = self.cleaned_data['password1']
        p2 = self.cleaned_data['password2']

        if p1 != p2:
            raise forms.ValidationError(_('Passwords do not match'))

        return p2

    def save(self):
        """Save the form."""
        from reviewboard.notifications.email.signal_handlers import \
            send_password_changed_mail

        backend = get_enabled_auth_backends()[0]

        try:
            backend.update_password(self.user, self.cleaned_data['password1'])

            self.user.save()

            messages.add_message(self.request, messages.INFO,
                                 _('Your password has been changed.'))
        except Exception as e:
            logger.error('Error when calling update_password for auth '
                         'backend %r: %s',
                         backend, e, exc_info=True)
            messages.add_message(self.request, messages.INFO,
                                 _('Unexpected error when changing your '
                                   'password. Please contact the '
                                   'administrator.'))
        else:
            send_password_changed_mail(self.user)


class ProfileForm(AccountPageForm):
    """Form for the Profile page for an account."""

    form_id = 'profile'
    form_title = _('Profile')
    save_label = _('Save Profile')

    first_name = forms.CharField(
        label=_('First name'),
        required=False)
    last_name = forms.CharField(
        label=_('Last name'),
        required=False)
    email = forms.EmailField(
        label=_('E-mail address'),
        required=True)
    profile_private = forms.BooleanField(
        required=False,
        label=_('Keep profile information private'),
        help_text=_(
            'By default, profile information (full name, e-mail address, and '
            'timezone) is only hidden from users who are not logged in. With '
            'this setting enabled, it will also be hidden from '
            'non-administrators.'))

    def load(self):
        """Load data for the form."""
        profile = self.user.get_profile()

        self.set_initial({
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'profile_private': profile.is_private,
        })

        backend = get_enabled_auth_backends()[0]

        if not backend.supports_change_name:
            del self.fields['first_name']
            del self.fields['last_name']

        if not backend.supports_change_email:
            del self.fields['email']

    def save(self):
        """Save the form."""
        backend = get_enabled_auth_backends()[0]

        if backend.supports_change_name:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']

            try:
                backend.update_name(self.user)
            except Exception as e:
                logger.error('Error when calling update_name for auth '
                             'backend %r: %s',
                             backend, e, exc_info=True)

        if backend.supports_change_email:
            new_email = self.cleaned_data['email']

            if new_email != self.user.email:
                self.user.email = new_email

                try:
                    backend.update_email(self.user)
                except Exception as e:
                    logger.error('Error when calling update_email for auth '
                                 'backend %r: %s',
                                 backend, e, exc_info=True)

        self.user.save()

        profile = self.user.get_profile()
        profile.is_private = self.cleaned_data['profile_private']
        profile.save(update_fields=('is_private',))

        messages.add_message(self.request, messages.INFO,
                             _('Your profile has been saved.'))


class GroupsForm(AccountPageForm):
    """Form for the group membership page.

    Unlike most forms, this doesn't deal with fields or saving to the database.
    Instead, it sets up the JavaScript View and provides serialized data
    representing the groups. The View handles group membership through the
    API.
    """

    form_id = 'groups'
    form_title = _('Groups')
    save_label = None

    js_view_class = 'RB.JoinedGroupsView'

    def get_js_view_data(self):
        """Get data to pass to the JavaScript view."""
        # Fetch the list of IDs of groups the user has joined.
        joined_group_ids = self.user.review_groups.values_list('pk', flat=True)

        # Fetch the list of groups available to the user.
        serialized_groups = OrderedDict()
        serialized_groups[''] = self._serialize_groups(None, joined_group_ids)

        for local_site in self.page.config_view.ordered_user_local_sites:
            serialized_groups[local_site.name] = self._serialize_groups(
                local_site, joined_group_ids)

        return {
            'groups': serialized_groups,
        }

    def _serialize_groups(self, local_site, joined_group_ids):
        if local_site:
            local_site_name = local_site.name
        else:
            local_site_name = None

        groups = Group.objects.accessible(user=self.user,
                                          local_site=local_site)
        return [
            {
                'name': group.name,
                'reviewGroupID': group.pk,
                'displayName': group.display_name,
                'localSiteName': local_site_name,
                'joined': group.pk in joined_group_ids,
                'url': local_site_reverse('group',
                                          local_site_name=local_site_name,
                                          kwargs={'name': group.name}),
            }
            for group in groups.order_by('name')
        ]


class OAuthApplicationsForm(AccountPageForm):
    """The OAuth Application form.

    This provides a list of all current OAuth2 applications the user has
    access to.
    """

    form_id = 'oauth'
    form_title = _('OAuth Applications')
    js_view_class = 'RB.OAuthApplicationsView'

    required_features = [oauth2_service_feature]
    save_label = None

    def get_js_view_data(self):
        """Return the data for the associated Javascript view.

        Returns:
            dict:
            Data to be passed to the Javascript view.
        """
        apps = {
            site_name: []
            for site_name in (
                LocalSite.objects
                .filter(users=self.user)
                .values_list('name', flat=True)
            )
        }

        apps[''] = []

        app_qs = (
            Application.objects
            .select_related('local_site')
            .filter(user=self.user)
        )

        for app in app_qs:
            app = self.serialize_app(app)
            apps[app['localSiteName'] or ''].append(app)

        return {
            'apps': apps,
            'editURL': reverse('edit-oauth-app'),
            'baseURL': reverse('oauth-apps-resource'),
        }

    @staticmethod
    def serialize_app(app):
        """Serialize an application for the JavaScript view.

        Args:
            app (reviewboard.oauth.models.Application):
                The application to serialize.

        Returns:
            dict:
            The serialized application.
        """
        if app.local_site is not None:
            local_site_name = app.local_site.name
        else:
            local_site_name = None

        enabled = app.enabled
        is_disabled_for_security = (not enabled and
                                    app.is_disabled_for_security)
        original_user = None

        if is_disabled_for_security:
            original_user = app.original_user.username

        return {
            'id': app.pk,
            'editURL': reverse('edit-oauth-app', kwargs={'app_id': app.pk}),
            'enabled': app.enabled,
            'isDisabledForSecurity': app.is_disabled_for_security,
            'localSiteName': local_site_name,
            'name': app.name,
            'originalUser': original_user,
        }


class OAuthTokensForm(AccountPageForm):
    """The OAuth Token form

    This provides a list of all current OAuth2 tokens the user has created.
    """

    form_id = 'oauth_tokens'
    form_title = _('OAuth Tokens')
    js_view_class = 'RB.OAuthTokensView'

    required_features = [oauth2_service_feature]
    save_label = None

    def get_js_view_data(self):
        """Return the data for the JavaScript view.

        Returns:
            dict:
            A dict containing a single key:

            ``'tokens'`` (:py:class:`list`):
                A list of serialized information about each token.
        """
        tokens = [
            self.serialize_token(token)
            for token in (
                AccessToken.objects
                .select_related('application', 'application__local_site')
                .filter(user=self.user)
            )
        ]

        return {
            'tokens': tokens,
        }

    @staticmethod
    def serialize_token(token):
        """Serialize a single token for the JavaScript view.

        Returns:
            dict:
            A dict with the following keys:

            ``'apiURL'`` (:py:class:`unicode`):
                The URL to access the token via the API.

            ``'application'`` (:py:class:`unicode`):
                The name of the application the token is associated with.
        """
        return {
            'apiURL': local_site_reverse(
                'oauth-token-resource',
                local_site=token.application.local_site,
                kwargs={
                    'oauth_token_id': token.pk,
                },
            ),
            'application': token.application.name,
        }


class PrivacyForm(ConsentConfigPageFormMixin, RedirectURLMixin,
                  AccountPageForm):
    """A form for displaying privacy information and gathering consent.

    This will display a user's privacy rights, link to any configured
    Privacy Policy document, and display a form for gathering consent for
    features that make use of the user's personally identifying information.

    Version Changed:
        7.0.5:
        Added :py:class:`django.contrib.auth.views.RedirectURLMixin` as a mixin
        to the class, to verify that we're using safe URL redirects.
    """

    next_url = forms.CharField(required=False,
                               widget=forms.HiddenInput)

    form_title = _('My Privacy Rights')
    template_name = 'accounts/privacy_form.html'
    redirect_field_name = 'next_url'

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the form.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent form.

            **kwargs (dict):
                Keyword arguments to pass to the parent form.
        """
        super().__init__(*args, **kwargs)

        siteconfig = SiteConfiguration.objects.get_current()

        if not siteconfig.get('privacy_enable_user_consent'):
            del self.fields[self.consent_field_name]
            self.save_label = None

    def load(self) -> None:
        """Load the form data.

        If a ``?next`` query argument is provided, it will be loaded into the
        initial value for the ``next_url`` so that it will persist through
        page submission.
        """
        super().load()

        next_url = self.request.GET.get('next')

        if next_url:
            self.set_initial({'next_url': unquote(next_url)})

    def is_visible(self) -> bool:
        """Return whether or not the form should be rendered.

        This will check if there's any information to display in this form.
        It's only displayed if consent requirements are enabled or there's
        any privacy information configured in Admin Settings.

        Returns:
            bool:
            Whether or not the form should be rendered.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        return (siteconfig.get('privacy_enable_user_consent') or
                bool(siteconfig.get('privacy_info_html')))

    def get_extra_context(self) -> dict[str, Any]:
        """Return extra context for the template.

        Returns:
            dict:
            Context used for rendering the form's template.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        return {
            'privacy_info_html': siteconfig.get('privacy_info_html'),
        }

    def clean_next_url(self) -> str | None:
        """Clean the next_url field.

        Returns:
            str:
            The URL to redirect to, if any.
        """
        return self.cleaned_data.get('next_url', '').strip() or None

    def save(self) -> HttpResponseRedirect | None:
        """Save the privacy form.

        This may redirect the user to the next URL if it is specified.

        Returns:
            django.http.HttpResponseRedirect:
            A redirect to the next URL if given and ``None`` otherwise.
        """
        redirect_to = self.get_redirect_url()

        if redirect_to:
            self.save_consent(self.request.user)
            return HttpResponseRedirect(redirect_to)
        else:
            return super().save()
