"""Unit tests for the Assembla hosting service."""

from __future__ import unicode_literals

import nose

from reviewboard.admin.server import get_hostname
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.models import Repository, Tool


class AssemblaTestCase(HostingServiceTestCase):
    """Base class for Assembla test suites."""

    service_name = 'assembla'
    fixtures = ['test_scmtools']

    default_account_data = {
        'password': encrypt_password('abc123'),
    }


class AssemblaTests(AssemblaTestCase):
    """Unit tests for the Assembla hosting service."""

    def test_service_support(self):
        """Testing Assembla service support capabilities"""
        self.assertTrue(self.service_class.needs_authorization)
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertEqual(self.service_class.supported_scmtools,
                         ['Perforce', 'Subversion'])

    def test_get_repository_fields_with_perforce(self):
        """Testing Assembla.get_repository_fields for Perforce"""
        self.assertEqual(
            self.get_repository_fields(
                'Perforce',
                fields={
                    'assembla_project_id': 'myproject',
                }
            ),
            {
                'path': 'perforce.assembla.com:1666',
                'encoding': 'utf8',
            })

    def test_get_repository_fields_with_subversion(self):
        """Testing Assembla.get_repository_fields for Subversion"""
        self.assertEqual(
            self.get_repository_fields(
                'Subversion',
                fields={
                    'assembla_project_id': 'myproject',
                    'assembla_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'https://subversion.assembla.com/svn/myproject/',
            })

    def test_authorize(self):
        """Testing Assembla.authorize"""
        account = self.create_hosting_account(data={})
        service = account.service

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_check_repository_perforce(self):
        """Testing Assembla.check_repository with Perforce"""
        try:
            account = self.create_hosting_account()
            service = account.service

            service.authorize('myuser', 'abc123', None)

            repository = Repository(hosting_account=account,
                                    tool=Tool.objects.get(name='Perforce'))
            scmtool = repository.get_scmtool()
            self.spy_on(scmtool.check_repository, call_original=False)

            service.check_repository(path='mypath',
                                     username='myusername',
                                     password='mypassword',
                                     scmtool_class=scmtool.__class__,
                                     local_site_name=None,
                                     assembla_project_id='myproject')

            self.assertTrue(scmtool.check_repository.called)
            self.assertIn('p4_host', scmtool.check_repository.last_call.kwargs)
            self.assertEqual(
                scmtool.check_repository.last_call.kwargs['p4_host'],
                'myproject')
        except ImportError:
            raise nose.SkipTest

    def test_check_repository_subversion(self):
        """Testing Assembla.check_repository with Subversion"""
        try:
            account = self.create_hosting_account()
            service = account.service

            service.authorize('myuser', 'abc123', None)

            repository = Repository(path='https://svn.example.com/',
                                    hosting_account=account,
                                    tool=Tool.objects.get(name='Subversion'))
            scmtool = repository.get_scmtool()
            self.spy_on(scmtool.check_repository, call_original=False)

            service.check_repository(path='https://svn.example.com/',
                                     username='myusername',
                                     password='mypassword',
                                     scmtool_class=scmtool.__class__,
                                     local_site_name=None)

            self.assertTrue(scmtool.check_repository.called)
            self.assertNotIn('p4_host',
                             scmtool.check_repository.last_call.kwargs)
        except ImportError:
            raise nose.SkipTest


class AssemblaFormTests(AssemblaTestCase):
    """Unit tests for reviewboard.hostingsvcs.assembla.AssemblaForm."""

    def setUp(self):
        super(AssemblaFormTests, self).setUp()

        self.account = self.create_hosting_account()

    def test_save_form_perforce(self):
        """Testing AssemblaForm with Perforce"""
        try:
            repository = self.create_repository(hosting_account=self.account,
                                                tool_name='Perforce')

            form = self.get_form(fields={'assembla_project_id': 'myproject'})
            self.spy_on(get_hostname,
                        call_fake=lambda: 'myhost.example.com')

            form.save(repository)

            self.assertIn('use_ticket_auth', repository.extra_data)
            self.assertTrue(repository.extra_data['use_ticket_auth'])
            self.assertIn('p4_host', repository.extra_data)
            self.assertIn('p4_client', repository.extra_data)
            self.assertEqual(repository.extra_data['p4_host'], 'myproject')
            self.assertEqual(repository.extra_data['p4_client'],
                             'myhost.example.com-myproject')
        except ImportError:
            raise nose.SkipTest('Perforce support is not installed')

    def test_save_form_perforce_with_portfolio(self):
        """Testing AssemblaForm with Perforce and Assembla portfolio IDs"""
        try:
            repository = self.create_repository(hosting_account=self.account,
                                                tool_name='Perforce')

            form = self.get_form(fields={
                'assembla_project_id': 'myportfolio/myproject',
            })
            self.spy_on(get_hostname,
                        call_fake=lambda: 'myhost.example.com')

            form.save(repository)

            self.assertIn('use_ticket_auth', repository.extra_data)
            self.assertTrue(repository.extra_data['use_ticket_auth'])
            self.assertIn('p4_host', repository.extra_data)
            self.assertIn('p4_client', repository.extra_data)
            self.assertEqual(repository.extra_data['p4_host'],
                             'myportfolio/myproject')
            self.assertEqual(repository.extra_data['p4_client'],
                             'myhost.example.com-myportfolio-myproject')
        except ImportError:
            raise nose.SkipTest('Perforce support is not installed')

    def test_save_form_subversion(self):
        """Testing AssemblaForm with Subversion"""
        try:
            repository = self.create_repository(
                path='https://svn.example.com/',
                hosting_account=self.account,
                tool_name='Subversion')

            form = self.get_form(fields={'assembla_project_id': 'myproject'})
            form.save(repository)

            self.assertNotIn('use_ticket_auth', repository.extra_data)
            self.assertNotIn('p4_host', repository.extra_data)
        except ImportError:
            raise nose.SkipTest
