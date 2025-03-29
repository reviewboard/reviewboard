"""Forms for SAML SSO.

Version Added:
    5.0
"""

from __future__ import annotations

from typing import Any

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.sso.backends.saml.settings import (
    DEFAULT_ATTR_EMAIL,
    DEFAULT_ATTR_FIRSTNAME,
    DEFAULT_ATTR_FULLNAME,
    DEFAULT_ATTR_LASTNAME,
    SAMLBinding,
    SAMLDigestAlgorithm,
    SAMLNameIDFormat,
    SAMLSignatureAlgorithm)


class SAMLLinkUserForm(AuthenticationForm):
    """Form for linking existing user accounts after SAML authentication.

    Version Added:
        5.0
    """

    provision: forms.BooleanField = forms.BooleanField(
        widget=forms.HiddenInput(),
        required=False)

    def __init__(self, *args, **kwargs) -> None:
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

    def clean(self) -> dict[str, Any]:
        """Run validation on the form.

        Returns:
            dict:
            The cleaned data.
        """
        username = self.cleaned_data.get('username')

        if self.cleaned_data.get('provision'):
            # If we're provisioning a new user, the only thing we need to check
            # is if automatic provisioning is enabled. We don't actually care
            # about authenticating the login/password.
            siteconfig = SiteConfiguration.objects.get_current()

            if not siteconfig.get('saml_automatically_provision_users', True):
                raise ValidationError(
                    _(
                        'A user account for {username} does not exist. Your '
                        'administrator will need to provision an account '
                        'before you can log in.'
                    )
                    .format(username=username))


            return self.cleaned_data
        else:
            if username:
                user = User.objects.get(username=username)
                self.confirm_login_allowed(user)

            return super().clean()


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

    saml_automatically_provision_users = forms.BooleanField(
        label=_('Automatically provision user accounts'),
        help_text=_(
            'When a new user logs in with SSO, automatically create a Review '
            'Board account for them. If unchecked, user accounts will need to '
            'be provisioned manually before users can log in.'
        ),
        required=False)

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

    saml_nameid_format = forms.ChoiceField(
        label=_('NameID format'),
        choices=SAMLNameIDFormat.CHOICES,
        initial=SAMLNameIDFormat.PERSISTENT)

    saml_require_login_to_link = forms.BooleanField(
        label=_('Require login to link'),
        help_text=_('When a matching user is found, ask them to log in with '
                    'their existing password before linking. If unchecked, '
                    'make sure that your Identity Provider is trusted and is '
                    'sending the correct username for all existing users.'),
        required=False)

    saml_attr_email = forms.CharField(
        label=_('Custom e-mail attribute'),
        required=True,
        initial=DEFAULT_ATTR_EMAIL,
        help_text=_('If your Identity Provider does not allow you to '
                    'configure attribute names, set this to the E-mail '
                    'attribute name returned in the SAML response.'),
        widget=forms.TextInput(attrs={'size': '60'}))

    saml_attr_firstname = forms.CharField(
        label=_('Custom first name attribute'),
        required=True,
        initial=DEFAULT_ATTR_FIRSTNAME,
        help_text=_('If your Identity Provider does not allow you to '
                    'configure attribute names, set this to the FirstName '
                    'attribute name returned in the SAML response.'),
        widget=forms.TextInput(attrs={'size': '60'}))

    saml_attr_lastname = forms.CharField(
        label=_('Custom last name attribute'),
        required=True,
        initial=DEFAULT_ATTR_LASTNAME,
        help_text=_('If your Identity Provider does not allow you to '
                    'configure attribute names, set this to the LastName '
                    'attribute name returned in the SAML response.'),
        widget=forms.TextInput(attrs={'size': '60'}))

    saml_attr_fullname = forms.CharField(
        label=_('Custom full name attribute'),
        required=True,
        initial=DEFAULT_ATTR_FULLNAME,
        help_text=_('If your Identity Provider does not allow you to '
                    'configure attribute names, set this to the FullName '
                    'attribute name returned in the SAML response. This is '
                    'only used if the separate first and last name '
                    'attributes are not available in the response.'),
        widget=forms.TextInput(attrs={'size': '60'}))

    class Meta:
        """Metadata for the SAMLSettingsForm."""

        title = _('SAML 2.0 Authentication Settings')
        fieldsets = (
            (None, {
                'fields': ('saml_login_button_text',
                           'saml_issuer',
                           'saml_signature_algorithm',
                           'saml_digest_algorithm',
                           'saml_nameid_format',
                           'saml_verification_cert',
                           'saml_sso_url',
                           'saml_sso_binding_type',
                           'saml_slo_url',
                           'saml_slo_binding_type',
                           'saml_automatically_provision_users',
                           'saml_require_login_to_link',
                           'saml_attr_email',
                           'saml_attr_firstname',
                           'saml_attr_lastname',
                           'saml_attr_fullname'),
            }),
        )
