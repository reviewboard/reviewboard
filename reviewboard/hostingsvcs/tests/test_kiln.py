"""Unit tests for the Kiln hosting service."""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.service import HostingServiceClient
from reviewboard.hostingsvcs.testing import HostingServiceTestCase


class KilnTests(HostingServiceTestCase):
    """Unit tests for the Kiln hosting service."""

    service_name = 'kiln'
    fixtures = ['test_scmtools']

    default_account_data = {
        'auth_token': 'my-token',
        'kiln_account_domain': 'mydomain',
    }

    default_repository_extra_data = {
        'kiln_account_domain': 'mydomain',
        'kiln_project_name': 'myproject',
        'kiln_group_name': 'mygroup',
        'kiln_repo_name': 'myrepo',
    }

    def test_service_support(self):
        """Testing Kiln service support capabilities"""
        self.assertTrue(self.service_class.supports_repositories)
        self.assertTrue(self.service_class.needs_authorization)
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_post_commit)
        self.assertFalse(self.service_class.supports_two_factor_auth)

    def test_repo_field_values_git(self):
        """Testing Kiln.get_repository_fields for Git"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'kiln_account_domain': 'mydomain',
                    'kiln_project_name': 'myproject',
                    'kiln_group_name': 'mygroup',
                    'kiln_repo_name': 'myrepo',
                }
            ),
            {
                'path': ('https://mydomain.kilnhg.com/Code/myproject/mygroup/'
                         'myrepo.git'),
                'mirror_path': ('ssh://mydomain@mydomain.kilnhg.com/myproject/'
                                'mygroup/myrepo'),
            })

    def test_repo_field_values_mercurial(self):
        """Testing Kiln.get_repository_fields for Mercurial"""
        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                fields={
                    'kiln_account_domain': 'mydomain',
                    'kiln_project_name': 'myproject',
                    'kiln_group_name': 'mygroup',
                    'kiln_repo_name': 'myrepo',
                }
            ),
            {
                'path': ('https://mydomain.kilnhg.com/Code/myproject/mygroup/'
                         'myrepo'),
                'mirror_path': ('ssh://mydomain@mydomain.kilnhg.com/myproject/'
                                'mygroup/myrepo'),
            })

    def test_authorize(self):
        """Testing Kiln.authorize"""
        hosting_account = self.create_hosting_account(data={})

        self.spy_on(HostingServiceClient._make_form_data_boundary,
                    call_fake=lambda: 'BOUNDARY')

        with self.setup_http_test(payload=b'"my-token"',
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            self.assertFalse(ctx.service.is_authorized())

            ctx.service.authorize(username='myuser',
                                  password='abc123',
                                  kiln_account_domain='mydomain')

        ctx.assertHTTPCall(
            0,
            url='https://mydomain.kilnhg.com/Api/1.0/Auth/Login',
            method='POST',
            username=None,
            password=None,
            body=(
                b'--BOUNDARY\r\n'
                b'Content-Disposition: form-data; name="sPassword"\r\n\r\n'
                b'abc123\r\n'
                b'--BOUNDARY\r\n'
                b'Content-Disposition: form-data; name="sUser"\r\n\r\n'
                b'myuser\r\n'
                b'--BOUNDARY--'
            ),
            headers={
                'Content-Length': '152',
                'Content-Type': 'multipart/form-data; boundary=BOUNDARY',
            })

        self.assertIn('auth_token', hosting_account.data)
        self.assertEqual(hosting_account.data['auth_token'], 'my-token')
        self.assertTrue(ctx.service.is_authorized())

    def test_check_repository(self):
        """Testing Kiln.check_repository"""
        payload = self.dump_json([{
            'sSlug': 'myproject',
            'repoGroups': [{
                'sSlug': 'mygroup',
                'repos': [{
                    'sSlug': 'myrepo',
                }]
            }]
        }])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(kiln_account_domain='mydomain',
                                         kiln_project_name='myproject',
                                         kiln_group_name='mygroup',
                                         kiln_repo_name='myrepo',
                                         tool_name='Mercurial')

        ctx.assertHTTPCall(
            0,
            url='https://mydomain.kilnhg.com/Api/1.0/Project?token=my-token',
            username=None,
            password=None)

    def test_check_repository_with_incorrect_repo_info(self):
        """Testing Kiln.check_repository with incorrect repo info"""
        payload = self.dump_json([{
            'sSlug': 'otherproject',
            'repoGroups': [{
                'sSlug': 'othergroup',
                'repos': [{
                    'sSlug': 'otherrepo',
                }]
            }]
        }])

        expected_message = (
            'The repository with this project, group, and name was not found. '
            'Please verify that the information exactly matches the '
            'configuration on Kiln.'
        )

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_message):
                ctx.service.check_repository(kiln_account_domain='mydomain',
                                             kiln_project_name='myproject',
                                             kiln_group_name='mygroup',
                                             kiln_repo_name='myrepo',
                                             tool_name='Mercurial')

        ctx.assertHTTPCall(
            0,
            url='https://mydomain.kilnhg.com/Api/1.0/Project?token=my-token',
            username=None,
            password=None)

    def test_get_file(self):
        """Testing Kiln.get_file"""
        paths = {
            '/Api/1.0/Project': {
                'payload': self.dump_json([{
                    'sSlug': 'myproject',
                    'repoGroups': [{
                        'sSlug': 'mygroup',
                        'repos': [{
                            'sSlug': 'myrepo',
                            'ixRepo': 123,
                        }]
                    }]
                }]),
            },
            '/Api/1.0/Repo/123/Raw/File/2F70617468': {
                'payload': b'My data',
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=2) as ctx:
            repository = ctx.create_repository(tool_name='Mercurial')
            result = ctx.service.get_file(repository=repository,
                                          path='/path',
                                          revision='123')

        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b'My data')

        ctx.assertHTTPCall(
            0,
            url='https://mydomain.kilnhg.com/Api/1.0/Project?token=my-token',
            method='GET',
            username=None,
            password=None)

        ctx.assertHTTPCall(
            1,
            url=('https://mydomain.kilnhg.com/Api/1.0/Repo/123/Raw/File/'
                 '2F70617468?rev=123&token=my-token'),
            username=None,
            password=None)

    def test_get_file_exists(self):
        """Testing Kiln.get_file_exists"""
        paths = {
            '/Api/1.0/Project': {
                'payload': self.dump_json([{
                    'sSlug': 'myproject',
                    'repoGroups': [{
                        'sSlug': 'mygroup',
                        'repos': [{
                            'sSlug': 'myrepo',
                            'ixRepo': 123,
                        }]
                    }]
                }]),
            },
            '/Api/1.0/Repo/123/Raw/File/2F70617468': {
                'payload': b'My data',
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=2) as ctx:
            repository = ctx.create_repository()
            result = ctx.service.get_file_exists(repository=repository,
                                                 path='/path',
                                                 revision='123')

        self.assertTrue(result)

        ctx.assertHTTPCall(
            0,
            url='https://mydomain.kilnhg.com/Api/1.0/Project?token=my-token',
            username=None,
            password=None)

        ctx.assertHTTPCall(
            1,
            url=('https://mydomain.kilnhg.com/Api/1.0/Repo/123/Raw/File/'
                 '2F70617468?rev=123&token=my-token'),
            username=None,
            password=None)
