"""Unit tests for reviewboard.cmdline.rbsite."""

from __future__ import unicode_literals

import os
import shutil
import sys
import tempfile

from django.utils import six
from django.utils.six.moves import cStringIO as StringIO

from reviewboard.cmdline.rbsite import (Command,
                                        ConsoleUI,
                                        InstallCommand,
                                        ManageCommand,
                                        MissingSiteError,
                                        UpgradeCommand,
                                        parse_options,
                                        set_ui,
                                        validate_site_paths)
from reviewboard.rb_platform import SITELIST_FILE_UNIX
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
                             [dir1, dir2])
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


class ParseOptionsTests(TestCase):
    """Unit tests for reviewboard.cmdline.rbsite.parse_options."""

    @classmethod
    def setUpClass(cls):
        super(ParseOptionsTests, cls).setUpClass()

        set_ui(ConsoleUI(allow_color=False))

        cls._tempdir = tempfile.mkdtemp(prefix='rb-site-')

        cls.sitelist_filename = os.path.join(cls._tempdir, 'sitelist.txt')
        cls.sitedir1 = os.path.join(cls._tempdir, 'site1')
        cls.sitedir2 = os.path.join(cls._tempdir, 'site2')
        cls.invalid_sitedir = os.path.join(cls._tempdir, 'invalid')

        with open(cls.sitelist_filename, 'w') as fp:
            fp.write('%s\n' % cls.sitedir1)
            fp.write('%s\n' % cls.sitedir2)

        os.mkdir(cls.sitedir1, 0o755)
        os.mkdir(cls.sitedir2, 0o755)

    @classmethod
    def tearDownClass(cls):
        super(ParseOptionsTests, cls).tearDownClass()

        shutil.rmtree(cls._tempdir)
        cls._tempdir = None

        set_ui(None)

    def setUp(self):
        super(ParseOptionsTests, self).setUp()

        # We want to capture both stdout and stderr. Nose takes care of
        # stdout for us, but not stderr, so that's our responsibility.
        self._old_stderr = sys.stderr
        sys.stderr = StringIO()

    def tearDown(self):
        sys.stderr = self._old_stderr
        self._old_stderr = None

        super(ParseOptionsTests, self).tearDown()

    def test_with_no_options(self):
        """Testing rb-site parse_options with no options"""
        self.assertIsNone(parse_options([]))

        help_text = sys.stdout.getvalue()
        self.assertTrue(help_text.startswith('usage: rb-site [-h]'))
        self.assertIn('rb-site helps create, upgrade', help_text)

    def test_with_help_only(self):
        """Testing rb-site parse_options with --help only"""
        with self.assertRaises(SystemExit):
            parse_options(['--help'])

        help_text = sys.stdout.getvalue()
        self.assertTrue(help_text.startswith('usage: rb-site [-h]'))
        self.assertIn('rb-site helps create, upgrade', help_text)

    def test_with_help_first(self):
        """Testing rb-site parse_options with --help as first option"""
        with self.assertRaises(SystemExit):
            parse_options(['--help', 'install', self.sitedir1])

        help_text = sys.stdout.getvalue()
        self.assertTrue(help_text.startswith('usage: rb-site [-h]'))
        self.assertIn('rb-site helps create, upgrade', help_text)

    def test_with_help_as_command_option(self):
        """Testing rb-site parse_options with --help as command option"""
        with self.assertRaises(SystemExit):
            parse_options(['install', self.sitedir1, '--help'])

        help_text = sys.stdout.getvalue()
        self.assertTrue(help_text.startswith('usage: rb-site install'))
        self.assertIn('This will guide you through installing', help_text)

    def test_with_install(self):
        """Testing rb-site parse_options with install"""
        sitedir = os.path.join(self.sitedir1, 'newdir')

        result = parse_options(['install', sitedir])

        self.assertIsNotNone(result)
        self.assertIsInstance(result['command'], InstallCommand)
        self.assertEqual(result['site_paths'], [sitedir])

    def test_with_upgrade(self):
        """Testing rb-site parse_options with upgrade"""
        result = parse_options(['upgrade', self.sitedir1])

        self.assertIsNotNone(result)
        self.assertIsInstance(result['command'], UpgradeCommand)
        self.assertEqual(result['site_paths'], [self.sitedir1])

    def test_with_upgrade_with_invalid_site_dir(self):
        """Testing rb-site parse_options with upgrade with invalid site
        directory
        """
        expected_error = (
            'The site directory "%s" does not exist.'
            % self.invalid_sitedir
        )

        with self.assertRaisesMessage(MissingSiteError, expected_error):
            parse_options(['upgrade', self.invalid_sitedir])

    def test_with_upgrade_with_no_site_dir(self):
        """Testing rb-site parse_options with upgrade and no site directory"""
        expected_message = \
            "You'll need to provide a site directory to run this command."

        with self.assertRaisesMessage(MissingSiteError, expected_message):
            parse_options(['upgrade'])

    def test_with_upgrade_with_all_sites_not_stored(self):
        """Testing rb-site parse_options with upgrade and --all-sites but no
        stored site
        """
        expected_message = \
            "No Review Board sites were listed in %s" % SITELIST_FILE_UNIX

        with self.assertRaisesMessage(MissingSiteError, expected_message):
            parse_options(['upgrade', '--all-sites'])

    def test_with_upgrade_with_all_sites_and_stored(self):
        """Testing rb-site parse_options with upgrade and --all-sites and
        sites stored
        """
        result = parse_options(['upgrade', '--all-sites', '--sitelist',
                                self.sitelist_filename])

        self.assertIsNotNone(result)
        self.assertIsInstance(result['command'], UpgradeCommand)
        self.assertEqual(result['site_paths'], [self.sitedir1, self.sitedir2])

    def test_with_manage_with_invalid_site_dir(self):
        """Testing rb-site parse_options with manage with invalid site
        directory
        """
        expected_error = (
            'The site directory "%s" does not exist.'
            % self.invalid_sitedir
        )

        with self.assertRaisesMessage(MissingSiteError, expected_error):
            parse_options(['manage', self.invalid_sitedir, 'my-command'])

    def test_with_manage_with_command(self):
        """Testing rb-site parse_options with manage and command"""
        result = parse_options(['manage', self.sitedir1, 'my-command'])

        self.assertIsNotNone(result)
        self.assertIsInstance(result['command'], ManageCommand)
        self.assertEqual(result['site_paths'], [self.sitedir1])
        self.assertEqual(result['options'].manage_command, ['my-command'])

    def test_with_manage_with_command_and_args(self):
        """Testing rb-site parse_options with manage and command and args"""
        result = parse_options([
            'manage', self.sitedir1, 'my-command', '--arg1', '--arg2',
            'arg3',
        ])

        self.assertIsNotNone(result)
        self.assertIsInstance(result['command'], ManageCommand)
        self.assertEqual(result['site_paths'], [self.sitedir1])
        self.assertEqual(result['options'].manage_command,
                         ['my-command', '--arg1', '--arg2', 'arg3'])

    def test_with_manage_with_command_and_help_arg(self):
        """Testing rb-site parse_options with manage and command and --help
        argument
        """
        result = parse_options([
            'manage', self.sitedir1, 'my-command', '--help'
        ])

        self.assertIsNotNone(result)
        self.assertIsInstance(result['command'], ManageCommand)
        self.assertEqual(result['site_paths'], [self.sitedir1])
        self.assertEqual(result['options'].manage_command,
                         ['my-command', '--help'])

    def test_with_manage_no_command(self):
        """Testing rb-site parse_options with manage and no command"""
        with self.assertRaises(SystemExit):
            parse_options(['manage', self.sitedir1])

        output = sys.stderr.getvalue()
        self.assertTrue(output.startswith('usage: rb-site manage [-h]'))

        if six.PY3:
            self.assertIn(
                'rb-site manage: error: the following arguments are '
                'required: <command> <args>',
                output)
        else:
            self.assertIn('rb-site manage: error: too few arguments', output)

    def test_with_invalid_command(self):
        """Testing rb-site parse_options with invalid command"""
        with self.assertRaises(SystemExit):
            parse_options(['frob', self.sitedir1])

        output = sys.stderr.getvalue()
        self.assertTrue(output.startswith('usage: rb-site [-h]'))
        self.assertIn('rb-site: error: invalid choice:', output)


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
