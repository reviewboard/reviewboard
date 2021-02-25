"""Unit tests for reviewboard.cmdline.rbsite."""

from __future__ import unicode_literals

import os
import shutil
import sys
import tempfile

import kgb
from django.utils import six
from django.utils.six.moves import cStringIO as StringIO

from reviewboard.cmdline.rbsite import (Command,
                                        InstallCommand,
                                        ManageCommand,
                                        MissingSiteError,
                                        Site,
                                        UpgradeCommand,
                                        parse_options,
                                        validate_site_paths)
from reviewboard.cmdline.utils.console import init_console, uninit_console
from reviewboard.rb_platform import SITELIST_FILE_UNIX
from reviewboard.testing.testcase import TestCase


class BaseRBSiteTestCase(TestCase):
    """Base class for rb-site unit tests.

    This handles setting up some initial site directories for tests and
    redirecting stderr for capture.
    """

    #: Whether the unit tests need site directories to work with.
    needs_sitedirs = False

    @classmethod
    def setUpClass(cls):
        super(BaseRBSiteTestCase, cls).setUpClass()

        init_console(allow_color=False)

        if cls.needs_sitedirs:
            cls._tempdir = tempfile.mkdtemp(prefix='rb-site-')

            cls.sitelist_filename = os.path.join(cls._tempdir, 'sitelist.txt')
            cls.sitedir1 = os.path.join(cls._tempdir, 'site1')
            cls.sitedir2 = os.path.join(cls._tempdir, 'site2')
            cls.invalid_sitedir = os.path.join(cls._tempdir, 'invalid')

            with open(cls.sitelist_filename, 'w') as fp:
                fp.write('%s\n' % cls.sitedir1)
                fp.write('%s\n' % cls.sitedir2)

            os.mkdir(cls.sitedir1, 0o755)
            os.mkdir(os.path.join(cls.sitedir1, 'conf'), 0o755)

            os.mkdir(cls.sitedir2, 0o755)
            os.mkdir(os.path.join(cls.sitedir2, 'conf'), 0o755)
            os.mkdir(os.path.join(cls.sitedir2, 'htdocs'), 0o755)

    @classmethod
    def tearDownClass(cls):
        super(BaseRBSiteTestCase, cls).tearDownClass()

        if cls.needs_sitedirs and cls._tempdir:
            shutil.rmtree(cls._tempdir)
            cls._tempdir = None

        uninit_console()

    def setUp(self):
        super(BaseRBSiteTestCase, self).setUp()

        # We want to capture both stdout and stderr. Nose takes care of
        # stdout for us, but not stderr, so that's our responsibility.
        self._old_stderr = sys.stderr
        sys.stderr = StringIO()

    def tearDown(self):
        sys.stderr = self._old_stderr
        self._old_stderr = None

        super(BaseRBSiteTestCase, self).tearDown()


class CommandTests(BaseRBSiteTestCase):
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


class UpgradeCommandTests(BaseRBSiteTestCase):
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


class ParseOptionsTests(BaseRBSiteTestCase):
    """Unit tests for reviewboard.cmdline.rbsite.parse_options."""

    needs_sitedirs = True

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


