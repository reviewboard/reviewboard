"""Unit tests for reviewboard.cmdline.rbsite."""

from __future__ import unicode_literals

import os
import shutil
import tempfile

from reviewboard.cmdline.rbsite import (Command,
                                        MissingSiteError,
                                        UpgradeCommand,
                                        validate_site_paths)
from reviewboard.testing.testcase import TestCase


class CommandTests(TestCase):
    """Unit tests for reviewboard.cmdline.rbsite.Command."""

    def setUp(self):
        super(CommandTests, self).setUp()

        self.command = Command()

    def test_get_site_paths_with_string(self):
        """Testing Command.get_site_paths with site_path as string"""
        class Options(object):
            site_path = '/var/www/reviewboard'

        self.assertEqual(self.command.get_site_paths(Options()),
                         ['/var/www/reviewboard'])

    def test_get_site_paths_with_list(self):
        """Testing Command.get_site_paths with site_path as ststring"""
        class Options(object):
            site_path = [
                '/var/www/reviewboard1',
                '/var/www/reviewboard2',
            ]

        self.assertEqual(
            self.command.get_site_paths(Options()),
            [
                '/var/www/reviewboard1',
                '/var/www/reviewboard2',
            ])

    def test_get_site_paths_without_site_path(self):
        """Testing Command.get_site_paths without site_path"""
        class Options(object):
            site_path = None

        self.assertEqual(self.command.get_site_paths(Options()), [])


class UpgradeCommandTests(TestCase):
    """Unit tests for reviewboard.cmdline.rbsite.UpgradeCommand."""

    def setUp(self):
        super(UpgradeCommandTests, self).setUp()

        self.command = UpgradeCommand()

    def test_get_site_paths_with_all_sites(self):
        """Testing UpgradeCommand.get_site_paths with all_sites=True"""
        tmpdir = tempfile.mkdtemp(prefix='rbsite-')

        dir1 = os.path.join(tmpdir, 'site1')
        dir2 = os.path.join(tmpdir, 'site2')
        dir3 = os.path.join(tmpdir, 'site3')

        # Create 2 of the 3 site directories. The third will be excluded, since
        # it doesn't exist.
        os.mkdir(dir1, 0o755)
        os.mkdir(dir2, 0o755)

        site_filename = os.path.join(tmpdir, 'sites')

        with open(site_filename, 'w') as fp:
            fp.write('%s\n' % dir1)
            fp.write('%s\n' % dir2)
            fp.write('%s\n' % dir3)

        class Options(object):
            all_sites = True
            sitelist = site_filename

        try:
            self.assertEqual(self.command.get_site_paths(Options()),
                             {dir1, dir2})
        finally:
            shutil.rmtree(tmpdir)

    def test_get_site_paths_with_all_sites_and_empty(self):
        """Testing UpgradeCommand.get_site_paths with all_sites=True and no
        existing sites in sites file
        """
        tmpdir = tempfile.mkdtemp(prefix='rbsite-')

        # Note that we won't be creating these directories.
        dir1 = os.path.join(tmpdir, 'site1')
        dir2 = os.path.join(tmpdir, 'site2')
        dir3 = os.path.join(tmpdir, 'site3')

        site_filename = os.path.join(tmpdir, 'sites')

        with open(site_filename, 'w') as fp:
            fp.write('%s\n' % dir1)
            fp.write('%s\n' % dir2)
            fp.write('%s\n' % dir3)

        class Options(object):
            all_sites = True
            sitelist = site_filename

        expected_message = \
            'No Review Board sites were listed in %s' % site_filename

        try:
            with self.assertRaisesMessage(MissingSiteError, expected_message):
                self.command.get_site_paths(Options())
        finally:
            shutil.rmtree(tmpdir)

    def test_get_site_paths_with_string(self):
        """Testing UpgradeCommand.get_site_paths with site_path as string"""
        class Options(object):
            all_sites = False
            site_path = '/var/www/reviewboard'

        self.assertEqual(self.command.get_site_paths(Options()),
                         ['/var/www/reviewboard'])

    def test_get_site_paths_with_list(self):
        """Testing UpgradeCommand.get_site_paths with site_path as ststring"""
        class Options(object):
            all_sites = False
            site_path = [
                '/var/www/reviewboard1',
                '/var/www/reviewboard2',
            ]

        self.assertEqual(
            self.command.get_site_paths(Options()),
            [
                '/var/www/reviewboard1',
                '/var/www/reviewboard2',
            ])

    def test_get_site_paths_without_site_path(self):
        """Testing UpgradeCommand.get_site_paths without site_path"""
        class Options(object):
            all_sites = False
            site_path = None

        self.assertEqual(self.command.get_site_paths(Options()), [])


class ValidateSitePathsTests(TestCase):
    """Unit tests for reviewboard.cmdline.rbsite.validate_site_paths."""

    def test_with_valid_sites(self):
        """Testing validate_site_paths with valid sites"""
        # This should not raise.
        validate_site_paths([os.path.dirname(__file__)])

    def test_with_empty(self):
        """Testing validate_site_paths with empty list"""
        expected_message = \
            "You'll need to provide a site directory to run this command."

        with self.assertRaisesMessage(MissingSiteError, expected_message):
            validate_site_paths([])

        with self.assertRaisesMessage(MissingSiteError, expected_message):
            validate_site_paths(None)

    def test_with_missing_site(self):
        """Testing validate_site_paths with missing site"""
        expected_message = 'The site directory "/test" does not exist.'

        with self.assertRaisesMessage(MissingSiteError, expected_message):
            validate_site_paths(['/test'])

    def test_with_missing_site_and_require_exists_false(self):
        """Testing validate_site_paths with missing site and
        require_exists=False
        """
        # This should not raise.
        validate_site_paths(['/test'], require_exists=False)
