"""Unit tests for the ReviewBoardGateway hosting service."""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password


class ReviewBoardGatewayTests(HostingServiceTestCase):
    """Unit tests for the ReviewBoardGateway hosting service."""

    service_name = 'rbgateway'

    default_use_hosting_url = True
    default_account_data = {
        'private_token': encrypt_password('abc123'),
    }

    default_repository_extra_data = {
        'rbgateway_repo_name': 'myrepo',
    }

    def test_service_support(self):
        """Testing ReviewBoardGateway service support capabilities"""
        self.assertTrue(self.service_class.supports_repositories)
        self.assertTrue(self.service_class.supports_post_commit)
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_repo_field_values(self):
        """Testing ReviewBoardGateway.get_repository_fields for Git"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'hosting_url': 'https://example.com',
                    'rbgateway_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'https://example.com/repos/myrepo/path',
            })

    def test_authorize(self):
        """Testing ReviewBoardGateway.authorize"""
        hosting_account = self.create_hosting_account(data={})
        self.assertFalse(hosting_account.is_authorized)

        with self.setup_http_test(payload=b'{"private_token": "abc123"}',
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            ctx.service.authorize(username='myuser',
                                  password='mypass',
                                  hosting_url='https://example.com')

        self.assertTrue(hosting_account.is_authorized)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/session',
            method='POST',
            body='',
            headers={
                'Content-Length': '0',
            })

    def test_check_repository(self):
        """Testing ReviewBoardGateway.check_repository"""
        with self.setup_http_test(payload=b'{}',
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(
                path='https://example.com/repos/myrepo/path')

        ctx.assertHTTPCall(
            0,
            url='https://example.com/repos/myrepo/path',
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_get_branches(self):
        """Testing ReviewBoardGateway.get_branches"""
        payload = self.dump_json([
            {
                'name': 'master',
                'id': 'c272edcac05b00e15440d6274723b639e3acbd7c',
            },
            {
                'name': 'im_a_branch',
                'id': '83904e6acb60e7ec0dcaae6c09a579ab44d0cf38',
            }
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/repos/myrepo/branches',
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            })

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
        payload = self.dump_json([
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

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            commits = ctx.service.get_commits(
                repository=repository,
                branch='bfdde95432b3af879af969bd2377dc3e55ee46e6')

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/repos/myrepo/branches/'
                 'bfdde95432b3af879af969bd2377dc3e55ee46e6/commits'),
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            })

        self.assertEqual(
            commits,
            [
                Commit(author_name='Author 1',
                       date='2015-02-13 22:34:01 -0700',
                       id='bfdde95432b3af879af969bd2377dc3e55ee46e6',
                       message='Message 1',
                       parent='304c53c163aedfd0c0e0933776f09c24b87f5944'),
                Commit(author_name='Author 2',
                       date='2015-02-13 22:32:42 -0700',
                       id='304c53c163aedfd0c0e0933776f09c24b87f5944',
                       message='Message 2',
                       parent='fa1330719893098ae397356e8125c2aa45b49221'),
                Commit(author_name='Author 3',
                       date='2015-02-12 16:01:48 -0700',
                       id='fa1330719893098ae397356e8125c2aa45b49221',
                       message='Message 3',
                       parent=''),
            ])

        for commit in commits:
            self.assertIsNone(commit.diff)

    def test_get_change(self):
        """Testing ReviewBoardGateway.get_change"""
        diff = (
            'diff --git a/test b/test\n'
            'index 9daeafb9864cf43055ae93beb0afd6c7d144bfa4..'
            'dced80a85fe1e8f13dd5ea19923e5d2e8680020d 100644\n'
            '--- a/test\n'
            '+++ b/test\n'
            '@@ -1 +1,3 @@\n'
            ' test\n'
            '+\n'
            '+test\n'
        )

        payload = self.dump_json({
            'author': 'Some Author',
            'id': 'bfdde95432b3af879af969bd2377dc3e55ee46e6',
            'date': '2015-02-13 22:34:01 -0700',
            'message': 'My Message',
            'parent_id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
            'diff': diff,
        })

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            change = ctx.service.get_change(
                repository=repository,
                revision='bfdde95432b3af879af969bd2377dc3e55ee46e6')

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/repos/myrepo/commits/'
                 'bfdde95432b3af879af969bd2377dc3e55ee46e6'),
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            })

        self.assertEqual(
            change,
            Commit(author_name='Some Author',
                   date='2015-02-13 22:34:01 -0700',
                   id='bfdde95432b3af879af969bd2377dc3e55ee46e6',
                   message='My Message',
                   parent='304c53c163aedfd0c0e0933776f09c24b87f5944'))
        self.assertEqual(change.diff, diff.encode('utf-8'))
