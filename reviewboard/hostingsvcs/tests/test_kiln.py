from __future__ import unicode_literals

import json

from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.models import Repository, Tool


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
