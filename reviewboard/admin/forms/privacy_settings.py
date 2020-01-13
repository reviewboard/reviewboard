"""Administration form for privacy settings."""

from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _
from djblets.avatars.registry import AvatarServiceRegistry
from djblets.siteconfig.forms import SiteSettingsForm


class PrivacySettingsForm(SiteSettingsForm):
    """Site-wide user privacy settings for Review Board."""

    terms_of_service_url = forms.URLField(
        label=_('Terms of service URL'),
        required=False,
        help_text=_('URL to your terms of service. This will be displayed on '
                    'the My Account page and during login and registration.'),
        widget=forms.widgets.URLInput(attrs={
            'size': 80,
        }))

    privacy_policy_url = forms.URLField(
        label=_('Privacy policy URL'),
        required=False,
        help_text=_('URL to your privacy policy. This will be displayed on '
                    'the My Account page and during login and registration.'),
        widget=forms.widgets.URLInput(attrs={
            'size': 80,
        }))

    privacy_info_html = forms.CharField(
        label=_('Privacy information'),
        required=False,
        help_text=_('A description of the privacy guarantees for users on '
                    'this server. This will be displayed on the My Account '
                    '-> Your Privacy page. HTML is allowed.'),
        widget=forms.widgets.Textarea(attrs={
            'cols': 60,
        }))

    privacy_enable_user_consent = forms.BooleanField(
        label=_('Require consent for usage of personal information'),
        required=False,
        help_text=_('Require consent from users when using their personally '
                    'identifiable information (usernames, e-mail addresses, '
                    'etc.) for when talking to third-party services, like '
                    'Gravatar. This is required for EU GDPR compliance.'))

    def save(self):
        """Save the privacy settings form.

        This will write the new configuration to the database.
        """
        self.siteconfig.set(AvatarServiceRegistry.ENABLE_CONSENT_CHECKS,
                            self.cleaned_data['privacy_enable_user_consent'])

        super(PrivacySettingsForm, self).save()

    class Meta:
        title = _('User Privacy Settings')
        fieldsets = (
            {
                'classes': ('wide',),
                'fields': (
                    'terms_of_service_url',
                    'privacy_policy_url',
                    'privacy_info_html',
                    'privacy_enable_user_consent',
                ),
            },
        )
