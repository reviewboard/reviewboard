from __future__ import unicode_literals

import nose

from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.models import Repository, Tool


class AssemblaTests(ServiceTests):
    """Unit tests for the Assembla hosting service."""

    service_name = 'assembla'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Assembla service support capabilities"""
        self.assertTrue(self.service_class.needs_authorization)
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertEqual(self.service_class.supported_scmtools,
                         ['Perforce', 'Subversion'])

    def test_repo_field_values_perforce(self):
        """Testing Assembla repository field values for Perforce"""
        fields = self._get_repository_fields('Perforce', fields={
            'assembla_project_id': 'myproject',
        })
        self.assertEqual(fields['path'], 'perforce.assembla.com:1666')
        self.assertNotIn('mirror_path', fields)
        self.assertIn('encoding', fields)
        self.assertEqual(fields['encoding'], 'utf8')

    def test_repo_field_values_subversion(self):
        """Testing Assembla repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'assembla_project_id': 'myproject',
            'assembla_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'https://subversion.assembla.com/svn/myproject/')
        self.assertNotIn('mirror_path', fields)
        self.assertNotIn('encoding', fields)

    def test_save_form_perforce(self):
        """Testing Assembla configuration form with Perforce"""
        try:
            account = self._get_hosting_account()
            service = account.service
            service.authorize('myuser', 'abc123', None)

            repository = Repository(hosting_account=account,
                                    tool=Tool.objects.get(name='Perforce'))

            form = self._get_form(fields={'assembla_project_id': 'myproject'})
            form.save(repository)

            self.assertIn('use_ticket_auth', repository.extra_data)
            self.assertTrue(repository.extra_data['use_ticket_auth'])
            self.assertIn('p4_host', repository.extra_data)
            self.assertEqual(repository.extra_data['p4_host'], 'myproject')
        except ImportError:
            raise nose.SkipTest

    def test_save_form_subversion(self):
        """Testing Assembla configuration form with Subversion"""
        try:
            account = self._get_hosting_account()
            service = account.service
            service.authorize('myuser', 'abc123', None)

            repository = Repository(path='https://svn.example.com/',
                                    hosting_account=account,
                                    tool=Tool.objects.get(name='Subversion'))

            form = self._get_form(fields={'assembla_project_id': 'myproject'})
            form.save(repository)

            self.assertNotIn('use_ticket_auth', repository.extra_data)
            self.assertNotIn('p4_host', repository.extra_data)
        except ImportError:
            raise nose.SkipTest

    def test_authorize(self):
        """Testing Assembla authorization password storage"""
        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_check_repository_perforce(self):
        """Testing Assembla check_repository with Perforce"""
        try:
            account = self._get_hosting_account()
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
            self.assertEqual(scmtool.check_repository.last_call.kwargs['p4_host'],
                             'myproject')
        except ImportError:
            raise nose.SkipTest

    def test_check_repository_subversion(self):
        """Testing Assembla check_repository with Subversion"""
        try:
            account = self._get_hosting_account()
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
            self.assertNotIn('p4_host', scmtool.check_repository.last_call.kwargs)
        except ImportError:
            raise nose.SkipTest
