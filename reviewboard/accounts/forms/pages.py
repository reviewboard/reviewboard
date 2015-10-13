from __future__ import unicode_literals

import logging

from django import forms
from django.contrib import messages
from django.forms import widgets
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _
from djblets.forms.fields import TimeZoneField
from djblets.siteconfig.models import SiteConfiguration
from djblets.configforms.forms import ConfigPageForm

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.reviews.models import Group
from reviewboard.site.urlresolvers import local_site_reverse


class AccountPageForm(ConfigPageForm):
    """Base class for a form on the My Account page.

    AccountPageForms belong to AccountPages, and will be displayed on the
    My Account page for a user.

    A simple form presents fields that can be filled out and posted.
    More advanced forms can supply their own template or even their own
    JavaScript models and views.
    """


class AccountSettingsForm(AccountPageForm):
    """Form for the Settings page for an account."""

    form_id = 'settings'
    form_title = _('Settings')
    save_label = _('Save Settings')

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

    should_send_email = forms.BooleanField(
        label=_('Get e-mail notification for review requests and reviews'),
        required=False)

    should_send_own_updates = forms.BooleanField(
        label=_('Get e-mail notifications for my own activity'),
        required=False)

    default_use_rich_text = forms.BooleanField(
        label=_('Always use Markdown for text fields'),
        required=False)

    def load(self):
        """Load data for the form."""
        self.set_initial({
            'open_an_issue': self.profile.open_an_issue,
            'should_send_email': self.profile.should_send_email,
            'should_send_own_updates': self.profile.should_send_own_updates,
            'syntax_highlighting': self.profile.syntax_highlighting,
            'timezone': self.profile.timezone,
            'default_use_rich_text': self.profile.should_use_rich_text,
        })

        siteconfig = SiteConfiguration.objects.get_current()

        if not siteconfig.get('diffviewer_syntax_highlighting'):
            del self.fields['syntax_highlighting']

    def save(self):
        """Save the form."""
        if 'syntax_highlighting' in self.cleaned_data:
            self.profile.syntax_highlighting = \
                self.cleaned_data['syntax_highlighting']

        self.profile.open_an_issue = self.cleaned_data['open_an_issue']
        self.profile.should_send_email = self.cleaned_data['should_send_email']
        self.profile.should_send_own_updates = \
            self.cleaned_data['should_send_own_updates']
        self.profile.default_use_rich_text = \
            self.cleaned_data['default_use_rich_text']
        self.profile.timezone = self.cleaned_data['timezone']
        self.profile.save()

        messages.add_message(self.request, messages.INFO,
                             _('Your settings have been saved.'))


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
        serialized_api_tokens = SortedDict()
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
                    'id': api_token.pk,
                    'tokenValue': api_token.token,
                    'timeAdded': api_token.time_added,
                    'lastUpdated': api_token.last_updated,
                    'note': api_token.note,
                    'policy': api_token.policy,
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
        """Get whether or not the "change password" form should be shown."""
        backend = get_enabled_auth_backends()[0]

        return backend.supports_change_password

    def clean_old_password(self):
        """Validate the 'old_password' field.

        This checks to make sure the old password is correct when changing the
        password.
        """
        backend = get_enabled_auth_backends()[0]

        password = self.cleaned_data['old_password']

        try:
            is_authenticated = backend.authenticate(self.user.username,
                                                    password)
        except Exception as e:
            logging.error('Error when calling authenticate for auth backend '
                          '%r: %s',
                          backend, e, exc_info=1)
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
        backend = get_enabled_auth_backends()[0]

        try:
            backend.update_password(self.user, self.cleaned_data['password1'])

            self.user.save()

            messages.add_message(self.request, messages.INFO,
                                 _('Your password has been changed.'))
        except Exception as e:
            logging.error('Error when calling update_password for auth '
                          'backend %r: %s',
                          backend, e, exc_info=1)
            messages.add_message(self.request, messages.INFO,
                                 _('Unexpected error when changing your '
                                   'password. Please contact the '
                                   'administrator.'))


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
        label=_("Keep profile information private"))

    def load(self):
        """Load data for the form."""
        self.set_initial({
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'profile_private': self.profile.is_private,
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
                logging.error('Error when calling update_name for auth '
                              'backend %r: %s',
                              backend, e, exc_info=1)

        if backend.supports_change_email:
            new_email = self.cleaned_data['email']

            if new_email != self.user.email:
                self.user.email = new_email

                try:
                    backend.update_email(self.user)
                except Exception as e:
                    logging.error('Error when calling update_email for auth '
                                  'backend %r: %s',
                                  backend, e, exc_info=1)

        self.user.save()

        self.profile.is_private = self.cleaned_data['profile_private']
        self.profile.save()

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
        serialized_groups = SortedDict()
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
