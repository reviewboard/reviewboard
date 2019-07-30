from __future__ import unicode_literals

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.forms import HostingServiceAuthForm
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.scmtools.models import Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase
from reviewboard.testing.hosting_services import (SelfHostedTestService,
                                                  TestService)


class HostingServiceAuthFormTests(TestCase):
    """Unit tests for reviewboard.hostingsvcs.forms.HostingServiceAuthForm."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(HostingServiceAuthFormTests, self).setUp()

        register_hosting_service(TestService.hosting_service_id, TestService)
        register_hosting_service(SelfHostedTestService.hosting_service_id,
                                 SelfHostedTestService)

        self.git_tool_id = Tool.objects.get(name='Git').pk

    def tearDown(self):
        super(HostingServiceAuthFormTests, self).tearDown()

        unregister_hosting_service(SelfHostedTestService.hosting_service_id)
        unregister_hosting_service(TestService.hosting_service_id)

    def test_override_help_texts(self):
        """Testing HostingServiceAuthForm subclasses overriding help texts"""
        class MyAuthForm(HostingServiceAuthForm):
            class Meta:
                help_texts = {
                    'hosting_account_username': 'My help text.',
                }

        form = MyAuthForm(hosting_service_cls=TestService)

        self.assertEqual(form.fields['hosting_account_username'].help_text,
                         'My help text.')

    def test_override_labels(self):
        """Testing HostingServiceAuthForm subclasses overriding labels"""
        class MyAuthForm(HostingServiceAuthForm):
            class Meta:
                labels = {
                    'hosting_account_username': 'My label.',
                }

        form = MyAuthForm(hosting_service_cls=TestService)

        self.assertEqual(form.fields['hosting_account_username'].label,
                         'My label.')

    def test_get_credentials_default(self):
        """Testing HostingServiceAuthForm.get_credentials default behavior"""
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.get_credentials default behavior
        with two-factor auth code
        """
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.get_credentials default behavior
        with form prefix
        """
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with new account"""
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with new account matching
        existing stored account information
        """
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with new account and hosting URL
        """
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with new account and hosting URL
        with non-self-hosted service
        """
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with new account and no
        hosting URL with a self-hosted service
        """
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with new account and Local Site
        """
        local_site = LocalSite.objects.create(name='test-site')
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with new account and no
        username in credentials
        """
        class MyAuthForm(HostingServiceAuthForm):
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
        """Testing HostingServiceAuthForm.save with updating existing account
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='test',
            username='myuser')

        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with updating existing account
        with new username
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='test',
            username='myuser')

        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with updating existing account
        with new hosting URL
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='self_hosted_test',
            username='myuser',
            hosting_url='example1.com')

        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with updating existing account
        with new hosting service fails
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
            HostingServiceAuthForm(hosting_service_cls=TestService,
                                   hosting_account=orig_account)

    def test_save_existing_account_new_local_site_fails(self):
        """Testing HostingServiceAuthForm.save with updating existing account
        with new Local Site fails
        """
        orig_account = HostingServiceAccount.objects.create(
            service_name='text',
            username='myuser')

        expected_message = (
            'This account is not compatible with this hosting service '
            'configuration.'
        )

        with self.assertRaisesMessage(ValueError, expected_message):
            HostingServiceAuthForm(
                hosting_service_cls=TestService,
                hosting_account=orig_account,
                local_site=LocalSite.objects.create(name='test-site'))

    def test_save_with_2fa_code_required(self):
        """Testing HostingServiceAuthForm.save with two-factor auth code
        required
        """
        form = HostingServiceAuthForm(
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
        """Testing HostingServiceAuthForm.save with two-factor auth code
        provided
        """
        form = HostingServiceAuthForm(
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
