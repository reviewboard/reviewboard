"""Settings for SAML SSO.

Version Added:
    5.0
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration
try:
    from onelogin.saml2.constants import OneLogin_Saml2_Constants as constants
except ImportError:
    constants = None

from reviewboard.admin.server import build_server_url


class SAMLSignatureAlgorithm(object):
    """Definitions for the signature algorithm.

    Version Added:
        5.0
    """

    DSA_SHA1 = 'dsa-sha1'
    RSA_SHA1 = 'rsa-sha1'
    RSA_SHA256 = 'rsa-sha256'
    RSA_SHA384 = 'rsa-sha384'
    RSA_SHA512 = 'rsa-sha512'

    CHOICES = (
        (DSA_SHA1, 'DSA-SHA1'),
        (RSA_SHA1, 'RSA-SHA1'),
        (RSA_SHA256, 'RSA-SHA256'),
        (RSA_SHA384, 'RSA-SHA384'),
        (RSA_SHA512, 'RSA-SHA512'),
    )

    if constants:
        TO_SAML2_SETTING_MAP = {
            DSA_SHA1: constants.DSA_SHA1,
            RSA_SHA1: constants.RSA_SHA1,
            RSA_SHA256: constants.RSA_SHA256,
            RSA_SHA384: constants.RSA_SHA384,
            RSA_SHA512: constants.RSA_SHA512,
        }

        FROM_SAML2_SETTING_MAP = {
            constants.DSA_SHA1: DSA_SHA1,
            constants.RSA_SHA1: RSA_SHA1,
            constants.RSA_SHA256: RSA_SHA256,
            constants.RSA_SHA384: RSA_SHA384,
            constants.RSA_SHA512: RSA_SHA512,
        }
    else:
        TO_SAML2_SETTING_MAP = {}
        FROM_SAML2_SETTING_MAP = {}


class SAMLDigestAlgorithm(object):
    """Definitions for the digest algorithm.

    Version Added:
        5.0
    """

    SHA1 = 'sha1'
    SHA256 = 'sha256'
    SHA384 = 'sha384'
    SHA512 = 'sha512'

    CHOICES = (
        (SHA1, 'SHA1'),
        (SHA256, 'SHA256'),
        (SHA384, 'SHA384'),
        (SHA512, 'SHA512'),
    )

    if constants:
        TO_SAML2_SETTING_MAP = {
            SHA1: constants.SHA1,
            SHA256: constants.SHA256,
            SHA384: constants.SHA384,
            SHA512: constants.SHA512,
        }

        FROM_SAML2_SETTING_MAP = {
            constants.SHA1: SHA1,
            constants.SHA256: SHA256,
            constants.SHA384: SHA384,
            constants.SHA512: SHA512,
        }
    else:
        TO_SAML2_SETTING_MAP = {}
        FROM_SAML2_SETTING_MAP = {}


class SAMLBinding(object):
    """Definitions for the binding type.

    Version Added:
        5.0
    """

    HTTP_POST = 'http-post'
    HTTP_REDIRECT = 'http-redirect'

    CHOICES = (
        (HTTP_POST, _('HTTP POST')),
        (HTTP_REDIRECT, _('HTTP Redirect')),
    )

    if constants:
        TO_SAML2_SETTING_MAP = {
            HTTP_POST: constants.BINDING_HTTP_POST,
            HTTP_REDIRECT: constants.BINDING_HTTP_REDIRECT,
        }

        FROM_SAML2_SETTING_MAP = {
            constants.BINDING_HTTP_POST: HTTP_POST,
            constants.BINDING_HTTP_REDIRECT: HTTP_REDIRECT,
        }
    else:
        TO_SAML2_SETTING_MAP = {}
        FROM_SAML2_SETTING_MAP = {}


def get_saml2_settings():
    """Return the SAML2.0 settings.

    Version Added:
        5.0

    Returns:
        dict:
        A dictionary of the settings to use for SAML operations.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    assert constants is not None
    return {
        'strict': True,
        'debug': True,
        'idp': {
            'entityId': siteconfig.get('saml_issuer'),
            'singleSignOnService': {
                'url': siteconfig.get('saml_sso_url'),
                'binding': SAMLBinding.TO_SAML2_SETTING_MAP[
                    siteconfig.get('saml_sso_binding_type')],
            },
            'singleLogoutService': {
                'url': siteconfig.get('saml_slo_url'),
                'binding': SAMLBinding.TO_SAML2_SETTING_MAP[
                    siteconfig.get('saml_slo_binding_type')],
            },
            'x509cert': siteconfig.get('saml_verification_cert'),
        },
        'sp': {
            'entityId': build_server_url(
                reverse('sso:saml:metadata', kwargs={'backend_id': 'saml'})),
            'assertionConsumerService': {
                'url': build_server_url(
                    reverse('sso:saml:acs', kwargs={'backend_id': 'saml'})),
                'binding': constants.BINDING_HTTP_POST,
            },
            'singleLogoutService': {
                'url': build_server_url(
                    reverse('sso:saml:sls', kwargs={'backend_id': 'saml'})),
                'binding': constants.BINDING_HTTP_REDIRECT,
            },
            'NameIDFormat': constants.NAMEID_PERSISTENT,
            'x509cert': '',
            'privateKey': '',
        },
    }
