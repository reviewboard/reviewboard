"""Unit tests for the Fedora Hosted hosting service."""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.tests.testcases import ServiceTests


class FedoraHosted(ServiceTests):
    """Unit tests for the Fedora Hosted hosting service."""

    service_name = 'fedorahosted'

    def test_service_support(self):
        """Testing FedoraHosted service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_get_repository_fields_with_git(self):
        """Testing FedoraHosted.get_repository_fields for Git"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'fedorahosted_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'git://git.fedorahosted.org/git/myrepo.git',
                'raw_file_url': ('http://git.fedorahosted.org/cgit/myrepo.git/'
                                 'blob/<filename>?id=<revision>'),
            })

    def test_get_repository_fields_with_mercurial(self):
        """Testing FedoraHosted.get_repository_fields for Mercurial"""
        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                fields={
                    'fedorahosted_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'http://hg.fedorahosted.org/hg/myrepo/',
                'mirror_path': 'https://hg.fedorahosted.org/hg/myrepo/',
            })

    def test_get_repository_fields_with_subversion(self):
        """Testing FedoraHosted.get_repository_fields for Subversion"""
        self.assertEqual(
            self.get_repository_fields(
                'Subversion',
                fields={
                    'fedorahosted_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'http://svn.fedorahosted.org/svn/myrepo/',
                'mirror_path': 'https://svn.fedorahosted.org/svn/myrepo/',
            })

    def test_get_bug_tracker_field(self):
        """Testing FedoraHosted.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'fedorahosted_repo_name': 'myrepo',
            }),
            'https://fedorahosted.org/myrepo/ticket/%s')
