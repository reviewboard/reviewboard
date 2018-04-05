"""Unit tests for the SourceForge hosting service."""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.tests.testcases import ServiceTests


class SourceForgeTests(ServiceTests):
    """Unit tests for the SourceForge hosting service."""

    service_name = 'sourceforge'

    def test_service_support(self):
        """Testing SourceForge service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_get_repository_fields_with_bazaar(self):
        """Testing SourceForge.get_repository_fields for Bazaar"""
        self.assertEqual(
            self.get_repository_fields(
                'Bazaar',
                fields={
                    'sourceforge_project_name': 'myproj',
                }
            ),
            {
                'path': 'bzr://myproj.bzr.sourceforge.net/bzrroot/myproj',
                'mirror_path': ('bzr+ssh://myproj.bzr.sourceforge.net/bzrroot/'
                                'myproj'),
            })

    def test_get_repository_fields_with_cvs(self):
        """Testing SourceForge.get_repository_fields for CVS"""
        self.assertEqual(
            self.get_repository_fields(
                'CVS',
                fields={
                    'sourceforge_project_name': 'myproj',
                }
            ),
            {
                'path': (':pserver:anonymous@myproj.cvs.sourceforge.net:'
                         '/cvsroot/myproj'),
                'mirror_path': 'myproj.cvs.sourceforge.net/cvsroot/myproj',
            })

    def test_get_repository_fields_with_mercurial(self):
        """Testing SourceForge.get_repository_fields for Mercurial"""
        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                fields={
                    'sourceforge_project_name': 'myproj',
                }
            ),
            {
                'path': 'http://myproj.hg.sourceforge.net:8000/hgroot/myproj',
                'mirror_path': 'ssh://myproj.hg.sourceforge.net/hgroot/myproj',
            })

    def test_get_repository_fields_with_svn(self):
        """Testing SourceForge.get_repository_fields for Subversion"""
        self.assertEqual(
            self.get_repository_fields(
                'Subversion',
                fields={
                    'sourceforge_project_name': 'myproj',
                }
            ),
            {
                'path': 'http://myproj.svn.sourceforge.net/svnroot/myproj',
                'mirror_path': ('https://myproj.svn.sourceforge.net/svnroot/'
                                'myproj'),
            })
