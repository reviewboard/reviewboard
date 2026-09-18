"""SAML SSO backend.

Version Added:
    5.0
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from django.urls import path, reverse
from django.utils.translation import gettext, gettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import cached_property

from reviewboard.accounts.sso.backends.base import BaseSSOBackend
from reviewboard.accounts.sso.backends.saml.forms import SAMLSettingsForm
from reviewboard.accounts.sso.backends.saml.settings import (
    DEFAULT_ATTR_EMAIL,
    DEFAULT_ATTR_FIRSTNAME,
    DEFAULT_ATTR_FULLNAME,
    DEFAULT_ATTR_LASTNAME,
    SAMLBinding,
    SAMLDigestAlgorithm,
    SAMLNameIDFormat,
    SAMLSignatureAlgorithm,
)
from reviewboard.accounts.sso.backends.saml.settings import (
    get_saml2_settings,
)
from reviewboard.accounts.sso.backends.saml.views import (
    SAMLACSView,
    SAMLLinkUserView,
    SAMLLoginView,
    SAMLMetadataView,
    SAMLSLSView,
)

if TYPE_CHECKING:
    from typing import Any


class SAMLSSOBackend(BaseSSOBackend):
    """SAML SSO backend.

    This can be subclassed to support additional SAML identity providers.
    Subclasses must set a unique :py:attr:`backend_id`, and can override
    :py:meth:`get_setting` to provide settings from another source and
    :py:meth:`get_username_for_sso_id` to map identities to Review Board
    usernames.

    Version Changed:
        9.0:
        Added support for subclassing with a different :py:attr:`backend_id`.

    Version Added:
        5.0
    """

    backend_id = 'saml'
    name = _('SAML 2.0')
    settings_form = SAMLSettingsForm
    siteconfig_defaults = {
        'saml_attr_email': DEFAULT_ATTR_EMAIL,
        'saml_attr_firstname': DEFAULT_ATTR_FIRSTNAME,
        'saml_attr_fullname': DEFAULT_ATTR_FULLNAME,
        'saml_attr_lastname': DEFAULT_ATTR_LASTNAME,
        'saml_automatically_provision_users': True,
        'saml_digest_algorithm': SAMLDigestAlgorithm.SHA1,
        'saml_enabled': False,
        'saml_issuer': '',
        'saml_login_button_text': _('Log in with SAML SSO'),
        'saml_nameid_format': SAMLNameIDFormat.PERSISTENT,
        'saml_require_login_to_link': True,
        'saml_signature_algorithm': SAMLSignatureAlgorithm.DSA_SHA1,
        'saml_slo_binding_type': SAMLBinding.HTTP_REDIRECT,
        'saml_slo_url': '',
        'saml_sso_binding_type': SAMLBinding.HTTP_POST,
        'saml_sso_url': '',
        'saml_verification_cert': '',
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
        return self.get_setting('login_button_text')

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

    @property
    def linked_account_service_id(self) -> str:
        """The service ID used for linked accounts.

        Version Added:
            9.0

        Type:
            str
        """
        return f'sso:{self.backend_id}'

    def get_setting(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """Return a setting for this backend.

        By default, this reads ``<backend_id>_<name>`` from the
        :py:class:`~djblets.siteconfig.models.SiteConfiguration`.
        Subclasses can override this to read settings from another source.

        Version Added:
            9.0

        Args:
            name (str):
                The name of the setting, without the backend prefix.

            default (object, optional):
                The value to return if the setting is not set.

        Returns:
            object:
            The setting value.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        return siteconfig.get(f'{self.backend_id}_{name}', default)

    def get_saml2_settings(self) -> dict[str, Any]:
        """Return the settings for the SAML library.

        Version Added:
            9.0

        Returns:
            dict:
            The settings for :py:mod:`onelogin.saml2`.
        """
        return get_saml2_settings(backend=self)

    def get_username_for_sso_id(
        self,
        sso_id: str,
        user_attrs: dict[str, Any],
    ) -> str:
        """Return the Review Board username for an identity provider ID.

        This is called on the first login for an identity, before it is
        linked to a user. The result is used to find an existing user, or as
        the username when provisioning a new one. The linked account keeps
        the original identity, so this is not called again once linked.

        By default, the ID is used as the username.

        Subclasses may override this if they need to define their own mapping
        of identities to Review Board usernames.

        Version Added:
            9.0

        Args:
            sso_id (str):
                The NameID from the identity provider.

            user_attrs (dict):
                The attributes from the SAML assertion.

        Returns:
            str:
            The Review Board username to use.

        Raises:
            reviewboard.accounts.errors.LoginNotAllowedError:
                The user is not allowed to log in.
        """
        return sso_id

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
