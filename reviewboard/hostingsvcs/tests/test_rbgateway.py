from __future__ import unicode_literals

import json
from hashlib import md5

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.core import Branch
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.models import Repository


class ReviewBoardGatewayTests(ServiceTests):
    """Unit tests for the ReviewBoardGateway hosting service."""

    service_name = 'rbgateway'

    def test_service_support(self):
        """Testing the ReviewBoardGateway service support capabilities"""
        self.assertTrue(self.service_class.supports_repositories)
        self.assertTrue(self.service_class.supports_post_commit)
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_repo_field_values(self):
        """Testing the ReviewBoardGateway repository field values"""
        fields = self._get_repository_fields('Git', fields={
            'hosting_url': 'https://example.com',
            'rbgateway_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'https://example.com/repos/myrepo/path')

    def test_authorization(self):
        """Testing that ReviewBoardGateway authorization sends expected data"""
        http_post_data = {}

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return json.dumps({
                'private_token': 'abc123'
            }), {}

        self.service_class._http_post = _http_post

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service

        self.spy_on(service.client.http_post, call_fake=_http_post)

        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass',
                          hosting_url='https://example.com')
        self.assertTrue(account.is_authorized)

        self.assertEqual(http_post_data['kwargs']['url'],
                         'https://example.com/session')
        self.assertIn('username', http_post_data['kwargs'])
        self.assertIn('password', http_post_data['kwargs'])

    def test_check_repository(self):
        """Testing that ReviewBoardGateway can find the repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(url, 'https://example.com/repos/myrepo/path')
            return '{}', {}

        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        service.check_repository(path='https://example.com/repos/myrepo/path')
        self.assertTrue(service.client.http_get.called)

    def test_get_branches(self):
        """Testing ReviewBoardGateway get_branches implementation"""
        branches_api_response = json.dumps([
            {
                'name': 'master',
                'id': 'c272edcac05b00e15440d6274723b639e3acbd7c',
            },
            {
                'name': 'im_a_branch',
                'id': '83904e6acb60e7ec0dcaae6c09a579ab44d0cf38',
            }
        ])

        def _http_get(self, *args, **kwargs):
            return branches_api_response, None

        account = self._get_hosting_account()
        account.data['private_token'] = encrypt_password('abc123')

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'rbgateway_repo_name': 'myrepo',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        branches = service.get_branches(repository)

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(len(branches), 2)

        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='c272edcac05b00e15440d6274723b639e3acbd7c',
                       default=True),
                Branch(id='im_a_branch',
                       commit='83904e6acb60e7ec0dcaae6c09a579ab44d0cf38',
                       default=False)
            ])

    def test_get_commits(self):
        """Testing ReviewBoardGateway get_commits implementation"""
        commits_api_response = json.dumps([
            {
                'author': 'myname',
                'id': 'bfdde95432b3af879af969bd2377dc3e55ee46e6',
                'date': '2015-02-13 22:34:01 -0700 -0700',
                'message': 'mymessage',
                'parent_id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
            },
            {
                'author': 'myname',
                'id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
                'date': '2015-02-13 22:32:42 -0700 -0700',
                'message': 'mymessage',
                'parent_id': 'fa1330719893098ae397356e8125c2aa45b49221',
            },
            {
                'author': 'anothername',
                'id': 'fa1330719893098ae397356e8125c2aa45b49221',
                'date': '2015-02-12 16:01:48 -0700 -0700',
                'message': 'mymessage',
                'parent_id': '',
            }
        ])

        def _http_get(self, *args, **kwargs):
            return commits_api_response, None

        account = self._get_hosting_account()
        account.data['private_token'] = encrypt_password('abc123')

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'rbgateway_repo_name': 'myrepo',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        commits = service.get_commits(
            repository, branch='bfdde95432b3af879af969bd2377dc3e55ee46e6')

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0].parent, commits[1].id)
        self.assertEqual(commits[1].parent, commits[2].id)
        self.assertEqual(commits[0].date, '2015-02-13 22:34:01 -0700 -0700')
        self.assertEqual(commits[1].id,
                         '304c53c163aedfd0c0e0933776f09c24b87f5944')
        self.assertEqual(commits[2].author_name, 'anothername')
        self.assertEqual(commits[2].parent, '')

    def test_get_change(self):
        """Testing ReviewBoardGateway get_change implementation"""
        diff = (b'diff --git a/test b/test\n'
                'index 9daeafb9864cf43055ae93beb0afd6c7d144bfa4..'
                'dced80a85fe1e8f13dd5ea19923e5d2e8680020d 100644\n'
                '--- a/test\n+++ b/test\n@@ -1 +1,3 @@\n test\n+\n+test\n')

        diff_encoding = md5(diff.encode('utf-8')).hexdigest()

        change_api_response = json.dumps(
            {
                'author': 'myname',
                'id': 'bfdde95432b3af879af969bd2377dc3e55ee46e6',
                'date': '2015-02-13 22:34:01 -0700 -0700',
                'message': 'mymessage',
                'parent_id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
                'diff': diff
            }
        )

        def _http_get(self, *args, **kwargs):
            return change_api_response, None

        account = self._get_hosting_account()
        account.data['private_token'] = encrypt_password('abc123')

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'rbgateway_repo_name': 'myrepo',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        change = service.get_change(
            repository, 'bfdde95432b3af879af969bd2377dc3e55ee46e6')

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(change.message, 'mymessage')
        self.assertEqual(md5(change.diff.encode('utf-8')).hexdigest(),
                         diff_encoding)
