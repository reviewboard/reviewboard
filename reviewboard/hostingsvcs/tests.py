from __future__ import print_function, unicode_literals

import hashlib
import hmac
import json
from hashlib import md5
from textwrap import dedent

from django.conf.urls import patterns, url
from django.core.urlresolvers import NoReverseMatch
from django.http import HttpResponse
from django.utils import six
from django.utils.six.moves import cStringIO as StringIO
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import urlparse
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            RepositoryError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.forms import HostingServiceAuthForm
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (get_hosting_service,
                                             HostingService,
                                             register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.core import Branch
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase
from reviewboard.testing.hosting_services import (SelfHostedTestService,
                                                  TestService)


class ServiceTests(SpyAgency, TestCase):
    service_name = None

    def __init__(self, *args, **kwargs):
        super(ServiceTests, self).__init__(*args, **kwargs)

        self.assertNotEqual(self.service_name, None)
        self.service_class = get_hosting_service(self.service_name)

    def setUp(self):
        super(ServiceTests, self).setUp()
        self.assertNotEqual(self.service_class, None)

    def _get_repository_info(self, field, plan=None):
        if plan:
            self.assertNotEqual(self.service_class.plans, None)
            result = None

            for plan_type, info in self.service_class.plans:
                if plan_type == plan:
                    result = info[field]
                    break

            self.assertNotEqual(result, None)
            return result
        else:
            self.assertEqual(self.service_class.plans, None)
            self.assertTrue(hasattr(self.service_class, field))

            return getattr(self.service_class, field)

    def _get_form(self, plan=None, fields={}):
        form = self._get_repository_info('form', plan)
        self.assertNotEqual(form, None)

        form = form(fields)
        self.assertTrue(form.is_valid())

        return form

    def _get_hosting_account(self, use_url=False, local_site=None):
        if use_url:
            hosting_url = 'https://example.com'
        else:
            hosting_url = None

        return HostingServiceAccount(service_name=self.service_name,
                                     username='myuser',
                                     hosting_url=hosting_url,
                                     local_site=local_site)

    def _get_service(self):
        return self._get_hosting_account().service

    def _get_repository_fields(self, tool_name, fields, plan=None,
                               with_url=False, hosting_account=None):
        form = self._get_form(plan, fields)

        if not hosting_account:
            hosting_account = self._get_hosting_account(with_url)

        service = hosting_account.service
        self.assertNotEqual(service, None)

        field_vars = form.clean().copy()

        field_vars.update(hosting_account.data)

        return service.get_repository_fields(username=hosting_account.username,
                                             hosting_url='https://example.com',
                                             plan=plan,
                                             tool_name=tool_name,
                                             field_vars=field_vars)


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

    def test_save_form_subversion(self):
        """Testing Assembla configuration form with Subversion"""
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

    def test_check_repository_subversion(self):
        """Testing Assembla check_repository with Subversion"""
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


class BeanstalkTests(ServiceTests):
    """Unit tests for the Beanstalk hosting service."""
    service_name = 'beanstalk'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Beanstalk service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_git(self):
        """Testing Beanstalk repository field values for Git"""
        fields = self._get_repository_fields('Git', fields={
            'beanstalk_account_domain': 'mydomain',
            'beanstalk_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'git@mydomain.beanstalkapp.com:/mydomain/myrepo.git')
        self.assertEqual(
            fields['mirror_path'],
            'https://mydomain.git.beanstalkapp.com/myrepo.git')

    def test_repo_field_values_subversion(self):
        """Testing Beanstalk repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'beanstalk_account_domain': 'mydomain',
            'beanstalk_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'https://mydomain.svn.beanstalkapp.com/myrepo/')
        self.assertNotIn('mirror_path', fields)

    def test_authorize(self):
        """Testing Beanstalk authorization password storage"""
        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_check_repository(self):
        """Testing Beanstalk check_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.beanstalkapp.com/api/repositories/'
                'myrepo.json')
            return '{}', {}

        account = self._get_hosting_account()
        service = account.service

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(beanstalk_account_domain='mydomain',
                                 beanstalk_repo_name='myrepo')
        self.assertTrue(service.client.http_get.called)

    def test_get_file_with_svn_and_base_commit_id(self):
        """Testing Beanstalk get_file with Subversion and base commit ID"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='123')

    def test_get_file_with_svn_and_revision(self):
        """Testing Beanstalk get_file with Subversion and revision"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_with_git_and_base_commit_id(self):
        """Testing Beanstalk get_file with Git and base commit ID"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='123')

    def test_get_file_with_git_and_revision(self):
        """Testing Beanstalk get_file with Git and revision"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_exists_with_svn_and_base_commit_id(self):
        """Testing Beanstalk get_file_exists with Subversion and base commit ID
        """
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_svn_and_revision(self):
        """Testing Beanstalk get_file_exists with Subversion and revision"""
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_git_and_base_commit_id(self):
        """Testing Beanstalk get_file_exists with Git and base commit ID"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_git_and_revision(self):
        """Testing Beanstalk get_file_exists with Git and revision"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def _test_get_file(self, tool_name, revision, base_commit_id,
                       expected_revision):
        def _http_get(service, url, *args, **kwargs):
            if tool_name == 'Git':
                self.assertEqual(
                    url,
                    'https://mydomain.beanstalkapp.com/api/repositories/'
                    'myrepo/blob?id=%s&name=path'
                    % expected_revision)
                payload = b'My data'
            else:
                self.assertEqual(
                    url,
                    'https://mydomain.beanstalkapp.com/api/repositories/'
                    'myrepo/node.json?path=/path&revision=%s&contents=true'
                    % expected_revision)
                payload = b'{"contents": "My data"}'

            return payload, {}

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'beanstalk_account_domain': 'mydomain',
            'beanstalk_repo_name': 'myrepo',
        }

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file(repository, '/path', revision,
                                  base_commit_id)
        self.assertTrue(service.client.http_get.called)
        self.assertEqual(result, 'My data')

    def _test_get_file_exists(self, tool_name, revision, base_commit_id,
                              expected_revision, expected_found):
        def _http_get(service, url, *args, **kwargs):
            expected_url = ('https://mydomain.beanstalkapp.com/api/'
                            'repositories/myrepo/')

            if not base_commit_id and tool_name == 'Git':
                expected_url += 'blob?id=%s&name=path' % expected_revision
            else:
                expected_url += ('node.json?path=/path&revision=%s'
                                 % expected_revision)

            self.assertEqual(url, expected_url)

            if expected_found:
                return b'{}', {}
            else:
                raise HTTPError()

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'beanstalk_account_domain': 'mydomain',
            'beanstalk_repo_name': 'myrepo',
        }

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, '/path', revision,
                                         base_commit_id)
        self.assertTrue(service.client.http_get.called)
        self.assertEqual(result, expected_found)


