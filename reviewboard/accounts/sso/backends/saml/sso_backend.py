"""SAML SSO backend.

Version Added:
    5.0
"""

from importlib import import_module

from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _, gettext
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import cached_property

from reviewboard.accounts.sso.backends.base import BaseSSOBackend
from reviewboard.accounts.sso.backends.saml.forms import SAMLSettingsForm
from reviewboard.accounts.sso.backends.saml.settings import (
    SAMLBinding,
    SAMLDigestAlgorithm,
    SAMLSignatureAlgorithm)
from reviewboard.accounts.sso.backends.saml.views import (
    SAMLACSView,
    SAMLLinkUserView,
    SAMLLoginView,
    SAMLMetadataView,
    SAMLSLSView)


class SAMLSSOBackend(BaseSSOBackend):
    """SAML SSO backend.

    Version Added:
        5.0
    """

    backend_id = 'saml'
    name = _('SAML 2.0')
    settings_form = SAMLSettingsForm
    siteconfig_defaults = {
        'saml_digest_algorithm': SAMLDigestAlgorithm.SHA1,
        'saml_enabled': False,
        'saml_issuer': '',
        'saml_login_button_text': _('Log in with SAML SSO'),
        'saml_require_login_to_link': True,
        'saml_signature_algorithm': SAMLSignatureAlgorithm.DSA_SHA1,
        'saml_slo_binding_type': SAMLBinding.HTTP_REDIRECT,
        'saml_slo_url': '',
        'saml_sso_binding_type': SAMLBinding.HTTP_POST,
        'saml_sso_url': '',
        'saml_verfication_cert': '',
    }
    login_view_cls = SAMLLoginView

    def __init__(self):
        """Initialize the SSO backend."""
        super().__init__()

        self._available = None

    @cached_property
    def login_label(self):
        """The text to show on the login button.

        Type:
            str
        """
        siteconfig = SiteConfiguration.objects.get_current()
        return siteconfig.get('saml_login_button_text')

    @cached_property
    def login_url(self):
        """The URL to the login page.

        Type:
            str
        """
        return reverse(
            'sso:%s:login' % self.backend_id,
            kwargs={'backend_id': self.backend_id})

    @cached_property
    def urls(self):
        """A list of URLs to register for this backend.

        Type:
            list
        """
        return [
            path('metadata/',
                 SAMLMetadataView.as_view(sso_backend=self),
                 name='metadata'),
            path('acs/',
                 SAMLACSView.as_view(sso_backend=self),
                 name='acs'),
            path('sls/',
                 SAMLSLSView.as_view(sso_backend=self),
                 name='sls'),
            path('link-user/',
                 SAMLLinkUserView.as_view(sso_backend=self),
                 name='link-user'),
        ]

    def is_available(self):
        """Return whether this backend is available.

        Returns:
            tuple:
            A two-tuple. The items in the tuple are:

            1. A bool indicating whether the backend is available.
            2. If the first element is ``False``, this will be a user-visible
               string indicating the reason why the backend is not available.
               If the backend is available, this element will be ``None``.
        """
        if self._available is None:
            try:
                import_module('onelogin.saml2.constants')
                self._available = True
            except ImportError:
                self._available = False

        if self._available:
            return True, None
        else:
            return False, gettext(
                'To enable SAML 2.0 support, install the '
                '<code>ReviewBoard[saml]</code> Python package and restart '
                'the web server.')