class SiteTests(kgb.SpyAgency, BaseRBSiteTestCase):
    """Unit tests for reviewboard.cmdline.rbsite.Site."""

    needs_sitedirs = True

    def test_generate_settings_local_with_mysql(self):
        """Testing Site.generate_settings_local with MySQL"""
        site = Site(install_dir=self.sitedir1,
                    options={})
        site.domain_name = 'reviews.example.com'
        site.db_type = 'mysql'
        site.db_name = 'test-database'
        site.db_user = 'test-user'
        site.db_pass = 'test-pass'
        site.db_host = 'db.example.com'
        site.db_port = 12345
        site.cache_info = 'localhost:1666'
        site.cache_type = 'memcached'
        site.secret_key = \
            'acdef12345acdef123456abcdef123456abcdef12345abcdef12345'

        site.generate_settings_local()

        self._check_settings_local(
            self.sitedir1,
            'DATABASES = {\n'
            '    "default": {\n'
            '        "ENGINE": "django.db.backends.mysql",\n'
            '        "NAME": "test-database",\n'
            '        "USER": "test-user",\n'
            '        "PASSWORD": "test-pass",\n'
            '        "HOST": "db.example.com",\n'
            '        "PORT": 12345\n'
            '    }\n'
            '}\n'
            'CACHES = {\n'
            '    "default": {\n'
            '        "BACKEND": "django.core.cache.backends.memcached'
            '.MemcachedCache",\n'
            '        "LOCATION": "localhost:1666"\n'
            '    }\n'
            '}\n'
            'SECRET_KEY = "acdef12345acdef123456abcdef123456abcdef12345'
            'abcdef12345"\n'
            'SITE_ROOT = ""\n'
            'DEBUG = False\n'
            'ALLOWED_HOSTS = [\n'
            '    "reviews.example.com"\n'
            ']\n')

    def test_generate_settings_local_with_postgres(self):
        """Testing Site.generate_settings_local with Postgres"""
        site = Site(install_dir=self.sitedir1,
                    options={})
        site.domain_name = 'reviews.example.com'
        site.db_type = 'postgresql'
        site.db_name = 'test-database'
        site.db_user = 'test-user'
        site.db_pass = 'test-pass'
        site.db_host = 'db.example.com'
        site.db_port = 12345
        site.cache_info = 'localhost:1666'
        site.cache_type = 'memcached'
        site.secret_key = \
            'acdef12345acdef123456abcdef123456abcdef12345abcdef12345'

        site.generate_settings_local()

        self._check_settings_local(
            self.sitedir1,
            'DATABASES = {\n'
            '    "default": {\n'
            '        "ENGINE": "django.db.backends.postgresql",\n'
            '        "NAME": "test-database",\n'
            '        "USER": "test-user",\n'
            '        "PASSWORD": "test-pass",\n'
            '        "HOST": "db.example.com",\n'
            '        "PORT": 12345\n'
            '    }\n'
            '}\n'
            'CACHES = {\n'
            '    "default": {\n'
            '        "BACKEND": "django.core.cache.backends.memcached'
            '.MemcachedCache",\n'
            '        "LOCATION": "localhost:1666"\n'
            '    }\n'
            '}\n'
            'SECRET_KEY = "acdef12345acdef123456abcdef123456abcdef12345'
            'abcdef12345"\n'
            'SITE_ROOT = ""\n'
            'DEBUG = False\n'
            'ALLOWED_HOSTS = [\n'
            '    "reviews.example.com"\n'
            ']\n')

    def test_generate_settings_local_with_sqlite(self):
        """Testing Site.generate_settings_local with SQLite"""
        site = Site(install_dir=self.sitedir1,
                    options={})
        site.domain_name = 'reviews.example.com'
        site.db_type = 'sqlite3'
        site.db_name = '/path/to/reviewboard.db'
        site.cache_info = 'localhost:1666'
        site.cache_type = 'memcached'
        site.secret_key = \
            'acdef12345acdef123456abcdef123456abcdef12345abcdef12345'

        site.generate_settings_local()

        self._check_settings_local(
            self.sitedir1,
            'DATABASES = {\n'
            '    "default": {\n'
            '        "ENGINE": "django.db.backends.sqlite3",\n'
            '        "NAME": "/path/to/reviewboard.db"\n'
            '    }\n'
            '}\n'
            'CACHES = {\n'
            '    "default": {\n'
            '        "BACKEND": "django.core.cache.backends.memcached'
            '.MemcachedCache",\n'
            '        "LOCATION": "localhost:1666"\n'
            '    }\n'
            '}\n'
            'SECRET_KEY = "acdef12345acdef123456abcdef123456abcdef12345'
            'abcdef12345"\n'
            'SITE_ROOT = ""\n'
            'DEBUG = False\n'
            'ALLOWED_HOSTS = [\n'
            '    "reviews.example.com"\n'
            ']\n')

    def test_get_settings_upgrade_needed_with_legacy_database(self):
        """Testing Site.get_settings_upgrade_needed with legacy
        DATABASE_* settings
        """
        self.assertTrue(self._get_settings_upgrade_needed({
            'CACHES': {
                'default': {
                    'BACKEND': ('django.core.cache.backends.memcached.'
                                'MemcachedCache'),
                    'LOCATION': 'localhost:1666',
                },
            },
            'DATABASE_ENGINE': 'mysql',
        }))

    def test_get_settings_upgrade_needed_with_legacy_cache_backend(self):
        """Testing Site.get_settings_upgrade_needed with legacy
        CACHE_BACKEND setting
        """
        self.assertTrue(self._get_settings_upgrade_needed({
            'CACHE_BACKEND': 'memcached://localhost:1666',
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.mysql',
                },
            },
        }))

    def test_get_settings_upgrade_needed_with_legacy_database_engine(self):
        """Testing Site.get_settings_upgrade_needed with legacy database
        engine name
        """
        self.assertTrue(self._get_settings_upgrade_needed({
            'CACHES': {
                'default': {
                    'BACKEND': ('django.core.cache.backends.memcached.'
                                'MemcachedCache'),
                    'LOCATION': 'localhost:1666',
                },
            },
            'DATABASES': {
                'default': {
                    'ENGINE': 'mysql',
                },
            },
        }))

    def test_get_settings_upgrade_needed_with_legacy_postgresql_psycopg2(self):
        """Testing Site.get_settings_upgrade_needed with legacy
        postgresql_psycopg2 database engine
        """
        self.assertTrue(self._get_settings_upgrade_needed({
            'CACHES': {
                'default': {
                    'BACKEND': ('django.core.cache.backends.memcached.'
                                'MemcachedCache'),
                    'LOCATION': 'localhost:1666',
                },
            },
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql_psycopg2',
                },
            },
        }))

    def test_get_settings_upgrade_needed_with_modern_settings(self):
        """Testing Site.get_settings_upgrade_needed with modern settings"""
        self.assertFalse(self._get_settings_upgrade_needed({
            'CACHES': {
                'default': {
                    'BACKEND': ('django.core.cache.backends.memcached.'
                                'MemcachedCache'),
                    'LOCATION': 'localhost:1666',
                },
            },
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                },
            },
        }))

    def test_get_wsgi_upgrade_needed_with_rb_pre_4(self):
        """Testing Site.get_wsgi_upgrade_needed with pre-RB4 configuration"""
        self.assertTrue(self._get_wsgi_upgrade_needed(
            "import os\n"
            "import sys\n"
            "\n"
            "os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'\n"
            "os.environ['PYTHON_EGG_CACHE'] = '%(sitedir)s/tmp/egg_cache'\n"
            "os.environ['HOME'] = '%(sitedir)s/data'\n"
            "os.environ['CUSTOM'] = 'abc123'\n"
            "os.environ['PATH'] = '/usr/local/bin:%%s'"
            " %% os.environ['PATH']\n"
            "os.environ['PYTHONPATH'] = '%(sitedir)s/conf:%%s'"
            " %% os.environ['PYTHONPATH']\n"
            "\n"
            "sys.path = ['%(sitedir)s/conf'] + sys.path\n"
            "\n"
            "import django.core.handlers.wsgi\n"
            "application = django.core.handlers.wsgi.WSGIHandler()\n"))

    def test_get_wsgi_upgrade_needed_with_rb4_beta(self):
        """Testing Site.get_wsgi_upgrade_needed with RB4 beta configuration"""
        self.assertTrue(self._get_wsgi_upgrade_needed(
            "import os\n"
            "import sys\n"
            "\n"
            "os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'\n"
            "os.environ['PYTHON_EGG_CACHE'] = '%(sitedir)s/tmp/egg_cache'\n"
            "os.environ['HOME'] = '%(sitedir)s/data'\n"
            "os.environ['CUSTOM'] = 'abc123'\n"
            "os.environ['PATH'] = '/usr/local/bin:%%s'"
            " %% os.environ['PATH']\n"
            "os.environ['PYTHONPATH'] = '%(sitedir)s/conf:%%s'"
            " %% os.environ['PYTHONPATH']\n"
            "\n"
            "sys.path = ['%(sitedir)s/conf'] + sys.path\n"
            "\n"
            "from django.core.wsgi import get_wsgi_application\n"
            "application = get_wsgi_application()\n"))

    def test_get_wsgi_upgrade_needed_with_rb4(self):
        """Testing Site.get_wsgi_upgrade_needed with RB4+ configuration"""
        self.assertFalse(self._get_wsgi_upgrade_needed(
            "import os\n"
            "import sys\n"
            "\n"
            "os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'\n"
            "os.environ['PYTHON_EGG_CACHE'] = '%(sitedir)s/tmp/egg_cache'\n"
            "os.environ['HOME'] = '%(sitedir)s/data'\n"
            "os.environ['CUSTOM'] = 'abc123'\n"
            "os.environ['PATH'] = '/usr/local/bin:%%s'"
            " %% os.environ['PATH']\n"
            "os.environ['PYTHONPATH'] = '%(sitedir)s/conf:%%s'"
            " %% os.environ['PYTHONPATH']\n"
            "\n"
            "sys.path = ['%(sitedir)s/conf'] + sys.path\n"
            "\n"
            "from reviewboard.wsgi import application\n"))

    def test_upgrade_settings_with_legacy_database(self):
        """Testing Site.upgrade_settings with legacy DATABASE_* settings"""
        self._check_upgrade_settings(
            stored_settings={
                'CACHES': {
                    'default': {
                        'BACKEND': ('django.core.cache.backends.memcached.'
                                    'MemcachedCache'),
                        'LOCATION': 'localhost:1666',
                    },
                },
                'DATABASE_ENGINE': 'mysql',
                'DATABASE_NAME': 'test-database',
                'DATABASE_HOST': 'db.example.com',
                'DATABASE_PORT': 12345,
                'DATABASE_USER': 'test-user',
                'DATABASE_PASSWORD': 'test-pass',
            },
            stored_settings_text=(
                'DATABASE_ENGINE = "mysql"\n'
                'DATABASE_NAME = "test-database"\n'
                'DATABASE_HOST = "db.example.com"\n'
                'DATABASE_PORT = 12345\n'
                'DATABASE_USER = "test-user"\n'
                'DATABASE_PASSWORD = "test-pass"\n'
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
            ),
            expected_settings_text=(
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.mysql",\n'
                '        "NAME": "test-database",\n'
                '        "USER": "test-user",\n'
                '        "PASSWORD": "test-pass",\n'
                '        "HOST": "db.example.com",\n'
                '        "PORT": 12345\n'
                '    }\n'
                '}\n'
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
            ))

    def test_upgrade_settings_with_legacy_cache_backend(self):
        """Testing Site.upgrade_settings with legacy CACHE_BACKEND setting"""
        self._check_upgrade_settings(
            stored_settings={
                'CACHE_BACKEND': 'memcached://localhost:1666',
                'DATABASES': {
                    'default': {
                        'ENGINE': 'mysql',
                    },
                },
            },
            stored_settings_text=(
                'CACHE_BACKEND = "memcached://localhost:1666"\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.mysql",\n'
                '    },\n'
                '}\n'
            ),
            expected_settings_text=(
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666"\n'
                '    }\n'
                '}\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.mysql",\n'
                '    },\n'
                '}\n'
            ))

    def test_upgrade_settings_with_legacy_database_engine(self):
        """Testing Site.upgrade_settings with legacy database engine name"""
        self._check_upgrade_settings(
            stored_settings={
                'CACHES': {
                    'default': {
                        'BACKEND': ('django.core.cache.backends.memcached.'
                                    'MemcachedCache'),
                        'LOCATION': 'localhost:1666',
                    },
                },
                'DATABASES': {
                    'default': {
                        'ENGINE': 'mysql',
                    },
                },
            },
            stored_settings_text=(
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "mysql",\n'
                '    },\n'
                '}\n'
            ),
            expected_settings_text=(
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.mysql",\n'
                '    },\n'
                '}\n'
            ))

    def test_upgrade_settings_with_legacy_postgresql_psycopg2(self):
        """Testing Site.upgrade_settings with legacy postgresql_psycopg2
        database engine
        """
        self._check_upgrade_settings(
            stored_settings={
                'CACHES': {
                    'default': {
                        'BACKEND': ('django.core.cache.backends.memcached.'
                                    'MemcachedCache'),
                        'LOCATION': 'localhost:1666',
                    },
                },
                'DATABASES': {
                    'default': {
                        'ENGINE': 'django.db.backends.postgresql_psycopg2',
                    },
                },
            },
            stored_settings_text=(
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.postgresql_psycopg2",\n'
                '    },\n'
                '}\n'
            ),
            expected_settings_text=(
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.postgresql",\n'
                '    },\n'
                '}\n'
            ))

    def test_upgrade_settings_with_modern_settings(self):
        """Testing Site.upgrade_settings with modern settings"""
        self._check_upgrade_settings(
            stored_settings={
                'CACHES': {
                    'default': {
                        'BACKEND': ('django.core.cache.backends.memcached.'
                                    'MemcachedCache'),
                        'LOCATION': 'localhost:1666',
                    },
                },
                'DATABASES': {
                    'default': {
                        'ENGINE': 'django.db.backends.postgresql',
                    },
                },
            },
            stored_settings_text=(
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.postgresql",\n'
                '    },\n'
                '}\n'
            ),
            expected_settings_text=(
                'CACHES = {\n'
                '    "default": {\n'
                '        "BACKEND": "django.core.cache.backends.memcached.'
                'MemcachedCache",\n'
                '        "LOCATION": "localhost:1666",\n'
                '    },\n'
                '}\n'
                'DATABASES = {\n'
                '    "default": {\n'
                '        "ENGINE": "django.db.backends.postgresql",\n'
                '    },\n'
                '}\n'
            ))

    def test_upgrade_wsgi_with_rb_pre_4(self):
        """Testing Site.upgrade_wsgi with pre-RB4 configuration"""
        self._check_upgrade_wsgi(
            ("import os\n"
             "import sys\n"
             "\n"
             "os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'\n"
             "os.environ['PYTHON_EGG_CACHE'] = '%(sitedir)s/tmp/egg_cache'\n"
             "os.environ['HOME'] = '%(sitedir)s/data'\n"
             "os.environ['CUSTOM'] = 'abc123'\n"
             "os.environ['PATH'] = '/usr/local/bin:%%s'"
             " %% os.environ['PATH']\n"
             "os.environ['PYTHONPATH'] = '%(sitedir)s/conf:%%s'"
             " %% os.environ['PYTHONPATH']\n"
             "\n"
             "sys.path = ['%(sitedir)s/conf'] + sys.path\n"
             "\n"
             "import django.core.handlers.wsgi\n"
             "application = django.core.handlers.wsgi.WSGIHandler()\n"),
            ("import os\n"
             "import sys\n"
             "\n"
             "os.environ['CUSTOM'] = 'abc123'\n"
             "os.environ['PATH'] = '/usr/local/bin:%%s'"
             " %% os.environ['PATH']\n"
             "\n"
             "os.environ['REVIEWBOARD_SITEDIR'] = '%(sitedir)s'\n"
             "\n"
             "from reviewboard.wsgi import application\n"))

    def test_upgrade_wsgi_with_rb_4_beta(self):
        """Testing Site.upgrade_wsgi with RB4 beta configuration"""
        self._check_upgrade_wsgi(
            ("import os\n"
             "import sys\n"
             "\n"
             "os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'\n"
             "os.environ['PYTHON_EGG_CACHE'] = '%(sitedir)s/tmp/egg_cache'\n"
             "os.environ['HOME'] = '%(sitedir)s/data'\n"
             "os.environ['CUSTOM'] = 'abc123'\n"
             "os.environ['PATH'] = '/usr/local/bin:%%s'"
             " %% os.environ['PATH']\n"
             "os.environ['PYTHONPATH'] = '%(sitedir)s/conf:%%s'"
             " %% os.environ['PYTHONPATH']\n"
             "\n"
             "sys.path = ['%(sitedir)s/conf'] + sys.path\n"
             "\n"
             "from django.core.wsgi import get_wsgi_application\n"
             "application = get_wsgi_application()\n"),
            ("import os\n"
             "import sys\n"
             "\n"
             "os.environ['CUSTOM'] = 'abc123'\n"
             "os.environ['PATH'] = '/usr/local/bin:%%s'"
             " %% os.environ['PATH']\n"
             "\n"
             "os.environ['REVIEWBOARD_SITEDIR'] = '%(sitedir)s'\n"
             "\n"
             "from reviewboard.wsgi import application\n"))

    def test_upgrade_wsgi_with_custom_values(self):
        """Testing Site.upgrade_wsgi with custom setting values"""
        self._check_upgrade_wsgi(
            ("import os, sys\n"
             "\n"
             "os.environ['DJANGO_SETTINGS_MODULE'] = 'special.settings'\n"
             "os.environ['PYTHON_EGG_CACHE'] = '/tmp/egg_cache\n"
             "os.environ['HOME'] = '/root'\n"
             "os.environ['CUSTOM'] = 'abc123'\n"
             "os.environ['PATH'] = '/usr/local/bin:%%s'"
             " %% os.environ['PATH']\n"
             "os.environ['PYTHONPATH'] = '/app/python'\n"
             "\n"
             "import django.core.handlers.wsgi\n"
             "application = django.core.handlers.wsgi.WSGIHandler()\n"),
            ("import os, sys\n"
             "\n"
             "os.environ['CUSTOM'] = 'abc123'\n"
             "os.environ['PATH'] = '/usr/local/bin:%%s'"
             " %% os.environ['PATH']\n"
             "os.environ['PYTHONPATH'] = '/app/python'\n"
             "\n"
             "os.environ['REVIEWBOARD_SITEDIR'] = '%(sitedir)s'\n"
             "\n"
             "from reviewboard.wsgi import application\n"))

    def _get_settings_upgrade_needed(self, stored_settings):
        """Return Site.get_settings_upgrade_needed with the provided settings.

        Args:
            stored_settings (dict):
                A dictionary of settings that would be stored in
                :file:`settings_local.py`.

        Returns:
            bool:
            The result of :py:class:`~reviewboard.cmdline.rbsite.Site.
            get_settings_upgrade_needed`.
        """
        class SettingsLocal(object):
            pass

        for key, value in six.iteritems(stored_settings):
            setattr(SettingsLocal, key, value)

        site = Site(install_dir=self.sitedir2,
                    options={})
        self.spy_on(site.get_settings_local,
                    op=kgb.SpyOpReturn(SettingsLocal))

        return site.get_settings_upgrade_needed()

    def _get_wsgi_upgrade_needed(self, stored_wsgi_text):
        """Return Site.get_wsgi_upgrade_needed with the provided file.

        Args:
            stored_settings (dict):
                A dictionary of settings that would be stored in
                :file:`settings_local.py`.

        Returns:
            bool:
            The result of :py:class:`~reviewboard.cmdline.rbsite.Site.
            get_settings_upgrade_needed`.
        """
        sitedir = self.sitedir2
        site = Site(install_dir=sitedir,
                    options={})

        filename = os.path.join(site.abs_install_dir, 'htdocs',
                                'reviewboard.wsgi')

        with open(filename, 'w') as fp:
            fp.write(stored_wsgi_text % {
                'sitedir': sitedir,
            })

        return site.get_wsgi_upgrade_needed()

    def _check_upgrade_settings(self, stored_settings, stored_settings_text,
                                expected_settings_text):
        """Check that upgrading settings produces the expected results.

        Args:
            stored_settings (dict):
                A dictionary of settings that would be stored in
                :file:`settings_local.py`.

            stored_settings_text (unicode):
                The content of the :file:`settings_local.py` file to write
                and upgrade.

            expected_settings_text (unicode):
                The content of just the settings, without any blank lines
                or comments.

        Raises:
            AssertionError:
                An expectation failed.
        """
        class SettingsLocal(object):
            pass

        for key, value in six.iteritems(stored_settings):
            setattr(SettingsLocal, key, value)

        site = Site(install_dir=self.sitedir2,
                    options={})
        self.spy_on(site.get_settings_local,
                    op=kgb.SpyOpReturn(SettingsLocal))

        with open(os.path.join(site.abs_install_dir, 'conf',
                               'settings_local.py'),
                  'w') as fp:
            fp.write(stored_settings_text)

        site.upgrade_settings()

        self._check_settings_local(site.abs_install_dir,
                                   expected_settings_text)

    def _check_upgrade_wsgi(self, stored_wsgi_text, expected_wsgi_text):
        """Check that upgrading reviewboard.wsgi produces the expected results.

        Args:
            stored_wsgi_text (unicode):
                The contents of the :file:`htdocs/reviewboard.wsgi` file to
                write and upgrade.

            expected_wsgi_text (unicode):
                The expected content of the file.

        Raises:
            AssertionError:
                An expectation failed.
        """
        sitedir = self.sitedir2
        site = Site(install_dir=sitedir,
                    options={})

        filename = os.path.join(site.abs_install_dir, 'htdocs',
                                'reviewboard.wsgi')

        with open(filename, 'w') as fp:
            fp.write(stored_wsgi_text % {
                'sitedir': sitedir,
            })

        site.upgrade_wsgi()

        with open(filename, 'r') as fp:
            self.assertMultiLineEqual(
                fp.read(),
                expected_wsgi_text % {
                    'sitedir': sitedir,
                })

    def _check_settings_local(self, sitedir, expected_settings_text):
        """Check that a generated settings_local.py has the expected settings.

        This will verify the existence of the file in the site directory,
        strip away any comments or blank lines, and compare against the
        expected settings text.

        Args:
            sitedir (unicode):
                The path to the site directory.

            expected_settings_text (unicode):
                The content of just the settings, without any blank lines
                or comments.

        Raises:
            AssertionError:
                An expectation failed.
        """
        filename = os.path.join(sitedir, 'conf', 'settings_local.py')
        self.assertTrue(os.path.exists(filename))

        with open(filename, 'r') as fp:
            lines = fp.readlines()

        # Strip away all comments and blank lines.
        lines = [
            line
            for line in lines
            if line.strip() and not line.startswith('#')
        ]

        self.assertMultiLineEqual(''.join(lines), expected_settings_text)


class ValidateSitePathsTests(BaseRBSiteTestCase):
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