class BitbucketTests(ServiceTests):
    """Unit tests for the Bitbucket hosting service."""
    service_name = 'bitbucket'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Bitbucket service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_personal_repo_field_values_git(self):
        """Testing Bitbucket personal repository field values for Git"""
        fields = self._get_repository_fields(
            'Git',
            fields={
                'bitbucket_repo_name': 'myrepo',
            },
            plan='personal')
        self.assertEqual(fields['path'],
                         'git@bitbucket.org:myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'https://myuser@bitbucket.org/myuser/myrepo.git')

    def test_personal_repo_field_values_mercurial(self):
        """Testing Bitbucket personal repository field values for Mercurial"""
        fields = self._get_repository_fields(
            'Mercurial',
            fields={
                'bitbucket_repo_name': 'myrepo',
            },
            plan='personal')
        self.assertEqual(fields['path'],
                         'https://myuser@bitbucket.org/myuser/myrepo')
        self.assertEqual(fields['mirror_path'],
                         'ssh://hg@bitbucket.org/myuser/myrepo')

    def test_personal_bug_tracker_field(self):
        """Testing Bitbucket personal bug tracker field values"""
        self.assertTrue(self.service_class.get_bug_tracker_requires_username(
            plan='personal'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field(
                'personal',
                {
                    'bitbucket_repo_name': 'myrepo',
                    'hosting_account_username': 'myuser',
                }),
            'https://bitbucket.org/myuser/myrepo/issue/%s/')

    def test_personal_check_repository(self):
        """Testing Bitbucket personal check_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/1.0/repositories/myuser/myrepo')
            return b'{}', {}

        account = self._get_hosting_account()
        account.data['password'] = encrypt_password('abc123')
        service = account.service

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(bitbucket_repo_name='myrepo',
                                 plan='personal')
        self.assertTrue(service.client.http_get.called)

    def test_team_repo_field_values_git(self):
        """Testing Bitbucket team repository field values for Git"""
        fields = self._get_repository_fields(
            'Git',
            fields={
                'bitbucket_team_name': 'myteam',
                'bitbucket_team_repo_name': 'myrepo',
            },
            plan='team')
        self.assertEqual(fields['path'],
                         'git@bitbucket.org:myteam/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'https://myuser@bitbucket.org/myteam/myrepo.git')

    def test_team_repo_field_values_mercurial(self):
        """Testing Bitbucket team repository field values for Mercurial"""
        fields = self._get_repository_fields(
            'Mercurial',
            fields={
                'bitbucket_team_name': 'myteam',
                'bitbucket_team_repo_name': 'myrepo',
            },
            plan='team')
        self.assertEqual(fields['path'],
                         'https://myuser@bitbucket.org/myteam/myrepo')
        self.assertEqual(fields['mirror_path'],
                         'ssh://hg@bitbucket.org/myteam/myrepo')

    def test_team_bug_tracker_field(self):
        """Testing Bitbucket team bug tracker field values"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username(
            plan='team'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field(
                'team',
                {
                    'bitbucket_team_name': 'myteam',
                    'bitbucket_team_repo_name': 'myrepo',
                }),
            'https://bitbucket.org/myteam/myrepo/issue/%s/')

    def test_team_check_repository(self):
        """Testing Bitbucket team check_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/1.0/repositories/myteam/myrepo')
            return b'{}', {}

        account = self._get_hosting_account()
        service = account.service

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(bitbucket_team_name='myteam',
                                 bitbucket_team_repo_name='myrepo',
                                 plan='team')
        self.assertTrue(service.client.http_get.called)

    def test_check_repository_with_slash(self):
        """Testing Bitbucket check_repository with /"""
        account = self._get_hosting_account()
        account.data['password'] = encrypt_password('abc123')
        service = account.service

        self.assertRaisesMessage(
            RepositoryError,
            'Please specify just the name of the repository, not a path.',
            lambda: service.check_repository(
                bitbucket_team_name='myteam',
                bitbucket_team_repo_name='myteam/myrepo',
                plan='team'))

    def test_check_repository_with_dot_git(self):
        """Testing Bitbucket check_repository with .git"""
        account = self._get_hosting_account()
        account.data['password'] = encrypt_password('abc123')
        service = account.service

        self.assertRaisesMessage(
            RepositoryError,
            'Please specify just the name of the repository without ".git".',
            lambda: service.check_repository(
                bitbucket_team_name='myteam',
                bitbucket_team_repo_name='myrepo.git',
                plan='team'))

    def test_authorize(self):
        """Testing Bitbucket authorization"""
        def _http_get(self, *args, **kwargs):
            return '{}', {}

        account = self._get_hosting_account()
        service = account.service

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_authorize_with_bad_credentials(self):
        """Testing Bitbucket authorization with bad credentials"""
        def _http_get(service, url, *args, **kwargs):
            raise HTTPError(url, 401, '', {}, StringIO(''))

        account = self._get_hosting_account()
        service = account.service

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertFalse(service.is_authorized())

        self.assertRaisesMessage(
            AuthorizationError,
            'Invalid Bitbucket username or password',
            lambda: service.authorize('myuser', 'abc123', None))

        self.assertNotIn('password', account.data)
        self.assertFalse(service.is_authorized())

    def test_get_file_with_mercurial_and_base_commit_id(self):
        """Testing Bitbucket get_file with Mercurial and base commit ID"""
        self._test_get_file(
            tool_name='Mercurial',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_mercurial_and_revision(self):
        """Testing Bitbucket get_file with Mercurial and revision"""
        self._test_get_file(
            tool_name='Mercurial',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_with_git_and_base_commit_id(self):
        """Testing Bitbucket get_file with Git and base commit ID"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_git_and_revision(self):
        """Testing Bitbucket get_file with Git and revision"""
        self.assertRaises(
            FileNotFoundError,
            self._test_get_file,
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_exists_with_mercurial_and_base_commit_id(self):
        """Testing Bitbucket get_file_exists with Mercurial and base commit ID
        """
        self._test_get_file_exists(
            tool_name='Mercurial',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_mercurial_and_revision(self):
        """Testing Bitbucket get_file_exists with Mercurial and revision"""
        self._test_get_file_exists(
            tool_name='Mercurial',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_git_and_base_commit_id(self):
        """Testing Bitbucket get_file_exists with Git and base commit ID"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_git_and_revision(self):
        """Testing Bitbucket get_file_exists with Git and revision"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=False,
            expected_http_called=False)

    def test_get_file_exists_with_git_and_404(self):
        """Testing BitBucket get_file_exists with Git and a 404 error"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=False)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook(self):
        """Testing BitBucket close_submitted hook"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing BitBucket close_submitted hook with a Local Site"""
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_repo(self):
        """Testing BitBucket close_submitted hook with invalid repository"""
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_site(self):
        """Testing BitBucket close_submitted hook with invalid Local Site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        account = self._get_hosting_account(local_site=local_site)
        account.save()

        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            local_site_name='badsite',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_service_id(self):
        """Testing BitBucket close_submitted hook with invalid hosting
        service ID
        """
        # We'll test against GitHub for this test.
        account = self._get_hosting_account()
        account.service_name = 'github'
        account.save()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def _test_post_commit_hook(self, local_site=None):
        account = self._get_hosting_account(local_site=local_site)
        account.save()

        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        self._post_commit_hook_payload(url, review_request)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (1c44b46)')

    def _post_commit_hook_payload(self, url, review_request):
        return self.client.post(
            url,
            data={
                'payload': json.dumps({
                    # NOTE: This payload only contains the content we make
                    #       use of in the hook.
                    'commits': [
                        {
                            'raw_node': '1c44b461cebe5874a857c51a4a13a84'
                                        '9a4d1e52d',
                            'branch': 'master',
                            'message': 'This is my fancy commit\n'
                                       '\n'
                                       'Reviewed at http://example.com%s'
                                       % review_request.get_absolute_url(),
                        },
                    ]
                }),
            })

    def _test_get_file(self, tool_name, revision, base_commit_id,
                       expected_revision):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/1.0/repositories/'
                'myuser/myrepo/raw/%s/path'
                % expected_revision)
            return b'My data', {}

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file(repository, 'path', revision,
                                  base_commit_id)
        self.assertTrue(service.client.http_get.called)
        self.assertEqual(result, 'My data')

    def _test_get_file_exists(self, tool_name, revision, base_commit_id,
                              expected_revision, expected_found,
                              expected_http_called=True):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/1.0/repositories/'
                'myuser/myrepo/raw/%s/path'
                % expected_revision)

            if expected_found:
                return b'{}', {}
            else:
                error = HTTPError(url, 404, 'Not Found', {}, None)
                error.read = lambda: error.msg
                raise error

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, 'path', revision,
                                         base_commit_id)
        self.assertEqual(service.client.http_get.called, expected_http_called)
        self.assertEqual(result, expected_found)


class BugzillaTests(ServiceTests):
    """Unit tests for the Bugzilla hosting service."""
    service_name = 'bugzilla'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing the Bugzilla service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the Bugzilla bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'bugzilla_url': 'http://bugzilla.example.com',
            }),
            'http://bugzilla.example.com/show_bug.cgi?id=%s')


class CodebaseHQTests(ServiceTests):
    """Unit tests for the Codebase HQ hosting service."""
    service_name = 'codebasehq'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Codebase HQ service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_post_commit)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_git(self):
        """Testing Codebase HQ repository field values for Git"""
        hosting_account = self._get_hosting_account()
        service = hosting_account.service

        self._authorize(service)

        fields = self._get_repository_fields(
            'Git',
            hosting_account=hosting_account,
            fields={
                'codebasehq_project_name': 'myproj',
                'codebasehq_repo_name': 'myrepo',
            })

        self.assertEqual(fields['path'],
                         'git@codebasehq.com:mydomain/myproj/myrepo.git')
        self.assertNotIn('raw_file_url', fields)
        self.assertNotIn('mirror_path', fields)

    def test_repo_field_values_mercurial(self):
        """Testing Codebase HQ repository field values for Mercurial"""
        hosting_account = self._get_hosting_account()
        service = hosting_account.service

        self._authorize(service)

        fields = self._get_repository_fields(
            'Mercurial',
            hosting_account=hosting_account,
            fields={
                'codebasehq_project_name': 'myproj',
                'codebasehq_repo_name': 'myrepo',
            })
        self.assertEqual(fields['path'],
                         'https://mydomain.codebasehq.com/projects/'
                         'myproj/repositories/myrepo/')
        self.assertNotIn('raw_file_url', fields)
        self.assertNotIn('mirror_path', fields)

    def test_repo_field_values_subversion(self):
        """Testing Codebase HQ repository field values for Subversion"""
        hosting_account = self._get_hosting_account()
        service = hosting_account.service

        self._authorize(service)

        fields = self._get_repository_fields(
            'Subversion',
            hosting_account=hosting_account,
            fields={
                'codebasehq_project_name': 'myproj',
                'codebasehq_repo_name': 'myrepo',
            })
        self.assertEqual(fields['path'],
                         'https://mydomain.codebasehq.com/myproj/myrepo.svn')
        self.assertNotIn('raw_file_url', fields)
        self.assertNotIn('mirror_path', fields)

    def test_check_repository_git(self):
        """Testing Codebase HQ check_repository for Git"""
        self._test_check_repository(codebase_scm_type='git',
                                    tool_name='Git')

    def test_check_repository_mercurial(self):
        """Testing Codebase HQ check_repository for Mercurial"""
        self._test_check_repository(codebase_scm_type='hg',
                                    tool_name='Mercurial')

    def test_check_repository_subversion(self):
        """Testing Codebase HQ check_repository for Subversion"""
        self._test_check_repository(codebase_scm_type='svn',
                                    tool_name='Subversion')

    def test_check_repository_with_mismatching_type(self):
        """Testing Codebase HQ check_repository with mismatching repository type
        """
        self._test_check_repository(codebase_scm_type='svn',
                                    tool_name='Mercurial',
                                    expect_success=False,
                                    expected_name_for_error='Subversion')

    def test_authorize(self):
        """Testing Codebase HQ authorization password storage"""
        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        self._authorize(service)

        self.assertIn('api_key', account.data)
        self.assertIn('domain', account.data)
        self.assertIn('password', account.data)
        self.assertEqual(decrypt_password(account.data['api_key']),
                         'abc123')
        self.assertEqual(account.data['domain'], 'mydomain')
        self.assertEqual(decrypt_password(account.data['password']),
                         'mypass')
        self.assertTrue(service.is_authorized())

    def test_get_file_with_mercurial(self):
        """Testing Codebase HQ get_file with Mercurial"""
        self._test_get_file(tool_name='Mercurial')

    def test_get_file_with_mercurial_not_found(self):
        """Testing Codebase HQ get_file with Mercurial with file not found"""
        self._test_get_file(tool_name='Mercurial', file_exists=False)

    def test_get_file_with_git(self):
        """Testing Codebase HQ get_file with Git"""
        self._test_get_file(tool_name='Git', expect_git_blob_url=True)

    def test_get_file_with_git_not_found(self):
        """Testing Codebase HQ get_file with Git with file not found"""
        self._test_get_file(tool_name='Git', expect_git_blob_url=True,
                            file_exists=False)

    def test_get_file_with_subversion(self):
        """Testing Codebase HQ get_file with Subversion"""
        self._test_get_file(tool_name='Subversion')

    def test_get_file_with_subversion_not_found(self):
        """Testing Codebase HQ get_file with Subversion with file not found"""
        self._test_get_file(tool_name='Subversion', file_exists=False)

    def test_get_file_exists_with_mercurial(self):
        """Testing Codebase HQ get_file_exists with Mercurial"""
        self._test_get_file_exists(tool_name='Mercurial')

    def test_get_file_exists_with_mercurial_not_found(self):
        """Testing Codebase HQ get_file_exists with Mercurial with file not
        found
        """
        self._test_get_file_exists(tool_name='Mercurial', file_exists=False)

    def test_get_file_exists_with_git(self):
        """Testing Codebase HQ get_file_exists with Git"""
        self._test_get_file_exists(tool_name='Git', expect_git_blob_url=True)

    def test_get_file_exists_with_git_not_found(self):
        """Testing Codebase HQ get_file_exists with Git with file not found"""
        self._test_get_file_exists(tool_name='Git', expect_git_blob_url=True,
                                   file_exists=False)

    def test_get_file_exists_with_subversion(self):
        """Testing Codebase HQ get_file_exists with Subversion"""
        self._test_get_file_exists(tool_name='Subversion')

    def test_get_file_exists_with_subversion_not_found(self):
        """Testing Codebase HQ get_file_exists with Subversion with file
        not found
        """
        self._test_get_file_exists(tool_name='Subversion', file_exists=False)

    def _test_check_repository(self, codebase_scm_type, tool_name,
                               expect_success=True,
                               expected_name_for_error=None):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api3.codebasehq.com/myproj/myrepo')
            return (
                ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<repository>\n'
                 ' <scm>%s</scm>\n'
                 '</repository>\n'
                 % codebase_scm_type),
                {})

        account = self._get_hosting_account()
        service = account.service

        self._authorize(service)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        if expect_success:
            service.check_repository(codebasehq_project_name='myproj',
                                     codebasehq_repo_name='myrepo',
                                     tool_name=tool_name)
        else:
            message = (
                "The repository type doesn't match what you selected. Did "
                "you mean %s?"
                % expected_name_for_error
            )

            with self.assertRaisesMessage(RepositoryError, message):
                service.check_repository(codebasehq_project_name='myproj',
                                         codebasehq_repo_name='myrepo',
                                         tool_name=tool_name)

        self.assertTrue(service.client.http_get.called)

    def _test_get_file(self, tool_name, expect_git_blob_url=False,
                       file_exists=True):
        def _http_get(service, url, *args, **kwargs):
            if expect_git_blob_url:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123')
            else:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123/'
                    'myfile')

            if file_exists:
                return b'My data\n', {}
            else:
                raise HTTPError(url, 404, '', {}, StringIO())

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'codebasehq_project_name': 'myproj',
            'codebasehq_repo_name': 'myrepo',
        }

        self._authorize(service)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        if file_exists:
            result = service.get_file(repository, 'myfile', '123')
            self.assertEqual(result, 'My data\n')
        else:
            with self.assertRaises(FileNotFoundError):
                service.get_file(repository, 'myfile', '123')

        self.assertTrue(service.client.http_get.called)

    def _test_get_file_exists(self, tool_name, expect_git_blob_url=False,
                              file_exists=True):
        def _http_get(service, url, *args, **kwargs):
            if expect_git_blob_url:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123')
            else:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123/'
                    'myfile')

            if file_exists:
                return b'{}', {}
            else:
                raise HTTPError(url, 404, '', {}, StringIO())

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'codebasehq_project_name': 'myproj',
            'codebasehq_repo_name': 'myrepo',
        }

        self._authorize(service)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, 'myfile', '123')
        self.assertTrue(service.client.http_get.called)
        self.assertEqual(result, file_exists)

    def _authorize(self, service):
        # Don't perform the call to test the API's credentials.
        self.spy_on(service.client.api_get_public_keys, call_original=False)

        service.authorize('myuser', 'mypass', {
            'domain': 'mydomain',
            'api_key': 'abc123',
        })


class FedoraHosted(ServiceTests):
    """Unit tests for the Fedora Hosted hosting service."""
    service_name = 'fedorahosted'

    def test_service_support(self):
        """Testing the Fedora Hosted service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_git(self):
        """Testing the Fedora Hosted repository field values for Git"""
        fields = self._get_repository_fields('Git', fields={
            'fedorahosted_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'git://git.fedorahosted.org/git/myrepo.git')
        self.assertEqual(fields['raw_file_url'],
                         'http://git.fedorahosted.org/cgit/myrepo.git/'
                         'blob/<filename>?id=<revision>')

    def test_repo_field_values_mercurial(self):
        """Testing the Fedora Hosted repository field values for Mercurial"""
        fields = self._get_repository_fields('Mercurial', fields={
            'fedorahosted_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'http://hg.fedorahosted.org/hg/myrepo/')
        self.assertEqual(fields['mirror_path'],
                         'https://hg.fedorahosted.org/hg/myrepo/')

    def test_repo_field_values_svn(self):
        """Testing the Fedora Hosted repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'fedorahosted_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'http://svn.fedorahosted.org/svn/myrepo/')
        self.assertEqual(fields['mirror_path'],
                         'https://svn.fedorahosted.org/svn/myrepo/')

    def test_bug_tracker_field(self):
        """Testing the Fedora Hosted bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'fedorahosted_repo_name': 'myrepo',
            }),
            'https://fedorahosted.org/myrepo/ticket/%s')


class FogBugzTests(ServiceTests):
    """Unit tests for the FogBugz hosting service."""
    service_name = 'fogbugz'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing the FogBugz service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the FogBugz bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'fogbugz_account_domain': 'mydomain',
            }),
            'https://mydomain.fogbugz.com/f/cases/%s')


class GitHubTests(ServiceTests):
    """Unit tests for the GitHub hosting service."""
    service_name = 'github'

    def test_service_support(self):
        """Testing the GitHub service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_public_field_values(self):
        """Testing the GitHub public plan repository field values"""
        fields = self._get_repository_fields('Git', plan='public', fields={
            'github_public_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git://github.com/myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myuser/myrepo.git')

    def test_public_repo_api_url(self):
        """Testing the GitHub public repository API URL"""
        url = self._get_repo_api_url('public', {
            'github_public_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo')

    def test_public_bug_tracker_field(self):
        """Testing the GitHub public repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('public'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public', {
                'github_public_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_public_org_field_values(self):
        """Testing the GitHub public-org plan repository field values"""
        fields = self._get_repository_fields('Git', plan='public-org', fields={
            'github_public_org_repo_name': 'myrepo',
            'github_public_org_name': 'myorg',
        })
        self.assertEqual(fields['path'], 'git://github.com/myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myorg/myrepo.git')

    def test_public_org_repo_api_url(self):
        """Testing the GitHub public-org repository API URL"""
        url = self._get_repo_api_url('public-org', {
            'github_public_org_name': 'myorg',
            'github_public_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo')

    def test_public_org_bug_tracker_field(self):
        """Testing the GitHub public-org repository bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('public-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public-org', {
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_private_field_values(self):
        """Testing the GitHub private plan repository field values"""
        fields = self._get_repository_fields('Git', plan='private', fields={
            'github_private_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git@github.com:myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

    def test_private_repo_api_url(self):
        """Testing the GitHub private repository API URL"""
        url = self._get_repo_api_url('private', {
            'github_private_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo')

    def test_private_bug_tracker_field(self):
        """Testing the GitHub private repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('private'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private', {
                'github_private_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_private_org_field_values(self):
        """Testing the GitHub private-org plan repository field values"""
        fields = self._get_repository_fields(
            'Git', plan='private-org', fields={
                'github_private_org_repo_name': 'myrepo',
                'github_private_org_name': 'myorg',
            })
        self.assertEqual(fields['path'], 'git@github.com:myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

    def test_private_org_repo_api_url(self):
        """Testing the GitHub private-org repository API URL"""
        url = self._get_repo_api_url('private-org', {
            'github_private_org_name': 'myorg',
            'github_private_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo')

    def test_private_org_bug_tracker_field(self):
        """Testing the GitHub private-org repository bug tracker field value"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username(
            'private-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private-org', {
                'github_private_org_name': 'myorg',
                'github_private_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_check_repository_public(self):
        """Testing GitHub check_repository with public repository"""
        self._test_check_repository(plan='public',
                                    github_public_repo_name='myrepo')

    def test_check_repository_private(self):
        """Testing GitHub check_repository with private repository"""
        self._test_check_repository(plan='private',
                                    github_private_repo_name='myrepo')

    def test_check_repository_public_org(self):
        """Testing GitHub check_repository with public org repository"""
        self._test_check_repository(plan='public-org',
                                    github_public_org_name='myorg',
                                    github_public_org_repo_name='myrepo',
                                    expected_user='myorg')

    def test_check_repository_private_org(self):
        """Testing GitHub check_repository with private org repository"""
        self._test_check_repository(plan='private-org',
                                    github_private_org_name='myorg',
                                    github_private_org_repo_name='myrepo',
                                    expected_user='myorg')

    def test_check_repository_public_not_found(self):
        """Testing GitHub check_repository with not found error and public
        repository"""
        self._test_check_repository_error(
            plan='public',
            github_public_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_private_not_found(self):
        """Testing GitHub check_repository with not found error and private
        repository"""
        self._test_check_repository_error(
            plan='private',
            github_private_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_public_org_not_found(self):
        """Testing GitHub check_repository with not found error and
        public organization repository"""
        self._test_check_repository_error(
            plan='public-org',
            github_public_org_name='myorg',
            github_public_org_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this organization or name '
                           'was not found.')

    def test_check_repository_private_org_not_found(self):
        """Testing GitHub check_repository with not found error and
        private organization repository"""
        self._test_check_repository_error(
            plan='private-org',
            github_private_org_name='myorg',
            github_private_org_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this organization or name '
                           'was not found, or your user may not have access '
                           'to it.')

    def test_check_repository_public_plan_private_repo(self):
        """Testing GitHub check_repository with public plan and
        private repository"""
        self._test_check_repository_error(
            plan='public',
            github_public_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": true}',
            expected_error='This is a private repository, but you have '
                           'selected a public plan.')

    def test_check_repository_private_plan_public_repo(self):
        """Testing GitHub check_repository with private plan and
        public repository"""
        self._test_check_repository_error(
            plan='private',
            github_private_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": false}',
            expected_error='This is a public repository, but you have '
                           'selected a private plan.')

    def test_check_repository_public_org_plan_private_repo(self):
        """Testing GitHub check_repository with public organization plan and
        private repository"""
        self._test_check_repository_error(
            plan='public-org',
            github_public_org_name='myorg',
            github_public_org_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": true}',
            expected_error='This is a private repository, but you have '
                           'selected a public plan.')

    def test_check_repository_private_org_plan_public_repo(self):
        """Testing GitHub check_repository with private organization plan and
        public repository"""
        self._test_check_repository_error(
            plan='private-org',
            github_private_org_name='myorg',
            github_private_org_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": false}',
            expected_error='This is a public repository, but you have '
                           'selected a private plan.')

    def test_authorization(self):
        """Testing that GitHub account authorization sends expected data"""
        http_post_data = {}

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return json.dumps({
                'id': 1,
                'url': 'https://api.github.com/authorizations/1',
                'scopes': ['user', 'repo'],
                'token': 'abc123',
                'note': '',
                'note_url': '',
                'updated_at': '2012-05-04T03:30:00Z',
                'created_at': '2012-05-04T03:30:00Z',
            }), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service

        self.spy_on(service.client.http_post, call_fake=_http_post)

        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass', None)
        self.assertTrue(account.is_authorized)

        self.assertEqual(http_post_data['kwargs']['url'],
                         'https://api.github.com/authorizations')
        self.assertEqual(http_post_data['kwargs']['username'], 'myuser')
        self.assertEqual(http_post_data['kwargs']['password'], 'mypass')

    def test_authorization_with_client_info(self):
        """Testing that GitHub account authorization with registered client
        info
        """
        http_post_data = {}
        client_id = '<my client id>'
        client_secret = '<my client secret>'

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return json.dumps({
                'id': 1,
                'url': 'https://api.github.com/authorizations/1',
                'scopes': ['user', 'repo'],
                'token': 'abc123',
                'note': '',
                'note_url': '',
                'updated_at': '2012-05-04T03:30:00Z',
                'created_at': '2012-05-04T03:30:00Z',
            }), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service

        self.spy_on(service.client.http_post, call_fake=_http_post)

        self.assertFalse(account.is_authorized)

        with self.settings(GITHUB_CLIENT_ID=client_id,
                           GITHUB_CLIENT_SECRET=client_secret):
            service.authorize('myuser', 'mypass', None)

        self.assertTrue(account.is_authorized)

        body = json.loads(http_post_data['kwargs']['body'])
        self.assertEqual(body['client_id'], client_id)
        self.assertEqual(body['client_secret'], client_secret)

    def test_get_branches(self):
        """Testing GitHub get_branches implementation"""
        branches_api_response = json.dumps([
            {
                'ref': 'refs/heads/master',
                'object': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                }
            },
            {
                'ref': 'refs/heads/release-1.7.x',
                'object': {
                    'sha': '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                }
            },
            {
                'ref': 'refs/heads/some-component/fix',
                'object': {
                    'sha': '764015ef492c8cb1546363b45fee7ab6d1a182ee',
                }
            },
            {
                'ref': 'refs/tags/release-1.7.11',
                'object': {
                    'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792',
                }
            },
        ])

        def _http_get(self, *args, **kwargs):
            return branches_api_response, None

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        branches = service.get_branches(repository)

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(len(branches), 3)
        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                       default=True),
                Branch(id='release-1.7.x',
                       commit='92463764015ef463b4b6d1a1825fee7aeec8cb15',
                       default=False),
                Branch(id='some-component/fix',
                       commit='764015ef492c8cb1546363b45fee7ab6d1a182ee',
                       default=False),
            ])

    def test_get_commits(self):
        """Testing GitHub get_commits implementation"""
        commits_api_response = json.dumps([
            {
                'commit': {
                    'author': {'name': 'Christian Hammond'},
                    'committer': {'date': '2013-06-25T23:31:22Z'},
                    'message': 'Fixed the bug number for the '
                               'blacktriangledown bug.',
                },
                'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                'parents': [
                    {'sha': '92463764015ef463b4b6d1a1825fee7aeec8cb15'}
                ],
            },
            {
                'commit': {
                    'author': {'name': 'Christian Hammond'},
                    'committer': {'date': '2013-06-25T23:30:59Z'},
                    'message': "Merge branch 'release-1.7.x'",
                },
                'sha': '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                'parents': [
                    {'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792'},
                    {'sha': '6c5f3465da5ed03dca8128bb3dd03121bd2cddb2'},
                ],
            },
            {
                'commit': {
                    'author': {'name': 'David Trowbridge'},
                    'committer': {'date': '2013-06-25T22:41:09Z'},
                    'message': 'Add DIFF_PARSE_ERROR to the '
                               'ValidateDiffResource.create error list.',
                },
                'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792',
                'parents': [],
            }
        ])

        def _http_get(self, *args, **kwargs):
            return commits_api_response, None

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        commits = service.get_commits(
            repository, start='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817')

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0].parent, commits[1].id)
        self.assertEqual(commits[1].parent, commits[2].id)
        self.assertEqual(commits[0].date, '2013-06-25T23:31:22Z')
        self.assertEqual(commits[1].id,
                         '92463764015ef463b4b6d1a1825fee7aeec8cb15')
        self.assertEqual(commits[2].author_name, 'David Trowbridge')
        self.assertEqual(commits[2].parent, '')

    def test_get_change(self):
        """Testing GitHub get_change implementation"""
        commit_sha = '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
        parent_sha = '44568f7d33647d286691517e6325fea5c7a21d5e'
        tree_sha = '56e25e58380daf9b4dfe35677ae6043fe1743922'

        commits_api_response = json.dumps([
            {
                'commit': {
                    'author': {'name': 'David Trowbridge'},
                    'committer': {'date': '2013-06-25T23:31:22Z'},
                    'message': 'Move .clearfix to defs.less',
                },
                'sha': commit_sha,
                'parents': [{'sha': parent_sha}],
            },
        ])

        compare_api_response = json.dumps({
            'base_commit': {
                'commit': {
                    'tree': {'sha': tree_sha},
                },
            },
            'files': [
                {
                    'sha': '4344b3ad41b171ea606e88e9665c34cca602affb',
                    'filename': 'reviewboard/static/rb/css/defs.less',
                    'status': 'modified',
                    'patch': dedent("""\
                        @@ -182,4 +182,23 @@
                         }


                        +/* !(*%!(&^ (see http://www.positioniseverything.net/easyclearing.html) */
                        +.clearfix {
                        +  display: inline-block;
                        +
                        +  &:after {
                        +    clear: both;
                        +    content: \".\";
                        +    display: block;
                        +    height: 0;
                        +    visibility: hidden;
                        +  }
                        +}
                        +
                        +/* Hides from IE-mac \\*/
                        +* html .clearfix {height: 1%;}
                        +.clearfix {display: block;}
                        +/* End hide from IE-mac */
                        +
                        +
                         // vim: set et ts=2 sw=2:"""),
                },
                {
                    'sha': '8e3129277b018b169cb8d13771433fbcd165a17c',
                    'filename': 'reviewboard/static/rb/css/reviews.less',
                    'status': 'modified',
                    'patch': dedent("""\
                        @@ -1311,24 +1311,6 @@
                           .border-radius(8px);
                         }

                        -/* !(*%!(&^ (see http://www.positioniseverything.net/easyclearing.html) */
                        -.clearfix {
                        -  display: inline-block;
                        -
                        -  &:after {
                        -    clear: both;
                        -    content: \".\";
                        -    display: block;
                        -    height: 0;
                        -    visibility: hidden;
                        -  }
                        -}
                        -
                        -/* Hides from IE-mac \\*/
                        -* html .clearfix {height: 1%;}
                        -.clearfix {display: block;}
                        -/* End hide from IE-mac */
                        -

                         /****************************************************************************
                          * Issue Summary"""),
                },
                {
                    'sha': '17ba0791499db908433b80f37c5fbc89b870084b',
                    'filename': 'new_filename',
                    'previous_filename': 'old_filename',
                    'status': 'renamed',
                    'patch': dedent('''\
                        @@ -1,1 +1,1 @@
                        - foo
                        + bar
                    ''')
                },
            ],
        })

        trees_api_response = json.dumps({
            'tree': [
                {
                    'path': 'reviewboard/static/rb/css/defs.less',
                    'sha': '830a40c3197223c6a0abb3355ea48891a1857bfd',
                },
                {
                    'path': 'reviewboard/static/rb/css/reviews.less',
                    'sha': '535cd2c4211038d1bb8ab6beaed504e0db9d7e62',
                },
                {
                    'path': 'old_filename',
                    'sha': '356a192b7913b04c54574d18c28d46e6395428ab',
                }
            ],
        })

        # This has to be a list to avoid python's hinky treatment of scope of
        # variables assigned within a closure.
        step = [1]

        def _http_get(service, url, *args, **kwargs):
            parsed = urlparse(url)
            if parsed.path == '/repos/myuser/myrepo/commits':
                self.assertEqual(step[0], 1)
                step[0] += 1

                query = parsed.query.split('&')
                self.assertIn(('sha=%s' % commit_sha), query)

                return commits_api_response, None
            elif parsed.path.startswith('/repos/myuser/myrepo/compare/'):
                self.assertEqual(step[0], 2)
                step[0] += 1

                revs = parsed.path.split('/')[-1].split('...')
                self.assertEqual(revs[0], parent_sha)
                self.assertEqual(revs[1], commit_sha)

                return compare_api_response, None
            elif parsed.path.startswith('/repos/myuser/myrepo/git/trees/'):
                self.assertEqual(step[0], 3)
                step[0] += 1

                self.assertEqual(parsed.path.split('/')[-1], tree_sha)

                return trees_api_response, None
            else:
                print(parsed)
                self.fail('Got an unexpected GET request')

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        change = service.get_change(repository, commit_sha)

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(change.message, 'Move .clearfix to defs.less')
        self.assertEqual(md5(change.diff.encode('utf-8')).hexdigest(),
                         '2e928c77c0bf703960eb49f04e76bc11')

    def test_get_change_exception(self):
        """Testing GitHub get_change exception types"""
        def _http_get(service, url, *args, **kwargs):
            raise Exception('Not Found')

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        commit_sha = '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
        self.assertRaisesMessage(
            SCMError, 'Not Found',
            lambda: service.get_change(repository, commit_sha))

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook(self):
        """Testing GitHub close_submitted hook"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing GitHub close_submitted hook with a Local Site"""
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_unpublished_review_request(self):
        """Testing GitHub close_submitted hook with an un-published review
        request
        """
        self._test_post_commit_hook(publish=False)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_ping(self):
        """Testing GitHub close_submitted hook ping"""
        account = self._get_hosting_account()
        account.save()

        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid(),
            event='ping')
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_repo(self):
        """Testing GitHub close_submitted hook with invalid repository"""
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_site(self):
        """Testing GitHub close_submitted hook with invalid Local Site"""
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            local_site_name='badsite',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_service_id(self):
        """Testing GitHub close_submitted hook with invalid hosting service ID
        """
        # We'll test against Bitbucket for this test.
        account = self._get_hosting_account()
        account.service_name = 'bitbucket'
        account.save()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_event(self):
        """Testing GitHub close_submitted hook with non-push event"""
        account = self._get_hosting_account()
        account.save()

        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid(),
            event='foo')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_signature(self):
        """Testing GitHub close_submitted hook with invalid signature"""
        account = self._get_hosting_account()
        account.save()

        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, 'bad-secret')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def _test_post_commit_hook(self, local_site=None, publish=True):
        account = self._get_hosting_account(local_site=local_site)
        account.save()

        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=publish)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (1c44b46)')

    def _post_commit_hook_payload(self, url, review_request, secret,
                                  event='push'):
        payload = json.dumps({
            # NOTE: This payload only contains the content we make
            #       use of in the hook.
            'ref': 'refs/heads/master',
            'commits': [
                {
                    'id': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                    'message': 'This is my fancy commit\n'
                               '\n'
                               'Reviewed at http://example.com%s'
                               % review_request.get_absolute_url(),
                },
            ]
        })

        m = hmac.new(bytes(secret), payload, hashlib.sha1)

        return self.client.post(
            url,
            payload,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT=event,
            HTTP_X_HUB_SIGNATURE='sha1=%s' % m.hexdigest())

    def _test_check_repository(self, expected_user='myuser', **kwargs):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api.github.com/repos/%s/myrepo?access_token=123'
                % expected_user)
            return b'{}', {}

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['authorization'] = {
            'token': '123',
        }

        service.check_repository(**kwargs)
        self.assertTrue(service.client.http_get.called)

    def _test_check_repository_error(self, http_status, payload,
                                     expected_error, **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if http_status == 200:
                return payload, {}
            else:
                raise HTTPError(url, http_status, '', {}, StringIO(payload))

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['authorization'] = {
            'token': '123',
        }

        try:
            service.check_repository(**kwargs)
            saw_exception = False
        except Exception as e:
            self.assertEqual(six.text_type(e), expected_error)
            saw_exception = True

        self.assertTrue(saw_exception)

    def _get_repo_api_url(self, plan, fields):
        account = self._get_hosting_account()
        service = account.service
        self.assertNotEqual(service, None)

        repository = Repository(hosting_account=account)
        repository.extra_data['repository_plan'] = plan

        form = self._get_form(plan, fields)
        form.save(repository)

        return service._get_repo_api_url(repository)


class GitLabTests(ServiceTests):
    """Unit tests for the GitLab hosting service."""
    service_name = 'gitlab'

    def test_service_support(self):
        """Testing the GitLab service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_personal_field_values(self):
        """Testing the GitLab personal plan repository field values"""
        fields = self._get_repository_fields('Git', plan='personal', fields={
            'hosting_url': 'https://example.com',
            'gitlab_personal_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'git@example.com:myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'https://example.com/myuser/myrepo.git')

    def test_personal_bug_tracker_field(self):
        """Testing the GitLab personal repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('personal'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('personal', {
                'hosting_url': 'https://example.com',
                'gitlab_personal_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'https://example.com/myuser/myrepo/issues/%s')

    def test_group_field_values(self):
        """Testing the GitLab group plan repository field values"""
        fields = self._get_repository_fields('Git', plan='group', fields={
            'hosting_url': 'https://example.com',
            'gitlab_group_repo_name': 'myrepo',
            'gitlab_group_name': 'mygroup',
        })
        self.assertEqual(fields['path'],
                         'git@example.com:mygroup/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'https://example.com/mygroup/myrepo.git')

    def test_group_bug_tracker_field(self):
        """Testing the GitLab group repository bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('group'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('group', {
                'hosting_url': 'https://example.com',
                'gitlab_group_name': 'mygroup',
                'gitlab_group_repo_name': 'myrepo',
            }),
            'https://example.com/mygroup/myrepo/issues/%s')

    def test_check_repository_personal(self):
        """Testing GitLab check_repository with personal repository"""
        self._test_check_repository(plan='personal',
                                    gitlab_personal_repo_name='myrepo')

    def test_check_repository_group(self):
        """Testing GitLab check_repository with group repository"""
        self._test_check_repository(plan='group',
                                    gitlab_group_name='mygroup',
                                    gitlab_group_repo_name='myrepo',
                                    expected_user='mygroup')

    def test_check_repository_personal_not_found(self):
        """Testing GitLab check_repository with not found error and personal
        repository"""
        self._test_check_repository_error(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_group_not_found(self):
        """Testing GitLab check_repository with not found error and
        group repository"""
        self._test_check_repository_error(
            plan='group',
            gitlab_group_name='mygroup',
            gitlab_group_repo_name='myrepo',
            expected_error='A repository with this name was not found on '
                           'this group, or your user may not have access '
                           'to it.')

    def test_authorization(self):
        """Testing that GitLab account authorization sends expected data"""
        http_post_data = {}

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return json.dumps({
                'id': 1,
                'private_token': 'abc123',
            }), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service

        self.spy_on(service.client.http_post, call_fake=_http_post)

        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass',
                          hosting_url='https://example.com')
        self.assertTrue(account.is_authorized)

        self.assertEqual(http_post_data['kwargs']['url'],
                         'https://example.com/api/v3/session')
        self.assertIn('fields', http_post_data['kwargs'])

        fields = http_post_data['kwargs']['fields']
        self.assertEqual(fields['login'], 'myuser')
        self.assertEqual(fields['password'], 'mypass')

    def test_get_branches(self):
        """Testing GitLab get_branches implementation"""
        branches_api_response = json.dumps([
            {
                'name': 'master',
                'commit': {
                    'id': 'ed899a2f4b50b4370feeea94676502b42383c746'
                }
            },
            {
                'name': 'branch1',
                'commit': {
                    'id': '6104942438c14ec7bd21c6cd5bd995272b3faff6'
                }
            },
            {
                'name': 'branch2',
                'commit': {
                    'id': '21b3bcabcff2ab3dc3c9caa172f783aad602c0b0'
                }
            },
            {
                'branch-name': 'branch3',
                'commit': {
                    'id': 'd5a3ff139356ce33e37e73add446f16869741b50'
                }
            }
        ])

        def _http_get(self, *args, **kwargs):
            return branches_api_response, None

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        self.spy_on(service.client.http_get, call_fake=_http_get)

        branches = service.get_branches(repository)

        self.assertTrue(service.client.http_get.called)
        self.assertEqual(len(branches), 3)
        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='ed899a2f4b50b4370feeea94676502b42383c746',
                       default=True),
                Branch(id='branch1',
                       commit='6104942438c14ec7bd21c6cd5bd995272b3faff6',
                       default=False),
                Branch(id='branch2',
                       commit='21b3bcabcff2ab3dc3c9caa172f783aad602c0b0',
                       default=False)
            ])

    def test_get_commits(self):
        """Testing GitLab get_commits implementation"""
        commits_api_response = json.dumps([
            {
                'id': 'ed899a2f4b50b4370feeea94676502b42383c746',
                'author_name': 'Chester Li',
                'created_at': '2015-03-10T11:50:22+03:00',
                'message': 'Replace sanitize with escape once'
            },
            {
                'id': '6104942438c14ec7bd21c6cd5bd995272b3faff6',
                'author_name': 'Chester Li',
                'created_at': '2015-03-10T09:06:12+03:00',
                'message': 'Sanitize for network graph'
            },
            {
                'id': '21b3bcabcff2ab3dc3c9caa172f783aad602c0b0',
                'author_name': 'East Coast',
                'created_at': '2015-03-04T15:31:18.000-04:00',
                'message': 'Add a timer to test file'
            }
        ])

        def _http_get(self, *args, **kargs):
            return commits_api_response, None

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        self.spy_on(service.client.http_get, call_fake=_http_get)

        commits = service.get_commits(
            repository, start='ed899a2f4b50b4370feeea94676502b42383c746')

        self.assertTrue(service.client.http_get.called)
        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0].id,
                         'ed899a2f4b50b4370feeea94676502b42383c746')
        self.assertNotEqual(commits[0].author_name, 'East Coast')
        self.assertEqual(commits[1].date, '2015-03-10T09:06:12+03:00')
        self.assertNotEqual(commits[1].message,
                            'Replace sanitize with escape once')
        self.assertEqual(commits[2].author_name, 'East Coast')

    def test_get_change(self):
        """Testing GitLab get_change implementation"""
        commit_id = 'ed899a2f4b50b4370feeea94676502b42383c746'

        commit_api_response = json.dumps(
            {
                'author_name': 'Chester Li',
                'id': commit_id,
                'created_at': '2015-03-10T11:50:22+03:00',
                'message': 'Replace sanitize with escape once',
                'parent_ids': ['ae1d9fb46aa2b07ee9836d49862ec4e2c46fbbba']
            }
        )

        path_api_response = json.dumps(
            {
                'path_with_namespace': 'username/project_name'
            }
        )

        diff = dedent(b'''\
            ---
            f1 | 1 +
            f2 | 1 +
            2 files changed, 2 insertions(+), 0 deletions(-)

            diff --git a/f1 b/f1
            index 11ac561..3ea0691 100644
            --- a/f1
            +++ b/f1
            @@ -1 +1,2 @@
            this is f1
            +add one line to f1
            diff --git a/f2 b/f2
            index c837441..9302ecd 100644
            --- a/f2
            +++ b/f2
            @@ -1 +1,2 @@
            this is f2
            +add one line to f2 with Unicode\xe2\x9d\xb6
            ''')

        def _http_get(service, url, *args, **kwargs):
            self.assertTrue(url.startswith(account.hosting_url))

            parsed = urlparse(url)

            if parsed.path.startswith(
                    '/api/v3/projects/123456/repository/commits'):
                # If the url is commit_api_url.
                return commit_api_response, None
            elif parsed.path == '/api/v3/projects/123456':
                # If the url is path_api_url.
                return path_api_response, None
            elif parsed.path.endswith('.diff'):
                # If the url is diff_url.
                return diff, None
            else:
                print(parsed)
                self.fail('Got an unexpected GET request')

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        self.spy_on(service.client.http_get, call_fake=_http_get)

        commit = service.get_change(repository, commit_id)

        self.assertTrue(service.client.http_get.called)
        self.assertEqual(commit.date, '2015-03-10T11:50:22+03:00')
        self.assertEqual(commit.diff, diff)
        self.assertNotEqual(commit.parent, '')

    def _test_check_repository(self, expected_user='myuser', **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if url == 'https://example.com/api/v3/projects?per_page=100':
                payload = [
                    {
                        'id': 1,
                        'path': 'myrepo',
                        'namespace': {
                            'path': expected_user,
                        },
                    }
                ]
            elif url == 'https://example.com/api/v3/projects/1':
                # We don't care about the contents. Just that it exists.
                payload = {}
            else:
                self.fail('Unexpected URL %s' % url)

            return json.dumps(payload), {}

        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        service.check_repository(**kwargs)
        self.assertTrue(service.client.http_get.called)

    def _test_check_repository_error(self, expected_error, **kwargs):
        def _http_get(service, url, *args, **kwargs):
            return '[]', {}

        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        try:
            service.check_repository(**kwargs)
            saw_exception = False
        except Exception as e:
            self.assertEqual(six.text_type(e), expected_error)
            saw_exception = True

        self.assertTrue(saw_exception)

    def _get_repo_api_url(self, plan, fields):
        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.assertNotEqual(service, None)

        repository = Repository(hosting_account=account)
        repository.extra_data['repository_plan'] = plan

        form = self._get_form(plan, fields)
        form.save(repository)

        return service._get_repo_api_url(repository)


class GitoriousTests(ServiceTests):
    """Unit tests for the Gitorious hosting service."""
    service_name = 'gitorious'

    def test_service_support(self):
        """Testing the Gitorious service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values(self):
        """Testing the Gitorious repository field values"""
        fields = self._get_repository_fields('Git', fields={
            'gitorious_project_name': 'myproj',
            'gitorious_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'git://gitorious.org/myproj/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'https://gitorious.org/myproj/myrepo.git')
        self.assertEqual(fields['raw_file_url'],
                         'https://gitorious.org/myproj/myrepo/blobs/raw/'
                         '<revision>')


class GoogleCodeTests(ServiceTests):
    """Unit tests for the Google Code hosting service."""
    service_name = 'googlecode'

    def test_service_support(self):
        """Testing the Google Code service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_mercurial(self):
        """Testing the Google Code repository field values for Mercurial"""
        fields = self._get_repository_fields('Mercurial', fields={
            'googlecode_project_name': 'myproj',
        })
        self.assertEqual(fields['path'], 'http://myproj.googlecode.com/hg')
        self.assertEqual(fields['mirror_path'],
                         'https://myproj.googlecode.com/hg')

    def test_repo_field_values_svn(self):
        """Testing the Google Code repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'googlecode_project_name': 'myproj',
        })
        self.assertEqual(fields['path'], 'http://myproj.googlecode.com/svn')
        self.assertEqual(fields['mirror_path'],
                         'https://myproj.googlecode.com/svn')

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook(self):
        """Testing Google Code close_submitted hook"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing Google Code close_submitted hook with a Local Site"""
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_repo(self):
        """Testing Google Code close_submitted hook with invalid repository"""
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'googlecode-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'googlecode',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_site(self):
        """Testing Google Code close_submitted hook with invalid Local Site"""
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'googlecode-hooks-close-submitted',
            local_site_name='badsite',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'googlecode',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_service_id(self):
        """Testing Google Code close_submitted hook with invalid hosting service ID
        """
        # We'll test against Bitbucket for this test.
        account = self._get_hosting_account()
        account.service_name = 'bitbucket'
        account.save()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'googlecode-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'googlecode',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_hooks_uuid(self):
        """Testing Google Code close_submitted hook with invalid hooks UUID"""
        account = self._get_hosting_account()
        account.save()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'googlecode-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'googlecode',
                'hooks_uuid': 'abc123',
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def _test_post_commit_hook(self, local_site=None):
        account = self._get_hosting_account(local_site=local_site)
        account.save()

        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'googlecode-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'googlecode',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (1c44b46)')

    def _post_commit_hook_payload(self, url, review_request):
        return self.client.post(
            url,
            json.dumps({
                # NOTE: This payload only contains the content we make
                #       use of in the hook.
                'repository_path': 'master',
                'revisions': [
                    {
                        'revision': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                        'message': 'This is my fancy commit\n'
                                   '\n'
                                   'Reviewed at http://example.com%s'
                                   % review_request.get_absolute_url(),
                    },
                ]
            }),
            content_type='application/json')


class KilnTests(ServiceTests):
    """Unit tests for the Kiln hosting service."""
    service_name = 'kiln'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Kiln service support capabilities"""
        self.assertTrue(self.service_class.supports_repositories)
        self.assertTrue(self.service_class.needs_authorization)
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_post_commit)
        self.assertFalse(self.service_class.supports_two_factor_auth)

    def test_repo_field_values_git(self):
        """Testing Kiln repository field values for Git"""
        fields = self._get_repository_fields('Git', fields={
            'kiln_account_domain': 'mydomain',
            'kiln_project_name': 'myproject',
            'kiln_group_name': 'mygroup',
            'kiln_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'https://mydomain.kilnhg.com/Code/myproject/mygroup/myrepo.git')
        self.assertEqual(
            fields['mirror_path'],
            'ssh://mydomain@mydomain.kilnhg.com/myproject/mygroup/myrepo')

    def test_repo_field_values_mercurial(self):
        """Testing Kiln repository field values for Mercurial"""
        fields = self._get_repository_fields('Mercurial', fields={
            'kiln_account_domain': 'mydomain',
            'kiln_project_name': 'myproject',
            'kiln_group_name': 'mygroup',
            'kiln_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'https://mydomain.kilnhg.com/Code/myproject/mygroup/myrepo')
        self.assertEqual(
            fields['mirror_path'],
            'ssh://mydomain@mydomain.kilnhg.com/myproject/mygroup/myrepo')

    def test_authorize(self):
        """Testing Kiln authorization token storage"""
        def _http_post(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.kilnhg.com/Api/1.0/Auth/Login')
            return '"my-token"', {}

        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        self.spy_on(service.client.http_post, call_fake=_http_post)

        service.authorize('myuser', 'abc123',
                          kiln_account_domain='mydomain')

        self.assertIn('auth_token', account.data)
        self.assertEqual(account.data['auth_token'], 'my-token')
        self.assertTrue(service.is_authorized())

    def test_check_repository(self):
        """Testing Kiln check_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.kilnhg.com/Api/1.0/Project?token=my-token')

            data = json.dumps([{
                'sSlug': 'myproject',
                'repoGroups': [{
                    'sSlug': 'mygroup',
                    'repos': [{
                        'sSlug': 'myrepo',
                    }]
                }]
            }])

            return data, {}

        account = self._get_hosting_account()
        service = account.service
        account.data.update({
            'auth_token': 'my-token',
            'kiln_account_domain': 'mydomain',
        })

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(kiln_account_domain='mydomain',
                                 kiln_project_name='myproject',
                                 kiln_group_name='mygroup',
                                 kiln_repo_name='myrepo',
                                 tool_name='Mercurial')
        self.assertTrue(service.client.http_get.called)

    def test_check_repository_with_incorrect_repo_info(self):
        """Testing Kiln check_repository with incorrect repo info"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.kilnhg.com/Api/1.0/Project?token=my-token')

            data = json.dumps([{
                'sSlug': 'otherproject',
                'repoGroups': [{
                    'sSlug': 'othergroup',
                    'repos': [{
                        'sSlug': 'otherrepo',
                    }]
                }]
            }])

            return data, {}

        account = self._get_hosting_account()
        service = account.service
        account.data.update({
            'auth_token': 'my-token',
            'kiln_account_domain': 'mydomain',
        })

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertRaises(
            RepositoryError,
            lambda: service.check_repository(
                kiln_account_domain='mydomain',
                kiln_project_name='myproject',
                kiln_group_name='mygroup',
                kiln_repo_name='myrepo',
                tool_name='Mercurial'))
        self.assertTrue(service.client.http_get.called)

    def test_get_file(self):
        """Testing Kiln get_file"""
        def _http_get(service, url, *args, **kwargs):
            if url == ('https://mydomain.kilnhg.com/Api/1.0/Project'
                       '?token=my-token'):
                data = json.dumps([{
                    'sSlug': 'myproject',
                    'repoGroups': [{
                        'sSlug': 'mygroup',
                        'repos': [{
                            'sSlug': 'myrepo',
                            'ixRepo': 123,
                        }]
                    }]
                }])
            else:
                self.assertEqual(
                    url,
                    'https://mydomain.kilnhg.com/Api/1.0/Repo/123/Raw/File/'
                    '%s?rev=%s&token=my-token'
                    % (encoded_path, revision))

                data = 'My data'

            return data, {}

        path = '/path'
        encoded_path = '2F70617468'
        revision = 123

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name='Mercurial'))
        repository.extra_data = {
            'kiln_account_domain': 'mydomain',
            'kiln_project_name': 'myproject',
            'kiln_group_name': 'mygroup',
            'kiln_repo_name': 'myrepo',
        }
        repository.save()

        account.data.update({
            'auth_token': 'my-token',
            'kiln_account_domain': 'mydomain',
        })

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file(repository, path, revision)
        self.assertTrue(service.client.http_get.called)
        self.assertEqual(result, 'My data')

    def test_get_file_exists(self):
        """Testing Kiln get_file_exists"""
        def _http_get(service, url, *args, **kwargs):
            if url == ('https://mydomain.kilnhg.com/Api/1.0/Project'
                       '?token=my-token'):
                data = json.dumps([{
                    'sSlug': 'myproject',
                    'repoGroups': [{
                        'sSlug': 'mygroup',
                        'repos': [{
                            'sSlug': 'myrepo',
                            'ixRepo': 123,
                        }]
                    }]
                }])
            else:
                self.assertEqual(
                    url,
                    'https://mydomain.kilnhg.com/Api/1.0/Repo/123/Raw/File/'
                    '%s?rev=%s&token=my-token'
                    % (encoded_path, revision))

                data = 'My data'

            return data, {}

        path = '/path'
        encoded_path = '2F70617468'
        revision = 123

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name='Mercurial'))
        repository.extra_data = {
            'kiln_account_domain': 'mydomain',
            'kiln_project_name': 'myproject',
            'kiln_group_name': 'mygroup',
            'kiln_repo_name': 'myrepo',
        }
        repository.save()

        account.data.update({
            'auth_token': 'my-token',
            'kiln_account_domain': 'mydomain',
        })

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, path, revision)
        self.assertTrue(service.client.http_get.called)
        self.assertTrue(result)


class RedmineTests(ServiceTests):
    """Unit tests for the Redmine hosting service."""
    service_name = 'redmine'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing the Redmine service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the Redmine bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'redmine_url': 'http://redmine.example.com',
            }),
            'http://redmine.example.com/issues/%s')


class SourceForgeTests(ServiceTests):
    """Unit tests for the SourceForge hosting service."""
    service_name = 'sourceforge'

    def test_service_support(self):
        """Testing the SourceForge service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_bazaar(self):
        """Testing the SourceForge repository field values for Bazaar"""
        fields = self._get_repository_fields('Bazaar', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         'bzr://myproj.bzr.sourceforge.net/bzrroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'bzr+ssh://myproj.bzr.sourceforge.net/bzrroot/'
                         'myproj')

    def test_repo_field_values_cvs(self):
        """Testing the SourceForge repository field values for CVS"""
        fields = self._get_repository_fields('CVS', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         ':pserver:anonymous@myproj.cvs.sourceforge.net:'
                         '/cvsroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'myproj.cvs.sourceforge.net/cvsroot/myproj')

    def test_repo_field_values_mercurial(self):
        """Testing the SourceForge repository field values for Mercurial"""
        fields = self._get_repository_fields('Mercurial', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         'http://myproj.hg.sourceforge.net:8000/hgroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'ssh://myproj.hg.sourceforge.net/hgroot/myproj')

    def test_repo_field_values_svn(self):
        """Testing the SourceForge repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         'http://myproj.svn.sourceforge.net/svnroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'https://myproj.svn.sourceforge.net/svnroot/myproj')


class TracTests(ServiceTests):
    """Unit tests for the Trac hosting service."""
    service_name = 'trac'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing the Trac service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the Trac bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'trac_url': 'http://trac.example.com',
            }),
            'http://trac.example.com/ticket/%s')


class UnfuddleTests(ServiceTests):
    """Unit tests for the Unfuddle hosting service."""
    service_name = 'unfuddle'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Unfuddle service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_git(self):
        """Testing Unfuddle repository field values for Git"""
        fields = self._get_repository_fields('Git', fields={
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'git@mydomain.unfuddle.com:mydomain/myrepo.git')
        self.assertEqual(
            fields['mirror_path'],
            'https://mydomain.unfuddle.com/git/mydomain_myrepo/')

    def test_repo_field_values_subversion(self):
        """Testing Unfuddle repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'https://mydomain.unfuddle.com/svn/mydomain_myrepo')
        self.assertEqual(
            fields['mirror_path'],
            'http://mydomain.unfuddle.com/svn/mydomain_myrepo')

    def test_authorize(self):
        """Testing Unfuddle authorization password storage"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/account/')
            return '{}', {}

        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.authorize('myuser', 'abc123',
                          unfuddle_account_domain='mydomain')

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_check_repository(self):
        """Testing Unfuddle check_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/')

            return '[{"id": 2, "abbreviation": "myrepo", "system": "git"}]', {}

        account = self._get_hosting_account()
        service = account.service
        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(unfuddle_account_domain='mydomain',
                                 unfuddle_repo_name='myrepo',
                                 tool_name='Git')
        self.assertTrue(service.client.http_get.called)

    def test_check_repository_with_wrong_repo_type(self):
        """Testing Unfuddle check_repository with wrong repo type"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/')

            return '[{"id": 1, "abbreviation": "myrepo", "system": "svn"}]', {}

        account = self._get_hosting_account()
        service = account.service
        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertRaises(
            RepositoryError,
            lambda: service.check_repository(
                unfuddle_account_domain='mydomain',
                unfuddle_repo_name='myrepo',
                tool_name='Git'))
        self.assertTrue(service.client.http_get.called)

    def test_get_file_with_svn_and_base_commit_id(self):
        """Testing Unfuddle get_file with Subversion and base commit ID"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_svn_and_revision(self):
        """Testing Unfuddle get_file with Subversion and revision"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_with_git_and_base_commit_id(self):
        """Testing Unfuddle get_file with Git and base commit ID"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_git_and_revision(self):
        """Testing Unfuddle get_file with Git and revision"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision=None,
            expected_error=True)

    def test_get_file_exists_with_svn_and_base_commit_id(self):
        """Testing Unfuddle get_file_exists with Subversion and base commit ID
        """
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_svn_and_revision(self):
        """Testing Unfuddle get_file_exists with Subversion and revision"""
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_git_and_base_commit_id(self):
        """Testing Unfuddle get_file_exists with Git and base commit ID"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_git_and_revision(self):
        """Testing Unfuddle get_file_exists with Git and revision"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision=None,
            expected_found=False,
            expected_error=True)

    def _test_get_file(self, tool_name, revision, base_commit_id,
                       expected_revision, expected_error=False):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/2/'
                'download/?path=%s&commit=%s'
                % (path, expected_revision))
            return 'My data', {}

        path = '/path'
        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_id': 2,
            'unfuddle_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        if expected_error:
            self.assertRaises(
                FileNotFoundError,
                lambda: service.get_file(repository, path, revision,
                                         base_commit_id))
            self.assertFalse(service.client.http_get.called)
        else:
            result = service.get_file(repository, path, revision,
                                      base_commit_id)
            self.assertTrue(service.client.http_get.called)
            self.assertEqual(result, 'My data')

    def _test_get_file_exists(self, tool_name, revision, base_commit_id,
                              expected_revision, expected_found=True,
                              expected_error=False):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/2/'
                'history/?path=/path&commit=%s&count=0'
                % expected_revision)

            if expected_found:
                return '{}', {}
            else:
                raise HTTPError()

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_id': 2,
            'unfuddle_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, '/path', revision,
                                         base_commit_id)

        if expected_error:
            self.assertFalse(service.client.http_get.called)
            self.assertFalse(result)
        else:
            self.assertTrue(service.client.http_get.called)
            self.assertEqual(result, expected_found)


class VersionOneTests(ServiceTests):
    """Unit tests for the VersionOne hosting service."""
    service_name = 'versionone'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing the VersionOne service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the VersionOne bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'versionone_url': 'http://versionone.example.com',
            }),
            'http://versionone.example.com/assetdetail.v1?Number=%s')


def hosting_service_url_test_view(request, repo_id):
    """View to test URL pattern addition when registering a hosting service"""
    return HttpResponse(str(repo_id))


class HostingServiceRegistrationTests(TestCase):
    """Unit tests for Hosting Service registration."""
    class DummyService(HostingService):
        name = 'DummyService'

    class DummyServiceWithURLs(HostingService):
        name = 'DummyServiceWithURLs'

        repository_url_patterns = patterns(
            '',

            url(r'^hooks/pre-commit/$', hosting_service_url_test_view,
                name='dummy-service-post-commit-hook'),
        )

    def tearDown(self):
        super(HostingServiceRegistrationTests, self).tearDown()

        # Unregister the service, going back to a default state. It's okay
        # if it fails.
        #
        # This will match whichever service we added for testing.
        try:
            unregister_hosting_service('dummy-service')
        except KeyError:
            pass

    def test_register_without_urls(self):
        """Testing HostingService registration"""
        register_hosting_service('dummy-service', self.DummyService)

        with self.assertRaises(KeyError):
            register_hosting_service('dummy-service', self.DummyService)

    def test_unregister(self):
        """Testing HostingService unregistration"""
        register_hosting_service('dummy-service', self.DummyService)
        unregister_hosting_service('dummy-service')

    def test_registration_with_urls(self):
        """Testing HostingService registration with URLs"""
        register_hosting_service('dummy-service', self.DummyServiceWithURLs)

        self.assertEqual(
            local_site_reverse(
                'dummy-service-post-commit-hook',
                kwargs={
                    'repository_id': 1,
                    'hosting_service_id': 'dummy-service',
                }),
            '/repos/1/dummy-service/hooks/pre-commit/')

        self.assertEqual(
            local_site_reverse(
                'dummy-service-post-commit-hook',
                local_site_name='test-site',
                kwargs={
                    'repository_id': 1,
                    'hosting_service_id': 'dummy-service',
                }),
            '/s/test-site/repos/1/dummy-service/hooks/pre-commit/')

        # Once registered, should not be able to register again
        with self.assertRaises(KeyError):
            register_hosting_service('dummy-service',
                                     self.DummyServiceWithURLs)

    def test_unregistration_with_urls(self):
        """Testing HostingService unregistration with URLs"""
        register_hosting_service('dummy-service', self.DummyServiceWithURLs)
        unregister_hosting_service('dummy-service')

        with self.assertRaises(NoReverseMatch):
            local_site_reverse(
                'dummy-service-post-commit-hook',
                kwargs={
                    'repository_id': 1,
                    'hosting_service_id': 'dummy-service',
                }),

        # Once unregistered, should not be able to unregister again
        with self.assertRaises(KeyError):
            unregister_hosting_service('dummy-service')


class HostingServiceAuthFormTests(TestCase):
    """Unit tests for reviewboard.hostingsvcs.forms.HostingServiceAuthForm."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(HostingServiceAuthFormTests, self).setUp()

        register_hosting_service('test', TestService)
        register_hosting_service('self_hosted_test', SelfHostedTestService)

        self.git_tool_id = Tool.objects.get(name='Git').pk

    def tearDown(self):
        super(HostingServiceAuthFormTests, self).tearDown()

        unregister_hosting_service('self_hosted_test')
        unregister_hosting_service('test')

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
