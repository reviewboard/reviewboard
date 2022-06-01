"""Forms for SAML SSO.

Version Added:
    5.0
"""

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.accounts.sso.backends.saml.settings import (
    SAMLBinding,
    SAMLDigestAlgorithm,
    SAMLSignatureAlgorithm)


class SAMLLinkUserForm(AuthenticationForm):
    """Form for linking existing user accounts after SAML authentication.

    Version Added:
        5.0
    """

    provision = forms.BooleanField(
        widget=forms.HiddenInput(),
        required=False)

    def __init__(self, *args, **kwargs):
        """Initialize the form.

        Args:
            *args (tuple):
                Positional arguments to pass through to the parent class.

            **kwargs (dict):
                Keyword arguments to pass through to the parent class.
        """
        super().__init__(*args, **kwargs)

        # If we're in provision mode, we don't want username and password to be
        # required.
        if kwargs.get('initial', {}).get('provision', False):
            self.fields['username'].required = False
            self.fields['password'].required = False

    def clean(self):
        """Run validation on the form.

        Returns:
            dict:
            The cleaned data.
        """
        if self.cleaned_data.get('provision'):
            # If we're provisioning a new user, we don't actually care about
            # authenticating the login/password.
            return self.cleaned_data
        else:
            return super(SAMLLinkUserForm, self).clean()


def validate_x509(value):
    """Validate that the given value is a correct X.509 certificate.

    Args:
        value (str):
            The value to validate.

    Raises:
        django.core.exceptions.ValidationError:
            The given value was not a correct X.509 certificate.
    """
    try:
        x509.load_pem_x509_certificate(value.encode('ascii'),
                                       default_backend())
    except ValueError:
        raise ValidationError('Could not parse X.509 certificate')


class SAMLSettingsForm(SiteSettingsForm):
    """Form for configuring SAML authentication.

    Version Added:
        5.0
    """

    saml_login_button_text = forms.CharField(
        label=_('Login button label'))

    saml_issuer = forms.CharField(
        label=_('IdP issuer URL (or Entity ID)'),
        validators=[URLValidator(schemes=['http', 'https'])],
        widget=forms.TextInput(attrs={'size': '60'}))

    saml_signature_algorithm = forms.ChoiceField(
        label=_('Signature algorithm'),
        choices=SAMLSignatureAlgorithm.CHOICES)

    saml_digest_algorithm = forms.ChoiceField(
        label=_('Digest algorithm'),
        choices=SAMLDigestAlgorithm.CHOICES)

    saml_verification_cert = forms.CharField(
        label=_('X.509 verification certificate'),
        validators=[validate_x509],
        widget=forms.Textarea())

    saml_sso_url = forms.CharField(
        label=_('SAML 2.0 endpoint'),
        validators=[URLValidator(schemes=['http', 'https'])],
        widget=forms.TextInput(attrs={'size': '60'}))

    saml_sso_binding_type = forms.ChoiceField(
        label=_('SAML 2.0 endpoint binding'),
        choices=SAMLBinding.CHOICES,
        initial=SAMLBinding.HTTP_POST)

    saml_slo_url = forms.CharField(
        label=_('SLO endpoint'),
        validators=[URLValidator(schemes=['http', 'https'])],
        widget=forms.TextInput(attrs={'size': '60'}))

    saml_slo_binding_type = forms.ChoiceField(
        label=_('SLO endpoint binding'),
        choices=SAMLBinding.CHOICES,
        initial=SAMLBinding.HTTP_REDIRECT)

    saml_require_login_to_link = forms.BooleanField(
        label=_('Require login to link'),
        help_text=_('When a matching user is found, ask them to log in with '
                    'their existing password before linking. If unchecked, '
                    'make sure that your Identity Provider is trusted and is '
                    'sending the correct username for all existing users.'),
        required=False)

    class Meta:
        """Metadata for the SAMLSettingsForm."""

        title = _('SAML 2.0 Authentication Settings')
        fieldsets = (
            (None, {
                'fields': ('saml_login_button_text',
                           'saml_issuer',
                           'saml_signature_algorithm',
                           'saml_digest_algorithm',
                           'saml_verification_cert',
                           'saml_sso_url',
                           'saml_sso_binding_type',
                           'saml_slo_url',
                           'saml_slo_binding_type',
                           'saml_require_login_to_link'),
            }),
        )
