.. _sso-backend-hook:

==============
SSOBackendHook
==============

.. versionadded:: 9.0

:py:class:`reviewboard.extensions.hooks.SSOBackendHook` allows extensions to
register new single sign-on backends. These let users log in through an
external identity provider, alongside the standard login form.

Extensions must provide an instance of a
:py:class:`reviewboard.accounts.sso.backends.base.BaseSSOBackend` subclass,
and pass it as a parameter to :py:class:`SSOBackendHook`. Each backend must
provide unique :py:attr:`backend_id` and :py:attr:`name` attributes. The
backend's URLs are made available under ``/account/sso/<backend_id>/``, and
a login button is shown on the login page while the backend is enabled.

The built-in
:py:class:`reviewboard.accounts.sso.backends.saml.sso_backend.SAMLSSOBackend`
can be subclassed to add a second SAML identity provider. Subclasses can
override :py:meth:`get_setting` to provide the identity provider settings and
:py:meth:`get_username_for_sso_id` to map identities to Review Board
usernames.


Example
=======

.. code-block:: python

    from typing import Any

    from reviewboard.accounts.errors import LoginNotAllowedError
    from reviewboard.accounts.sso.backends.saml.sso_backend import (
        SAMLSSOBackend,
    )
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import SSOBackendHook


    class PartnerSAMLSSOBackend(SAMLSSOBackend):
        backend_id = 'saml-partner'
        name = 'Partner SAML'
        settings_form = None
        siteconfig_defaults = {}

        SETTINGS = {
            'login_button_text': 'Log in with Partner SSO',
            'issuer': 'https://idp.partner.example.com/',
            'sso_url': 'https://idp.partner.example.com/sso',
            'sso_binding_type': 'http-post',
            'slo_url': 'https://idp.partner.example.com/slo',
            'slo_binding_type': 'http-redirect',
            'verification_cert': '...',
            'nameid_format': 'persistent',
            'attr_email': 'User.email',
            'attr_firstname': 'User.FirstName',
            'attr_lastname': 'User.LastName',
            'attr_fullname': 'User.FullName',
            'automatically_provision_users': False,
            'require_login_to_link': False,
        }

        def get_setting(
            self,
            name: str,
            default: Any = None,
        ) -> Any:
            return self.SETTINGS.get(name, default)

        def is_enabled(self) -> bool:
            return True

        def get_username_for_sso_id(
            self,
            sso_id: str,
            user_attrs: dict[str, Any],
        ) -> str:
            username = lookup_partner_username(sso_id)

            if not username:
                raise LoginNotAllowedError()

            return username


    class SampleExtension(Extension):
        def initialize(self) -> None:
            SSOBackendHook(self, PartnerSAMLSSOBackend())
