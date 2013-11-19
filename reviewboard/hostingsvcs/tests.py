from __future__ import print_function, unicode_literals

import json
from hashlib import md5
from textwrap import dedent

from django.contrib.sites.models import Site
from djblets.util.compat import six
from djblets.util.compat.six.moves import cStringIO as StringIO
from djblets.util.compat.six.moves.urllib.error import HTTPError
from djblets.util.compat.six.moves.urllib.parse import urlparse
from kgb import SpyAgency

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.scmtools.core import Branch
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.testing import TestCase


class ServiceTests(SpyAgency, TestCase):
    service_name = None

    def __init__(self, *args, **kwargs):
        super(ServiceTests, self).__init__(*args, **kwargs)

        self.assertNotEqual(self.service_name, None)
        self.service_class = get_hosting_service(self.service_name)

    def setUp(self):
        self.assertNotEqual(self.service_class, None)
        self._old_http_post = self.service_class._http_post
        self._old_http_get = self.service_class._http_get

    def tearDown(self):
        self.service_class._http_post = self._old_http_post
        self.service_class._http_get = self._old_http_get

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

    def _get_hosting_account(self, use_url=False):
        if use_url:
            hosting_url = 'https://example.com'
        else:
            hosting_url = None

        return HostingServiceAccount(service_name=self.service_name,
                                     username='myuser',
                                     hosting_url=hosting_url)

    def _get_service(self):
        return self._get_hosting_account().service

    def _get_repository_fields(self, tool_name, fields, plan=None,
                               with_url=False):
        form = self._get_form(plan, fields)
        account = self._get_hosting_account(with_url)
        service = account.service
        self.assertNotEqual(service, None)

        return service.get_repository_fields(account.username,
                                             'https://example.com',
                                             plan, tool_name, form.clean())


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
            'git@mydomain.beanstalkapp.com:/myrepo.git')
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
        self.assertFalse('mirror_path' in fields)

    def test_authorize(self):
        """Testing Beanstalk authorization password storage"""
        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertTrue('password' in account.data)
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

        self.spy_on(service._http_get, call_fake=_http_get)

        service.check_repository(beanstalk_account_domain='mydomain',
                                 beanstalk_repo_name='myrepo')
        self.assertTrue(service._http_get.called)

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
        """Testing Beanstalk get_file_exists with Subversion and base commit ID"""
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
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
            self.assertEqual(
                url,
                'https://mydomain.beanstalkapp.com/api/repositories/'
                'myrepo/blob?id=%s&name=path'
                % expected_revision)
            return b'My data', {}

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'beanstalk_account_domain': 'mydomain',
            'beanstalk_repo_name': 'myrepo',
        }

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service._http_get, call_fake=_http_get)

        result = service.get_file(repository, '/path', revision,
                                  base_commit_id)
        self.assertTrue(service._http_get.called)
        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, 'My data')

    def _test_get_file_exists(self, tool_name, revision, base_commit_id,
                              expected_revision, expected_found):
        def _http_get(service, url, *args, **kwargs):
            expected_url = ('https://mydomain.beanstalkapp.com/api/'
                            'repositories/myrepo/')

            if base_commit_id:
                expected_url += ('node.json?path=/path&revision=%s&contents=0'
                                 % expected_revision)
            else:
                expected_url += 'blob?id=%s&name=path' % expected_revision

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

        self.spy_on(service._http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, '/path', revision,
                                         base_commit_id)
        self.assertTrue(service._http_get.called)
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
        service = account.service

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service._http_get, call_fake=_http_get)

        service.check_repository(bitbucket_repo_name='myrepo',
                                 plan='personal')
        self.assertTrue(service._http_get.called)

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

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service._http_get, call_fake=_http_get)

        service.check_repository(bitbucket_team_name='myteam',
                                 bitbucket_team_repo_name='myrepo',
                                 plan='team')
        self.assertTrue(service._http_get.called)

    def test_authorize(self):
        """Testing Bitbucket authorization password storage"""
        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertTrue('password' in account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

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
        """Testing Bitbucket get_file_exists with Mercurial and base commit ID"""
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

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service._http_get, call_fake=_http_get)

        result = service.get_file(repository, 'path', revision,
                                  base_commit_id)
        self.assertTrue(service._http_get.called)
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
                raise HTTPError()

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service._http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, 'path', revision,
                                         base_commit_id)
        self.assertEqual(service._http_get.called, expected_http_called)
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

    def test_service_support(self):
        """Testing the Codebase HQ service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values(self):
        """Testing the Codebase HQ repository field values"""
        fields = self._get_repository_fields('Git', fields={
            'codebasehq_project_name': 'myproj',
            'codebasehq_group_name': 'mygroup',
            'codebasehq_repo_name': 'myrepo',
            'codebasehq_api_username': 'myapiuser',
            'codebasehq_api_key': 'myapikey',
        })
        self.assertEqual(fields['username'], 'myapiuser')
        self.assertEqual(fields['password'], 'myapikey')
        self.assertEqual(fields['path'],
                         'git@codebasehq.com:mygroup/myproj/myrepo.git')
        self.assertEqual(fields['raw_file_url'],
                         'https://api3.codebasehq.com/myproj/myrepo/blob/'
                         '<revision>')


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
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'fedorahosted_repo_name': 'myrepo',
            }),
            'https://fedorahosted.org/myrepo/ticket/%s')


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
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('private-org'))
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

        self.service_class._http_post = _http_post

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service
        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass', None)
        self.assertTrue(account.is_authorized)

        self.assertEqual(http_post_data['kwargs']['url'],
                         'https://api.github.com/authorizations')
        self.assertEqual(http_post_data['kwargs']['username'], 'myuser')
        self.assertEqual(http_post_data['kwargs']['password'], 'mypass')

    def test_authorization_with_client_info(self):
        """Testing that GitHub account authorization with registered client info"""
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

        self.service_class._http_post = _http_post

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service
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
                'ref': 'refs/tags/release-1.7.11',
                'object': {
                    'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792',
                }
            },
        ])

        def _http_get(self, *args, **kwargs):
            return branches_api_response, None

        self.service_class._http_get = _http_get

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        branches = service.get_branches(repository)

        self.assertEqual(len(branches), 2)
        self.assertEqual(
            branches,
            [
                Branch('master',
                       '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                       True),
                Branch('release-1.7.x',
                       '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                       False),
            ])

    def test_get_commits(self):
        """Testing GitHub get_commits implementation"""
        commits_api_response = json.dumps([
            {
                'commit': {
                    'author': {'name': 'Christian Hammond'},
                    'committer': {'date': '2013-06-25T23:31:22Z'},
                    'message': 'Fixed the bug number for the blacktriangledown bug.',
                },
                'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                'parents': [{'sha': '92463764015ef463b4b6d1a1825fee7aeec8cb15'}],
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
                    'message': 'Add DIFF_PARSE_ERROR to the ValidateDiffResource.create error list.',
                },
                'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792',
                'parents': [],
            }
        ])

        def _http_get(self, *args, **kwargs):
            return commits_api_response, None

        self.service_class._http_get = _http_get

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        commits = service.get_commits(
            repository, '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817')

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
            ]
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
                self.assertTrue(('sha=%s' % commit_sha) in query)

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

        self.service_class._http_get = _http_get

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        change = service.get_change(repository, commit_sha)

        self.assertEqual(change.message, 'Move .clearfix to defs.less')
        self.assertEqual(md5(change.diff.encode('utf-8')).hexdigest(),
                         '5f63bd4f1cd8c4d8b46f2f72ea8d33bc')

    def test_get_change_exception(self):
        """Testing GitHub get_change exception types"""
        def _http_get(service, url, *args, **kwargs):
            raise Exception('Not Found')

        self.service_class._http_get = _http_get

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

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

    def _test_check_repository(self, expected_user='myuser', **kwargs):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api.github.com/repos/%s/myrepo?access_token=123'
                % expected_user)
            return b'{}', {}

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service._http_get, call_fake=_http_get)
        account.data['authorization'] = {
            'token': '123',
        }

        service.check_repository(**kwargs)
        self.assertTrue(service._http_get.called)

    def _test_check_repository_error(self, http_status, payload, expected_error,
                                     **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if http_status == 200:
                return payload, {}
            else:
                raise HTTPError(url, http_status, '', {}, StringIO(payload))

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service._http_get, call_fake=_http_get)
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
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
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
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'trac_url': 'http://trac.example.com',
            }),
            'http://trac.example.com/ticket/%s')


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
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'versionone_url': 'http://versionone.example.com',
            }),
            'http://versionone.example.com/assetdetail.v1?Number=%s')
