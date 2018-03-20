"""Unit tests for the ReviewBoardGateway hosting service."""

from __future__ import unicode_literals

import json

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.core import Branch
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.models import Repository


class ReviewBoardGatewayTests(ServiceTests):
    """Unit tests for the ReviewBoardGateway hosting service."""

    service_name = 'rbgateway'

    def test_service_support(self):
        """Testing ReviewBoardGateway service support capabilities"""
        self.assertTrue(self.service_class.supports_repositories)
        self.assertTrue(self.service_class.supports_post_commit)
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_repo_field_values(self):
        """Testing ReviewBoardGateway.get_repository_fields for Git"""
        fields = self._get_repository_fields('Git', fields={
            'hosting_url': 'https://example.com',
            'rbgateway_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'https://example.com/repos/myrepo/path')

    def test_authorization(self):
        """Testing ReviewBoardGateway.authorize"""
        def _http_request(client, *args, **kwargs):
            return b'{"private_token": "abc123"}', {}


        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass',
                          hosting_url='https://example.com')
        self.assertTrue(account.is_authorized)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://example.com/session',
            method='POST',
            username='myuser',
            password='mypass',
            body='',
            headers={
                'Content-Length': '0',
            }))

    def test_check_repository(self):
        """Testing ReviewBoardGateway.check_repository"""
        def _http_request(client, *args, **kwargs):
            return b'{}', {}

        account = self._get_hosting_account(use_url=True)
        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        account.data['private_token'] = encrypt_password('abc123')

        service.check_repository(path='https://example.com/repos/myrepo/path')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://example.com/repos/myrepo/path',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            }))

    def test_get_branches(self):
        """Testing ReviewBoardGateway.get_branches"""
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

        def _http_request(client, *args, **kwargs):
            return branches_api_response.encode('utf-8'), {}

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'rbgateway_repo_name': 'myrepo',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        branches = service.get_branches(repository)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://example.com/repos/myrepo/branches',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            }))

        self.assertEqual(len(branches), 2)
        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='c272edcac05b00e15440d6274723b639e3acbd7c',
                       default=True),
                Branch(id='im_a_branch',
                       commit='83904e6acb60e7ec0dcaae6c09a579ab44d0cf38'),
            ])

    def test_get_commits(self):
        """Testing ReviewBoardGateway.get_commits"""
        commits_api_response = json.dumps([
            {
                'author': 'Author 1',
                'id': 'bfdde95432b3af879af969bd2377dc3e55ee46e6',
                'date': '2015-02-13 22:34:01 -0700',
                'message': 'Message 1',
                'parent_id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
            },
            {
                'author': 'Author 2',
                'id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
                'date': '2015-02-13 22:32:42 -0700',
                'message': 'Message 2',
                'parent_id': 'fa1330719893098ae397356e8125c2aa45b49221',
            },
            {
                'author': 'Author 3',
                'id': 'fa1330719893098ae397356e8125c2aa45b49221',
                'date': '2015-02-12 16:01:48 -0700',
                'message': 'Message 3',
                'parent_id': '',
            }
        ])

        def _http_request(client, *args, **kwargs):
            return commits_api_response.encode('utf-8'), {}

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'rbgateway_repo_name': 'myrepo',
        }

        service = account.service
        client = service.client
        self.spy_on(client.http_request, call_fake=_http_request)

        commits = service.get_commits(
            repository,
            branch='bfdde95432b3af879af969bd2377dc3e55ee46e6')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url=('https://example.com/repos/myrepo/branches/'
                 'bfdde95432b3af879af969bd2377dc3e55ee46e6/commits'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            }))

        self.assertEqual(len(commits), 3)
        commit = commits[0]
        self.assertEqual(commit.author_name, 'Author 1')
        self.assertEqual(commit.date, '2015-02-13 22:34:01 -0700')
        self.assertEqual(commit.id, 'bfdde95432b3af879af969bd2377dc3e55ee46e6')
        self.assertEqual(commit.message, 'Message 1')
        self.assertEqual(commit.parent, commits[1].id)

        commit = commits[1]
        self.assertEqual(commit.author_name, 'Author 2')
        self.assertEqual(commit.date, '2015-02-13 22:32:42 -0700')
        self.assertEqual(commit.id, '304c53c163aedfd0c0e0933776f09c24b87f5944')
        self.assertEqual(commit.message, 'Message 2')
        self.assertEqual(commit.parent, commits[2].id)

        commit = commits[2]
        self.assertEqual(commit.author_name, 'Author 3')
        self.assertEqual(commit.date, '2015-02-12 16:01:48 -0700')
        self.assertEqual(commit.id, 'fa1330719893098ae397356e8125c2aa45b49221')
        self.assertEqual(commit.message, 'Message 3')
        self.assertEqual(commit.parent, '')

    def test_get_change(self):
        """Testing ReviewBoardGateway.get_change"""
        diff = (
            b'diff --git a/test b/test\n'
            b'index 9daeafb9864cf43055ae93beb0afd6c7d144bfa4..'
            b'dced80a85fe1e8f13dd5ea19923e5d2e8680020d 100644\n'
            b'--- a/test\n'
            b'+++ b/test\n'
            b'@@ -1 +1,3 @@\n'
            b' test\n'
            b'+\n'
            b'+test\n'
        )

        change_api_response = json.dumps({
            'author': 'Some Author',
            'id': 'bfdde95432b3af879af969bd2377dc3e55ee46e6',
            'date': '2015-02-13 22:34:01 -0700',
            'message': 'My Message',
            'parent_id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
            'diff': diff,
        })

        def _http_request(client, *args, **kwargs):
            return change_api_response.encode('utf-8'), {}

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'rbgateway_repo_name': 'myrepo',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        change = service.get_change(repository,
                                    'bfdde95432b3af879af969bd2377dc3e55ee46e6')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url=('https://example.com/repos/myrepo/commits/'
                 'bfdde95432b3af879af969bd2377dc3e55ee46e6'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            }))

        self.assertEqual(change.author_name, 'Some Author')
        self.assertEqual(change.id, 'bfdde95432b3af879af969bd2377dc3e55ee46e6')
        self.assertEqual(change.date, '2015-02-13 22:34:01 -0700')
        self.assertEqual(change.message, 'My Message')
        self.assertEqual(change.parent,
                         '304c53c163aedfd0c0e0933776f09c24b87f5944')
        self.assertEqual(change.diff, diff)
