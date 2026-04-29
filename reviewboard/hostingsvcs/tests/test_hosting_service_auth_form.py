"""Unit tests for BaseHostingServiceAuthForm."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

import kgb

from reviewboard.admin.server import get_data_dir
from reviewboard.certs.cert import Certificate, CertificateFingerprints
from reviewboard.certs.errors import (CertificateVerificationError,
                                      CertificateVerificationFailureCode)
from reviewboard.certs.manager import cert_manager
from reviewboard.certs.tests.testcases import TEST_SHA256, TEST_TRUST_CERT_PEM
from reviewboard.deprecation import (RemovedInReviewBoard10_0Warning,
                                     RemovedInReviewBoard90Warning)
from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceAuthForm
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.certs import Certificate as LegacyCertificate
from reviewboard.scmtools.errors import UnverifiedCertificateError
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase
from reviewboard.testing.hosting_services import (SelfHostedTestService,
                                                  TestService)

if TYPE_CHECKING:
    from djblets.testing.testcases import ExpectedWarning


class HostingServiceAuthFormTests(kgb.SpyAgency, TestCase):
    """Unit tests for BaseHostingServiceAuthForm."""

    fixtures = ['test_scmtools']

    def setUp(self) -> None:
        """Set up state for the test.

        This will clear out the certs directory before running a test.
        """
        super().setUp()

        hosting_service_registry.register(TestService)
        hosting_service_registry.register(SelfHostedTestService)
        shutil.rmtree(os.path.join(get_data_dir(), 'rb-certs'),
                      ignore_errors=True)

    def tearDown(self) -> None:
        """Tear down state for the test.

        This will clear out the certs directory after running a test.
        """
        hosting_service_registry.unregister(SelfHostedTestService)
        hosting_service_registry.unregister(TestService)
        shutil.rmtree(os.path.join(get_data_dir(), 'rb-certs'),
                      ignore_errors=True)

        super().tearDown()

    def test_override_help_texts(self):
        """Testing BaseHostingServiceAuthForm subclasses overriding help texts
        """
        class MyAuthForm(BaseHostingServiceAuthForm):
            class Meta:
                help_texts = {
                    'hosting_account_username': 'My help text.',
                }

        form = MyAuthForm(hosting_service_cls=TestService)

        self.assertEqual(form.fields['hosting_account_username'].help_text,
                         'My help text.')

    def test_override_labels(self):
        """Testing BaseHostingServiceAuthForm subclasses overriding labels"""
        class MyAuthForm(BaseHostingServiceAuthForm):
            class Meta:
                labels = {
                    'hosting_account_username': 'My label.',
                }

        form = MyAuthForm(hosting_service_cls=TestService)

        self.assertEqual(form.fields['hosting_account_username'].label,
                         'My label.')

    def test_get_credentials_default(self):
        """Testing BaseHostingServiceAuthForm.get_credentials default behavior
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.get_credentials(),
            {
                'username': 'myuser',
                'password': 'mypass',
            })

    def test_get_credentials_default_with_2fa_code(self):
        """Testing BaseHostingServiceAuthForm.get_credentials default behavior
        with two-factor auth code
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
                'hosting_account_two_factor_auth_code': '123456',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.get_credentials(),
            {
                'username': 'myuser',
                'password': 'mypass',
                'two_factor_auth_code': '123456',
            })

    def test_get_credentials_with_form_prefix(self):
        """Testing BaseHostingServiceAuthForm.get_credentials default behavior
        with form prefix
        """
        form = BaseHostingServiceAuthForm(
            {
                'myservice-hosting_account_username': 'myuser',
                'myservice-hosting_account_password': 'mypass',
                'myservice-hosting_account_two_factor_auth_code': '123456',
            },
            hosting_service_cls=TestService,
            prefix='myservice')

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.get_credentials(),
            {
                'username': 'myuser',
                'password': 'mypass',
                'two_factor_auth_code': '123456',
            })

    def test_save_new_account(self):
        """Testing BaseHostingServiceAuthForm.save with new account"""
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())

        hosting_account = form.save()

        self.assertIsNotNone(hosting_account.pk)
        self.assertEqual(hosting_account.service_name, 'test')
        self.assertEqual(hosting_account.username, 'myuser')
        self.assertEqual(hosting_account.data['password'], 'mypass')
        self.assertIsNone(hosting_account.hosting_url)
        self.assertIsNone(hosting_account.local_site)

    def test_save_new_account_with_existing_stored(self):
        """Testing BaseHostingServiceAuthForm.save with new account matching
        existing stored account information
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())

        orig_account = HostingServiceAccount.objects.create(
            service_name='test',
            username='myuser')

        hosting_account = form.save()

        self.assertIsNotNone(hosting_account.pk)
        self.assertEqual(hosting_account.pk, orig_account.pk)
        self.assertEqual(hosting_account.service_name, 'test')
        self.assertEqual(hosting_account.username, 'myuser')
        self.assertEqual(hosting_account.data['password'], 'mypass')
        self.assertIsNone(hosting_account.hosting_url)
        self.assertIsNone(hosting_account.local_site)

    def test_save_new_account_with_hosting_url(self):
        """Testing BaseHostingServiceAuthForm.save with new account and
        hosting URL
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
                'hosting_url': 'example.com',
            },
            hosting_service_cls=SelfHostedTestService)

        self.assertTrue(form.is_valid())

        hosting_account = form.save()

        self.assertIsNotNone(hosting_account.pk)
        self.assertEqual(hosting_account.service_name, 'self_hosted_test')
        self.assertEqual(hosting_account.username, 'myuser')
        self.assertEqual(hosting_account.data['password'], 'mypass')
        self.assertEqual(hosting_account.hosting_url, 'example.com')
        self.assertIsNone(hosting_account.local_site)

    def test_save_new_account_with_hosting_url_not_self_hosted(self):
        """Testing BaseHostingServiceAuthForm.save with new account and
        hosting URL with non-self-hosted service
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
                'hosting_url': 'example.com',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())
        self.assertNotIn('hosting_url', form.cleaned_data)

        hosting_account = form.save()
        self.assertIsNone(hosting_account.hosting_url)

    def test_save_new_account_without_hosting_url_self_hosted(self):
        """Testing BaseHostingServiceAuthForm.save with new account and no
        hosting URL with a self-hosted service
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=SelfHostedTestService)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'hosting_url': ['This field is required.'],
            })

    def test_save_new_account_with_local_site(self):
        """Testing BaseHostingServiceAuthForm.save with new account and Local
        Site
        """
        local_site = LocalSite.objects.create(name='test-site')
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService,
            local_site=local_site)

        self.assertTrue(form.is_valid())

        hosting_account = form.save()

        self.assertIsNotNone(hosting_account.pk)
        self.assertEqual(hosting_account.service_name, 'test')
        self.assertEqual(hosting_account.username, 'myuser')
        self.assertEqual(hosting_account.data['password'], 'mypass')
        self.assertEqual(hosting_account.local_site, local_site)
        self.assertIsNone(hosting_account.hosting_url)

    def test_save_new_account_without_username(self):
        """Testing BaseHostingServiceAuthForm.save with new account and no
        username in credentials
        """
        class MyAuthForm(BaseHostingServiceAuthForm):
            def get_credentials(self):
                return {}

        form = MyAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())

        expected_message = (
            'Hosting service implementation error: '
            'MyAuthForm.get_credentials() must return a "username" key.'
        )

        with self.assertRaisesMessage(AuthorizationError, expected_message):
            form.save()

    def test_save_existing_account(self):
        """Testing BaseHostingServiceAuthForm.save with updating existing
        account
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='test',
            username='myuser')

        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService,
            hosting_account=orig_account)

        self.assertTrue(form.is_valid())

        hosting_account = form.save()

        self.assertIs(hosting_account, orig_account)
        self.assertEqual(hosting_account.pk, orig_account.pk)
        self.assertEqual(hosting_account.service_name, 'test')
        self.assertEqual(hosting_account.username, 'myuser')
        self.assertEqual(hosting_account.data['password'], 'mypass')
        self.assertIsNone(hosting_account.hosting_url)
        self.assertIsNone(hosting_account.local_site)

    def test_save_existing_account_new_username(self):
        """Testing BaseHostingServiceAuthForm.save with updating existing
        account with new username
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='test',
            username='myuser')

        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'mynewuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService,
            hosting_account=orig_account)

        self.assertTrue(form.is_valid())

        hosting_account = form.save()

        self.assertIs(hosting_account, orig_account)
        self.assertEqual(hosting_account.pk, orig_account.pk)
        self.assertEqual(hosting_account.service_name, 'test')
        self.assertEqual(hosting_account.username, 'mynewuser')
        self.assertEqual(hosting_account.data['password'], 'mypass')
        self.assertIsNone(hosting_account.hosting_url)
        self.assertIsNone(hosting_account.local_site)

    def test_save_existing_account_new_hosting_url(self):
        """Testing BaseHostingServiceAuthForm.save with updating existing
        account with new hosting URL
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='self_hosted_test',
            username='myuser',
            hosting_url='example1.com')

        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
                'hosting_url': 'example2.com',
            },
            hosting_service_cls=SelfHostedTestService,
            hosting_account=orig_account)

        self.assertTrue(form.is_valid())

        hosting_account = form.save()

        self.assertIs(hosting_account, orig_account)
        self.assertEqual(hosting_account.pk, orig_account.pk)
        self.assertEqual(hosting_account.service_name, 'self_hosted_test')
        self.assertEqual(hosting_account.username, 'myuser')
        self.assertEqual(hosting_account.data['password'], 'mypass')
        self.assertEqual(hosting_account.hosting_url, 'example2.com')
        self.assertIsNone(hosting_account.local_site)

    def test_save_existing_account_new_service_fails(self):
        """Testing BaseHostingServiceAuthForm.save with updating existing
        account with new hosting service fails
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='self_hosted_test',
            username='myuser',
            hosting_url='example1.com')

        expected_message = (
            'This account is not compatible with this hosting service '
            'configuration.'
        )

        with self.assertRaisesMessage(ValueError, expected_message):
            BaseHostingServiceAuthForm(hosting_service_cls=TestService,
                                   hosting_account=orig_account)

    def test_save_existing_account_new_local_site_fails(self):
        """Testing BaseHostingServiceAuthForm.save with updating existing
        account with new Local Site fails
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='text',
            username='myuser')

        expected_message = (
            'This account is not compatible with this hosting service '
            'configuration.'
        )

        with self.assertRaisesMessage(ValueError, expected_message):
            BaseHostingServiceAuthForm(
                hosting_service_cls=TestService,
                hosting_account=orig_account,
                local_site=LocalSite.objects.create(name='test-site'))

    def test_save_with_2fa_code_required(self):
        """Testing BaseHostingServiceAuthForm.save with two-factor auth code
        required
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': '2fa-user',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())

        self.assertFalse(
            form.fields['hosting_account_two_factor_auth_code'].required)

        with self.assertRaises(TwoFactorAuthCodeRequiredError):
            form.save()

        self.assertTrue(
            form.fields['hosting_account_two_factor_auth_code'].required)

    def test_save_with_2fa_code_provided(self):
        """Testing BaseHostingServiceAuthForm.save with two-factor auth code
        provided
        """
        form = BaseHostingServiceAuthForm(
            {
                'hosting_account_username': '2fa-user',
                'hosting_account_password': 'mypass',
                'hosting_account_two_factor_auth_code': '123456',
            },
            hosting_service_cls=TestService)

        self.assertTrue(form.is_valid())

        hosting_account = form.save()
        self.assertEqual(hosting_account.service_name, 'test')
        self.assertEqual(hosting_account.username, '2fa-user')

    def test_save_with_cert_error(self) -> None:
        """Testing BaseHostingServiceAuthForm.save with
        UnverifiedCertificateError
        """
        fingerprints = CertificateFingerprints(sha256=TEST_SHA256)

        class _MyAuthForm(BaseHostingServiceAuthForm):
            def authorize(self, *args, **kwargs) -> None:
                verified = cert_manager.is_certificate_verified(
                    hostname='example.com',
                    port=443,
                    latest_fingerprints=fingerprints,
                )

                if not verified:
                    raise CertificateVerificationError(
                        code=CertificateVerificationFailureCode.NOT_TRUSTED,
                        certificate=Certificate(
                            hostname='example.com',
                            port=443,
                            fingerprints=fingerprints,
                            cert_data=TEST_TRUST_CERT_PEM,
                        ),
                    )

        form = _MyAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService,
        )
        self.spy_on(form.authorize)

        self.assertTrue(form.is_valid())

        message = (
            'The SSL certificate provided by example.com has not been '
            'signed by a trusted Certificate Authority and may not be safe. '
            'The certificate needs to be verified in Review Board before '
            'the server can be accessed. Certificate details: '
            'hostname="example.com", port=443, issuer="example.com", '
            'fingerprint=SHA256=79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:B1:6A:'
            'AD:79:FF:F7:28:69:02:5E:C3:6F:B3:C2:B4:FD:84:66:DF:8F'
        )

        with self.assertRaisesMessage(CertificateVerificationError, message):
            form.save(allow_authorize=True)

        self.assertFalse(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=fingerprints,
        ))
        self.assertIsNone(cert_manager.get_certificate(
            hostname='example.com',
            port=443,
        ))
        self.assertSpyCallCount(form.authorize, 1)

    def test_save_with_cert_error_and_trust_host(self) -> None:
        """Testing BaseHostingServiceAuthForm.save with
        CertificateVerificationError and trust_host=True
        """
        fingerprints = CertificateFingerprints(sha256=TEST_SHA256)

        class _MyAuthForm(BaseHostingServiceAuthForm):
            def authorize(self, *args, **kwargs) -> None:
                verified = cert_manager.is_certificate_verified(
                    hostname='example.com',
                    port=443,
                    latest_fingerprints=fingerprints,
                )

                if not verified:
                    raise CertificateVerificationError(
                        code=CertificateVerificationFailureCode.NOT_TRUSTED,
                        certificate=Certificate(
                            hostname='example.com',
                            port=443,
                            fingerprints=fingerprints,
                            cert_data=TEST_TRUST_CERT_PEM,
                        ),
                    )

        self.assertFalse(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=fingerprints,
        ))

        form = _MyAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService,
        )
        self.spy_on(form.authorize)

        self.assertTrue(form.is_valid())

        form.save(allow_authorize=True,
                  trust_host=True)

        self.assertTrue(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=fingerprints,
        ))
        self.assertAttrsEqual(
            cert_manager.get_certificate(
                hostname='example.com',
                port=443,
            ),
            {
                'cert_data': TEST_TRUST_CERT_PEM,
                'hostname': 'example.com',
                'port': 443,
            })
        self.assertSpyCallCount(form.authorize, 2)

    def test_save_with_legacy_cert_error(self) -> None:
        """Testing BaseHostingServiceAuthForm.save with
        legacy UnverifiedCertificateError
        """
        fingerprints = CertificateFingerprints(sha256=TEST_SHA256)

        class _MyAuthForm(BaseHostingServiceAuthForm):
            def authorize(self, *args, **kwargs) -> None:
                verified = cert_manager.is_certificate_verified(
                    hostname='example.com',
                    port=443,
                    latest_fingerprints=fingerprints,
                )

                if not verified:
                    raise UnverifiedCertificateError(
                        certificate=LegacyCertificate(
                            pem_data=TEST_TRUST_CERT_PEM.decode('utf-8'),
                            issuer='issuer',
                            hostname='example.com',
                            fingerprint=TEST_SHA256.replace(':', '').lower(),
                        )
                    )

        form = _MyAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService,
        )
        self.spy_on(form.authorize)

        self.assertTrue(form.is_valid())

        warnings: list[ExpectedWarning] = [
            {
                'cls': RemovedInReviewBoard90Warning,
                'message': (
                    'UnverifiedCertificateError is deprecated in favor of '
                    'reviewboard.certs.errors.CertificateVerificationError, '
                    'and will be removed in Review Board 9.'
                ),
            },
        ]

        message = (
            'The SSL certificate for this repository (hostname '
            '"example.com", fingerprint "791970aea61bebbc357cb854b16aad79f'
            'ff72869025ec36fb3c2b4fd8466df8f") was not verified and might '
            'not be safe. This certificate needs to be verified before the '
            'repository can be accessed.'
        )

        with (self.assertWarnings(warnings),
              self.assertRaisesMessage(UnverifiedCertificateError, message)):
            form.save(allow_authorize=True)

        self.assertFalse(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=fingerprints,
        ))
        self.assertIsNone(cert_manager.get_certificate(
            hostname='example.com',
            port=443,
        ))
        self.assertSpyCallCount(form.authorize, 1)

    def test_save_with_legacy_cert_error_and_trust_host(self) -> None:
        """Testing BaseHostingServiceAuthForm.save with
        legacy UnverifiedCertificateError and trust_host=True
        """
        fingerprints = CertificateFingerprints(sha256=TEST_SHA256)

        class _MyAuthForm(BaseHostingServiceAuthForm):
            def authorize(self, *args, **kwargs) -> None:
                verified = cert_manager.is_certificate_verified(
                    hostname='example.com',
                    port=443,
                    latest_fingerprints=fingerprints,
                )

                if not verified:
                    raise UnverifiedCertificateError(
                        certificate=LegacyCertificate(
                            pem_data=TEST_TRUST_CERT_PEM.decode('utf-8'),
                            issuer='issuer',
                            hostname='example.com',
                            fingerprint=TEST_SHA256.replace(':', '').lower(),
                        )
                    )

        self.assertFalse(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=fingerprints,
        ))

        form = _MyAuthForm(
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=TestService,
        )
        self.spy_on(form.authorize)

        self.assertTrue(form.is_valid())

        warnings: list[ExpectedWarning] = [
            {
                'cls': RemovedInReviewBoard90Warning,
                'message': (
                    'UnverifiedCertificateError is deprecated in favor of '
                    'reviewboard.certs.errors.CertificateVerificationError, '
                    'and will be removed in Review Board 9.'
                ),
            },
            {
                'cls': RemovedInReviewBoard10_0Warning,
                'message': (
                    'HostingServiceAccount.accept_certificate() is '
                    'deprecated and will be removed in Review Board 10. '
                    'Use cert_manager.add_certificate() instead.'
                ),
            },
        ]

        with self.assertWarnings(warnings):
            form.save(allow_authorize=True,
                      trust_host=True)

        self.assertTrue(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=fingerprints,
        ))
        self.assertAttrsEqual(
            cert_manager.get_certificate(
                hostname='example.com',
                port=443,
            ),
            {
                'cert_data': TEST_TRUST_CERT_PEM,
                'hostname': 'example.com',
                'port': 443,
            })
        self.assertSpyCallCount(form.authorize, 2)
