"""Administration form for support settings."""

from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.support import get_install_key


class SupportSettingsForm(SiteSettingsForm):
    """Support settings for Review Board."""

    install_key = forms.CharField(
        label=_('Install key'),
        help_text=_('The installation key to provide when purchasing a '
                    'support contract.'),
        required=False,
        widget=forms.TextInput(attrs={
            'size': '80',
            'readonly': 'readonly'
        }))

    support_url = forms.CharField(
        label=_('Custom Support URL'),
        help_text=_("The location of your organization's own Review Board "
                    "support page. Leave blank to use the default support "
                    "page."),
        required=False,
        widget=forms.TextInput(attrs={'size': '80'}))

    send_support_usage_stats = forms.BooleanField(
        label=_('Send support-related usage statistics'),
        help_text=_('Basic usage information will be sent to us at times to '
                    'help with some support issues and to provide a more '
                    'personalized support page for your users. '
                    '<i>No information is ever given to a third party.</i>'),
        required=False)

    def load(self):
        """Load settings from the form.

        This will populate initial fields based on the site configuration
        and the current install key.
        """
        super(SupportSettingsForm, self).load()

        self.fields['install_key'].initial = get_install_key()

    class Meta:
        title = _('Support Settings')
        save_blacklist = ('install_key',)
        fieldsets = ({
            'classes': ('wide',),
            'description': (
                '<p>'
                'For fast one-on-one support, plus other benefits, '
                'purchase a <a href="https://www.reviewboard.org/support/">'
                'support contract</a>.'
                '</p>'
                '<p>'
                'You can also customize where your users will go for '
                'support by changing the Custom Support URL below. If left '
                'blank, they will be taken to our support channel.'
                '</p>'),
            'fields': ('install_key', 'support_url',
                       'send_support_usage_stats'),
        },)
