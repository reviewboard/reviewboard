#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import getpass
import imp
import logging
import os
import pkg_resources
import platform
import re
import shutil
import sys
import textwrap
import subprocess
import warnings
from importlib import import_module
from optparse import OptionGroup, OptionParser
from random import choice as random_choice

from django.db.utils import OperationalError
from django.dispatch import receiver
from django.utils import six
from django.utils.encoding import force_str
from django.utils.six.moves import input
from django.utils.six.moves.urllib.request import urlopen

import reviewboard
from reviewboard import finalize_setup, get_manual_url, get_version_string
from reviewboard.admin.import_utils import has_module
from reviewboard.rb_platform import (SITELIST_FILE_UNIX,
                                     DEFAULT_FS_CACHE_PATH,
                                     INSTALLED_SITE_PATH)


# Ignore the PendingDeprecationWarnings that we'll get from Django.
# See bug 1683.
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)

# Ignore the same for cryptography for Python 2. They actually subclass from
# UserWarning to make sure it's always visible. We're going to hide that. We
# don't really want to show any UserWarnings anyway.
warnings.filterwarnings('ignore', category=UserWarning)


VERSION = get_version_string()
DEBUG = False


is_windows = (platform.system() == 'Windows')


# Global State
options = None
args = None
site = None
ui = None


SUPPORT_URL = 'https://www.reviewboard.org/support/'


class CommandError(Exception):
    """An error running a command."""


class MissingSiteError(CommandError):
    """An error indicating a site wasn't provided."""


class Dependencies(object):
    """An object which queries and caches dependency information."""

    memcached_modules = ["memcache"]
    sqlite_modules = ["pysqlite2", "sqlite3"]
    mysql_modules = ["MySQLdb"]
    postgresql_modules = ["psycopg2"]

    cache_dependency_info = {
        'required': False,
        'title': 'Server Cache',
        'dependencies': [
            ("memcached", memcached_modules),
        ],
    }

    db_dependency_info = {
        'required': True,
        'title': 'Databases',
        'dependencies': [
            ("sqlite3", sqlite_modules),
            ("MySQL", mysql_modules),
            ("PostgreSQL", postgresql_modules)
        ],
    }

    @classmethod
    def get_support_memcached(cls):
        """Return whether memcached is supported."""
        return cls.has_modules(cls.memcached_modules)

    @classmethod
    def get_support_mysql(cls):
        """Return whether mysql is supported."""
        return cls.has_modules(cls.mysql_modules)

    @classmethod
    def get_support_postgresql(cls):
        """Return whether postgresql is supported."""
        return cls.has_modules(cls.postgresql_modules)

    @classmethod
    def get_support_sqlite(cls):
        """Return whether sqlite is supported."""
        return cls.has_modules(cls.sqlite_modules)

    @classmethod
    def get_missing(cls):
        """Return any missing dependencies.

        This will return a two-tuple, where the first item is a boolean
        indicating if any missing dependencies are fatal, and the second is a
        list of missing dependency groups.
        """
        fatal = False
        missing_groups = []

        for dep_info in [cls.cache_dependency_info,
                         cls.db_dependency_info]:
            missing_deps = []

            for desc, modules in dep_info['dependencies']:
                if not cls.has_modules(modules):
                    missing_deps.append("%s (%s)" % (desc, ", ".join(modules)))

            if missing_deps:
                if (dep_info['required'] and
                        len(missing_deps) == len(dep_info['dependencies'])):
                    fatal = True
                    text = "%s (required)" % dep_info['title']
                else:
                    text = "%s (optional)" % dep_info['title']

                missing_groups.append({
                    'title': text,
                    'dependencies': missing_deps,
                })

        return fatal, missing_groups

    @classmethod
    def has_modules(cls, names):
        """Return True if one of the specified modules is installed."""
        for name in names:
            try:
                __import__(name)
                return True
            except ImportError:
                continue

        return False


class Site(object):
    """An object which contains the configuration for a Review Board site."""

    CACHE_BACKENDS = {
        'memcached': 'django.core.cache.backends.memcached.MemcachedCache',
        'file': 'django.core.cache.backends.filebased.FileBasedCache',
    }

    def __init__(self, install_dir, options):
        """Initialize the site."""
        self.install_dir = self.get_default_site_path(install_dir)
        self.abs_install_dir = os.path.abspath(self.install_dir)
        self.site_id = \
            os.path.basename(install_dir).replace(" ", "_").replace(".", "_")
        self.options = options

        # State saved during installation
        self.company = None
        self.domain_name = None
        self.web_server_port = None
        self.site_root = None
        self.static_url = None
        self.media_url = None
        self.db_type = None
        self.db_name = None
        self.db_host = None
        self.db_port = None
        self.db_user = None
        self.db_pass = None
        self.reenter_db_pass = None
        self.cache_type = None
        self.cache_info = None
        self.web_server_type = None
        self.python_loader = None
        self.admin_user = None
        self.admin_password = None
        self.reenter_admin_password = None
        self.send_support_usage_stats = True

    def get_default_site_path(self, install_dir):
        """Return the default site path."""
        if os.path.isabs(install_dir) or os.sep in install_dir:
            return install_dir

        return os.path.join(INSTALLED_SITE_PATH, install_dir)

    def rebuild_site_directory(self):
        """Rebuild the site hierarchy."""
        htdocs_dir = os.path.join(self.install_dir, "htdocs")
        errordocs_dir = os.path.join(htdocs_dir, 'errordocs')
        media_dir = os.path.join(htdocs_dir, "media")
        static_dir = os.path.join(htdocs_dir, "static")

        self.mkdir(self.install_dir)
        self.mkdir(os.path.join(self.install_dir, "logs"))
        self.mkdir(os.path.join(self.install_dir, "conf"))

        self.mkdir(os.path.join(self.install_dir, "tmp"))
        os.chmod(os.path.join(self.install_dir, "tmp"), 0o777)

        self.mkdir(os.path.join(self.install_dir, "data"))

        self.mkdir(htdocs_dir)
        self.mkdir(media_dir)
        self.mkdir(static_dir)

        uploaded_dir = os.path.join(media_dir, 'uploaded')

        self.mkdir(uploaded_dir)

        # Assuming this is an upgrade, the 'uploaded' directory should
        # already have the right permissions for writing, so use that as a
        # template for all the new directories.
        writable_st = os.stat(uploaded_dir)

        writable_dirs = [
            os.path.join(uploaded_dir, 'images'),
            os.path.join(uploaded_dir, 'files'),
            os.path.join(media_dir, 'ext'),
            os.path.join(static_dir, 'ext'),
        ]

        for writable_dir in writable_dirs:
            self.mkdir(writable_dir)

            try:
                if hasattr(os, 'chown'):
                    os.chown(writable_dir, writable_st.st_uid,
                             writable_st.st_gid)
            except OSError:
                # The user didn't have permission to change the ownership,
                # they'll have to do this manually later.
                pass

        # Process the error docs templates and add them where the web server
        # can get to them.
        if os.path.exists(errordocs_dir) and os.path.islink(errordocs_dir):
            # This is from an older install where errordocs was linked to
            # the versions shipped in the package.
            os.unlink(errordocs_dir)

        self.mkdir(errordocs_dir)
        self.process_template('cmdline/conf/errordocs/500.html.in',
                              os.path.join(errordocs_dir, '500.html'))

        self.link_pkg_dir("reviewboard",
                          "htdocs/static/lib",
                          os.path.join(static_dir, 'lib'))
        self.link_pkg_dir("reviewboard",
                          "htdocs/static/rb",
                          os.path.join(static_dir, 'rb'))
        self.link_pkg_dir("reviewboard",
                          "htdocs/static/admin",
                          os.path.join(static_dir, 'admin'))
        self.link_pkg_dir("djblets",
                          "htdocs/static/djblets",
                          os.path.join(static_dir, 'djblets'))

        # Remove any old media directories from old sites
        self.unlink_media_dir(os.path.join(media_dir, 'admin'))
        self.unlink_media_dir(os.path.join(media_dir, 'djblets'))
        self.unlink_media_dir(os.path.join(media_dir, 'rb'))

        # Generate .htaccess files that enable compression and
        # never expires various file types.
        common_htaccess = [
            '<IfModule mod_expires.c>',
            '  <FilesMatch "\.(jpg|gif|png|css|js|htc)">',
            '    ExpiresActive on',
            '    ExpiresDefault "access plus 1 year"',
            '  </FilesMatch>',
            '</IfModule>',
            '',
            '<IfModule mod_deflate.c>',
        ] + [
            '  AddOutputFilterByType DEFLATE %s' % mimetype
            for mimetype in [
                'text/html',
                'text/plain',
                'text/xml',
                'text/css',
                'text/javascript',
                'application/javascript',
                'application/x-javascript',
            ]
        ] + [
            '</IfModule>',
        ]

        static_htaccess = common_htaccess

        media_htaccess = common_htaccess + [
            '<IfModule mod_headers.c>',
            '  Header set Content-Disposition "attachment"',
            '</IfModule>',
        ]

        with open(os.path.join(static_dir, '.htaccess'), 'w') as fp:
            fp.write('\n'.join(static_htaccess))
            fp.write('\n')

        with open(os.path.join(media_dir, '.htaccess'), 'w') as fp:
            fp.write('\n'.join(media_htaccess))
            fp.write('\n')

    def setup_settings(self):
        """Set up the environment for running django management commands."""
        # Make sure that we have our settings_local.py in our path for when
        # we need to run manager commands.
        sys.path.insert(0, os.path.join(self.abs_install_dir, "conf"))
        os.environ[str('DJANGO_SETTINGS_MODULE')] = str('reviewboard.settings')

        import django
        django.setup()

    def get_apache_version(self):
        """Return the version of the installed apache."""
        try:
            apache_version = subprocess.check_output(['httpd', '-v'])
            # Extract the major and minor version from the string
            m = re.search('Apache\/(\d+).(\d+)', apache_version)
            if m:
                return m.group(1, 2)
            else:
                # Raise a generic regex error so we go to the
                # exception handler to pick a default
                raise re.error
        except:
            # Version check returned an error or the regular
            # expression did not match. Guess 2.2 for historic
            # compatibility
            return (2, 2)

    def generate_cron_files(self):
        """Generate sample crontab for this site."""
        self.process_template("cmdline/conf/cron.conf.in",
                              os.path.join(self.install_dir, "conf",
                                           "cron.conf"))

    def generate_config_files(self):
        """Generate the configuration files for this site."""
        web_conf_filename = ""
        enable_fastcgi = False
        enable_wsgi = False

        if self.web_server_type == "apache":
            if self.python_loader == "fastcgi":
                web_conf_filename = "apache-fastcgi.conf"
                enable_fastcgi = True
            elif self.python_loader == "wsgi":
                web_conf_filename = "apache-wsgi.conf"
                enable_wsgi = True
            else:
                # Should never be reached.
                assert False

            # Get the Apache version so we know which
            # authorization directive to use
            apache_version = self.get_apache_version()
            if apache_version[0] >= 2 and apache_version[1] >= 4:
                self.apache_auth = "Require all granted"
            else:
                self.apache_auth = "Allow from all"

        elif self.web_server_type == "lighttpd":
            web_conf_filename = "lighttpd.conf"
            enable_fastcgi = True
        else:
            # Should never be reached.
            assert False

        conf_dir = os.path.join(self.install_dir, "conf")
        htdocs_dir = os.path.join(self.install_dir, "htdocs")

        self.process_template("cmdline/conf/%s.in" % web_conf_filename,
                              os.path.join(conf_dir, web_conf_filename))
        self.generate_cron_files()
        if enable_fastcgi:
            fcgi_filename = os.path.join(htdocs_dir, "reviewboard.fcgi")
            self.process_template("cmdline/conf/reviewboard.fcgi.in",
                                  fcgi_filename)
            os.chmod(fcgi_filename, 0o755)
        elif enable_wsgi:
            wsgi_filename = os.path.join(htdocs_dir, "reviewboard.wsgi")
            self.process_template("cmdline/conf/reviewboard.wsgi.in",
                                  wsgi_filename)
            os.chmod(wsgi_filename, 0o755)

        # Generate a secret key based on Django's code.
        secret_key = ''.join([
            random_choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
            for i in range(50)
        ])

        # Generate the settings_local.py
        fp = open(os.path.join(conf_dir, "settings_local.py"), "w")
        fp.write("# Site-specific configuration settings for Review Board\n")
        fp.write("# Definitions of these settings can be found at\n")
        fp.write("# http://docs.djangoproject.com/en/dev/ref/settings/\n")
        fp.write("\n")
        fp.write("# Database configuration\n")

        db_engine = self.db_type
        if db_engine == "postgresql":
            db_engine = "postgresql_psycopg2"

        fp.write("DATABASES = {\n")
        fp.write("    'default': {\n")
        fp.write("        'ENGINE': 'django.db.backends.%s',\n" % db_engine)
        fp.write("        'NAME': '%s',\n"
                 % self.db_name.replace("\\", "\\\\"))

        if self.db_type != "sqlite3":
            if ':' in self.db_host:
                self.db_host, self.db_port = self.db_host.split(':', 1)

            fp.write("        'USER': '%s',\n" % (self.db_user or ""))
            fp.write("        'PASSWORD': '%s',\n" % (self.db_pass or ""))
            fp.write("        'HOST': '%s',\n" % (self.db_host or ""))
            fp.write("        'PORT': '%s',\n" % (self.db_port or ""))

        fp.write("    },\n")
        fp.write("}\n")

        fp.write("\n")
        fp.write("# Unique secret key. Don't share this with anybody.\n")
        fp.write("SECRET_KEY = '%s'\n" % secret_key)
        fp.write("\n")
        fp.write("# Cache backend settings.\n")
        fp.write("CACHES = {\n")
        fp.write("    'default': {\n")
        fp.write("        'BACKEND': '%s',\n" %
                 self.CACHE_BACKENDS[self.cache_type])
        fp.write("        'LOCATION': '%s',\n" % self.cache_info)
        fp.write("    },\n")
        fp.write("}\n")
        fp.write("\n")
        fp.write("# Extra site information.\n")
        fp.write("SITE_ID = 1\n")
        fp.write("SITE_ROOT = '%s'\n" % self.site_root)
        fp.write("FORCE_SCRIPT_NAME = ''\n")
        fp.write("DEBUG = False\n")
        fp.write("ALLOWED_HOSTS = ['%s']\n" % (self.domain_name or '*'))
        fp.close()

        self.setup_settings()

    def update_database(self, allow_input=False, report_progress=False):
        """Update the database.

        This will create the database if needed, or update the schema
        (applying any evolutions or migrations) if upgrading an existing
        database.

        Args:
            allow_input (bool, optional):
                Whether the evolution process or management commands can
                prompt for input.

            report_progress (bool, optional):
                Whether to report progress on the operation.
        """
        # Note that we're importing here so that we can ensure any new
        # settings have already been applied prior to import by the caller.
        from django.db import connection
        from django_evolution.errors import EvolutionException
        from django_evolution.evolve import Evolver
        from django_evolution.signals import (applying_evolution,
                                              applying_migration,
                                              creating_models)
        from django_evolution.utils.apps import import_management_modules

        import_management_modules()

        # Check that the database exists and can be accessed.
        while True:
            try:
                connection.ensure_connection()
                break
            except OperationalError as e:
                ui.error('There was an error connecting to the database. '
                         'Make sure the database exists and can be accessed '
                         'by the configured user and password, then continue.'
                         '\n'
                         'Details: %s'
                         % e,
                         force_wait=True)

        # Prepare the evolver and queue up all Review Board apps so we can
        # start running tests and ensuring everything is ready.
        evolver = Evolver(interactive=allow_input,
                          verbosity=1)
        evolver.queue_evolve_all_apps()

        # Make sure that the stored evolutions and migrations will properly
        # upgrade the database.
        diff = evolver.diff_evolutions()

        if not diff.is_empty(ignore_apps=True):
            ui.error(
                'Review Board cannot update your database. There is a '
                'discrepency between the state of your database and what '
                'Review Board expects.'
                '\n'
                'This could be caused by manual changes to your database '
                'schema, corruption, an incomplete uprade, or missing '
                'database upgrade history (stored in the '
                'django_project_version, django_evolution, and '
                'django_migrations tables).'
                '\n'
                'This may require manual repair. Please check our support '
                'options at %(support_url)s'
                % {
                    'support_url': SUPPORT_URL,
                },
                done_func=lambda: sys.exit(1))

        if not evolver.get_evolution_required():
            if report_progress:
                print('No database upgrade is required.')

            return

        # We're all set up to perform the evolution.
        @receiver(applying_evolution, sender=evolver)
        def _on_applying_evolution(task, **kwargs):
            if report_progress:
                print('  Applying database evolution for %s...'
                      % task.app_label)

        @receiver(applying_migration, sender=evolver)
        def _on_applying_migration(migration, **kwargs):
            if report_progress:
                print('  Applying database migration %s for %s...'
                      % (migration.name, migration.app_label))

        @receiver(creating_models, sender=evolver)
        def _on_creating_models(app_label, model_names, **kwargs):
            if report_progress:
                print('  Creating new database models for %s...' % app_label)

        # Begin the evolution process.
        if report_progress:
            print('* Updating database. This may take a while.')
            print()

        try:
            evolver.evolve()
        except EvolutionException as e:
            ui.error('There was an error updating the database. '
                     'Make sure the database is created and has the '
                     'appropriate permissions, and then continue.'
                     '\n'
                     'Details: %s'
                     % e,
                     force_wait=True,
                     done_func=lambda: sys.exit(1))
            return

        finalize_setup(is_upgrade=True)

    def harden_passwords(self):
        """Harden any password storage.

        Any legacy plain-text passwords will be encrypted, and any
        repositories with stored credentials that are also associated with
        a hosting service will have those credentials removed.
        """
        from reviewboard.scmtools.models import Repository

        # Due to a bug in Review Board 2.0.x < 2.0.25 and 2.5.x < 2.5.7,
        # the browser could end up filling in the hidden "password" field
        # on repositories that were set up to use a hosting service. For
        # these, we want to make sure those credentials are safely removed.
        repositories = (
            Repository.objects
            .filter(hosting_account__isnull=False)
            .exclude(username='', encrypted_password='')
        )
        repositories.update(username='', encrypted_password='')

        # Any remaining passwords should be encrypted (if coming from an older
        # version before encryption was added).
        Repository.objects.encrypt_plain_text_passwords()

    def get_static_media_upgrade_needed(self):
        """Determine if a static media config upgrade is needed."""
        from djblets.siteconfig.models import SiteConfiguration

        siteconfig = SiteConfiguration.objects.get_current()
        manual_updates = siteconfig.settings.get('manual-updates', {})
        resolved_update = manual_updates.get('static-media', False)

        return (not resolved_update and
                (pkg_resources.parse_version(siteconfig.version) <
                 pkg_resources.parse_version("1.7")))

    def get_diff_dedup_needed(self):
        """Determine if there's likely duplicate diff data stored."""
        from reviewboard.diffviewer.models import FileDiff

        try:
            return FileDiff.objects.unmigrated().exists()
        except:
            # Very likely, there was no diffviewer_filediff.diff_hash_id
            # column, indicating a pre-1.7 database. We want to assume
            # a dedup is needed.
            return True

    def get_settings_upgrade_needed(self):
        """Determine if a settings upgrade is needed."""
        try:
            import settings_local

            if (hasattr(settings_local, 'DATABASE_ENGINE') or
                    hasattr(settings_local, 'CACHE_BACKEND')):
                return True

            if hasattr(settings_local, 'DATABASES'):
                engine = settings_local.DATABASES['default']['ENGINE']

                if not engine.startswith('django.db.backends'):
                    return True
        except ImportError:
            sys.stderr.write("Unable to import settings_local. "
                             "Cannot determine if upgrade is needed.\n")

        return False

    def get_wsgi_upgrade_needed(self):
        """Return whether a reviewboard.wsgi upgrade is needed.

        Returns:
            bool:
            ``True`` if the :file:`reviewboard.wsgi` file needs to be upgraded.
            ``False`` if it does not.
        """
        filename = os.path.join(self.abs_install_dir, 'htdocs',
                                'reviewboard.wsgi')

        with open(filename, 'r') as fp:
            data = fp.read()

        return 'django.core.handlers.wsgi.WSGIHandler' in data

    def upgrade_settings(self):
        """Perform a settings upgrade."""
        settings_file = os.path.join(self.abs_install_dir, "conf",
                                     "settings_local.py")
        perform_upgrade = False
        buf = []
        database_info = {}
        database_keys = ('ENGINE', 'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT')
        backend_info = {}

        from django.core.cache import InvalidCacheBackendError
        from djblets.util.compat.django.core.cache import parse_backend_uri

        try:
            import settings_local

            if hasattr(settings_local, 'DATABASE_ENGINE'):
                engine = settings_local.DATABASE_ENGINE

                # Don't convert anything other than the ones we know about,
                # or third parties with custom databases may have problems.
                if engine in ('sqlite3', 'mysql', 'postgresql',
                              'postgresql_psycopg2'):
                    engine = 'django.db.backends.' + engine

                database_info['ENGINE'] = engine

                for key in database_keys:
                    if key != 'ENGINE':
                        database_info[key] = getattr(settings_local,
                                                     'DATABASE_%s' % key, '')

                perform_upgrade = True

            if hasattr(settings_local, 'DATABASES'):
                engine = settings_local.DATABASES['default']['ENGINE']

                if engine == 'postgresql_psycopg2':
                    perform_upgrade = True

            if hasattr(settings_local, 'CACHE_BACKEND'):
                try:
                    backend_info = parse_backend_uri(
                        settings_local.CACHE_BACKEND)
                    perform_upgrade = True
                except InvalidCacheBackendError:
                    pass
        except ImportError:
            sys.stderr.write("Unable to import settings_local for upgrade.\n")
            return

        if not perform_upgrade:
            return

        fp = open(settings_file, 'r')

        found_database = False
        found_cache = False

        for line in fp.readlines():
            if line.startswith('DATABASE_'):
                if not found_database:
                    found_database = True

                    buf.append("DATABASES = {\n")
                    buf.append("    'default': {\n")

                    for key in database_keys:
                        if database_info[key]:
                            buf.append("        '%s': '%s',\n" %
                                       (key, database_info[key]))

                    buf.append("    },\n")
                    buf.append("}\n")
            elif line.startswith('CACHE_BACKEND') and backend_info:
                if not found_cache:
                    found_cache = True

                    buf.append("CACHES = {\n")
                    buf.append("    'default': {\n")
                    buf.append("        'BACKEND': '%s',\n"
                               % self.CACHE_BACKENDS[backend_info[0]])
                    buf.append("        'LOCATION': '%s',\n" % backend_info[1])
                    buf.append("    },\n")
                    buf.append("}\n")
            elif line.strip().startswith("'ENGINE': 'postgresql_psycopg2'"):
                buf.append("        'ENGINE': '"
                           "django.db.backends.postgresql_psycopg2',\n")
            else:
                buf.append(line)

        fp.close()

        fp = open(settings_file, 'w')
        fp.writelines(buf)
        fp.close()

        # Reload the settings module
        del sys.modules['settings_local']
        del sys.modules['reviewboard.settings']
        import django.conf
        django.conf.settings = django.conf.LazySettings()

    def upgrade_wsgi(self):
        """Upgrade the reviewboard.wsgi file.

        This will modify :file:`reviewboard.wsgi` to replace any old
        WSGI initialization logic with modern logic.
        """
        filename = os.path.join(self.abs_install_dir, 'htdocs',
                                'reviewboard.wsgi')

        with open(filename, 'r') as fp:
            data = fp.read()

        data = data.replace(
            'import django.core.handlers.wsgi',
            'from django.core.wsgi import get_wsgi_application')
        data = data.replace(
            'application = django.core.handlers.wsgi.WSGIHandler()',
            'application = get_wsgi_application()')

        with open(filename, 'w') as fp:
            fp.write(data)

    def create_admin_user(self):
        """Create an administrator user account."""
        from django.contrib.auth.models import User

        if not User.objects.filter(username=self.admin_user).exists():
            cwd = os.getcwd()
            os.chdir(self.abs_install_dir)

            User.objects.create_superuser(self.admin_user, self.admin_email,
                                          self.admin_password)

            os.chdir(cwd)

    def register_support_page(self):
        """Register this installation with the support data tracker."""
        from reviewboard.admin.support import get_register_support_url

        url = get_register_support_url(force_is_admin=True)

        try:
            urlopen(url, timeout=5).read()
        except:
            # There may be a number of issues preventing this from working,
            # such as a restricted network environment or a server issue on
            # our side. This isn't a catastrophic issue, so don't bother them
            # about it.
            pass

    def run_manage_command(self, cmd, params=None):
        """Run a given django management command."""
        cwd = os.getcwd()
        os.chdir(self.abs_install_dir)

        try:
            from django.core.management import (BaseCommand,
                                                ManagementUtility,
                                                get_commands)

            os.environ.setdefault(str('DJANGO_SETTINGS_MODULE'),
                                  str('reviewboard.settings'))

            if not params:
                params = []

            if DEBUG:
                params.append('--verbosity=0')

            # This is a terrible hack, but it doesn't seem we have a great
            # way of disabling Django's system checks otherwise.
            #
            # It's possible for commands to opt out of doing system checks
            # (which we have no control over here), or to skip them when
            # invoking the command (but not when executing through an argv
            # approach). We'd also have the problem of commands calling other
            # commands and re-invoking the checks.
            #
            # Given that, we're opting to monkey patch.
            if has_module('django.core.checks'):
                BaseCommand.check = lambda *args, **kwargs: None

            usage_prefix = 'rb-site manage %s' % self.abs_install_dir

            # Patch the help output of the subcommand to show the actual
            # command used to run it in the usage information.
            def _create_parser(_self, prog_name, subcommand):
                parser = real_create_parser(_self, prog_name, subcommand)
                parser.prog = parser.prog.replace('rb-site-manage',
                                                  usage_prefix)

                return parser

            real_create_parser = BaseCommand.create_parser
            BaseCommand.create_parser = _create_parser

            commands_dir = os.path.join(self.abs_install_dir, 'commands')

            if os.path.exists(commands_dir):
                # Pre-fetch all the available management commands.
                get_commands()

                # Insert our own management commands into this list.
                # Yes, this is a bit of a hack.
                from django.core.management import _commands

                for command in os.listdir(commands_dir):
                    module_globals = {}
                    filename = os.path.join(commands_dir, command)
                    with open(filename) as f:
                        code = compile(f.read(), filename, 'exec')
                        exec(code, module_globals)

                    if 'Command' in module_globals:
                        name = os.path.splitext(f)[0]
                        _commands[name] = module_globals['Command']()

            manage_util = ManagementUtility(
                argv=['rb-site-manage', cmd] + params)
            manage_util.prog_name = usage_prefix
            manage_util.execute()
        except ImportError as e:
            ui.error("Unable to execute the manager command %s: %s" %
                     (cmd, e))

        os.chdir(cwd)

    def mkdir(self, dirname):
        """Create a directory, but only if it doesn't already exist."""
        if not os.path.exists(dirname):
            os.mkdir(dirname)

    def link_pkg_dir(self, pkgname, src_path, dest_dir, replace=True):
        """Create the package directory."""
        src_dir = pkg_resources.resource_filename(pkgname, src_path)

        if os.path.islink(dest_dir) and not os.path.exists(dest_dir):
            os.unlink(dest_dir)

        if os.path.exists(dest_dir):
            if not replace:
                return

            self.unlink_media_dir(dest_dir)

        if self.options.copy_media:
            shutil.copytree(src_dir, dest_dir)
        else:
            os.symlink(src_dir, dest_dir)

    def unlink_media_dir(self, path):
        """Delete the given media directory and all contents."""
        if os.path.exists(path):
            if os.path.islink(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)

    def process_template(self, template_path, dest_filename):
        """Generate a file from a template."""
        domain_name = self.domain_name or ''
        domain_name_escaped = domain_name.replace(".", "\\.")
        template = (
            pkg_resources.resource_string('reviewboard', template_path)
            .decode('utf-8')
        )
        sitedir = os.path.abspath(self.install_dir).replace("\\", "/")

        if self.site_root:
            site_root = self.site_root
            site_root_noslash = site_root[1:-1]
        else:
            site_root = '/'
            site_root_noslash = ''

        # Check if this is a .exe.
        if (hasattr(sys, "frozen") or         # new py2exe
                hasattr(sys, "importers") or  # new py2exe
                imp.is_frozen("__main__")):   # tools/freeze
            rbsite_path = sys.executable
        else:
            rbsite_path = '"%s" "%s"' % (sys.executable, sys.argv[0])

        data = {
            'rbsite': rbsite_path,
            'port': self.web_server_port,
            'sitedir': sitedir,
            'sitedomain': domain_name,
            'sitedomain_escaped': domain_name_escaped,
            'siteid': self.site_id,
            'siteroot': site_root,
            'siteroot_noslash': site_root_noslash,
        }

        if hasattr(self, 'apache_auth'):
            data['apache_auth'] = self.apache_auth

        template = re.sub(r"@([a-z_]+)@", lambda m: data.get(m.group(1)),
                          template)

        with open(dest_filename, 'w') as fp:
            fp.write(template)


class SiteList(object):
    """Maintains the list of sites installed on the system."""

    def __init__(self, path):
        """Initialize the site list."""
        self.path = path

        # Read the list in as a unique set.
        # This way, we can easily eliminate duplicates.
        self.sites = set()

        if os.path.exists(self.path):
            with open(self.path, 'r') as fp:
                for site_path in fp.readlines():
                    site_path = site_path.strip()

                    # Verify that this path exists on the system
                    # And add it to the dictionary.
                    print(repr(site_path))
                    if os.path.exists(site_path):
                        self.sites.add(site_path)

    def add_site(self, site_path):
        """Add a site to the site list."""
        self.sites.add(site_path)

        # Write all of the sites back to the file.
        # Sort keys to ensure consistent order.
        ordered_sites = list(self.sites)
        ordered_sites.sort()

        # Create the parent directory of the site
        # if it doesn't already exist
        if not os.path.exists(os.path.dirname(self.path)):
            # Create the parent directory with read-write
            # permissions for user but read and execute
            # only for others.
            try:
                os.makedirs(os.path.dirname(self.path), 0o755)
            except:
                # We shouldn't consider this an abort-worthy error
                # We'll warn the user and just complete setup
                print("WARNING: Could not save site to sitelist %s" %
                      self.path)
                return

        with open(self.path, 'w') as f:
            for site in ordered_sites:
                f.write("%s\n" % site)


class UIToolkit(object):
    """An abstract class that forms the basis for all UI interaction.

    Subclasses can override this to provide new ways of representing the UI
    to the user.
    """

    def run(self):
        """Run the UI."""
        pass

    def page(self, text, allow_back=True, is_visible_func=None,
             on_show_func=None):
        """Add a new "page" to display to the user.

        Input and text are associated with this page and may be displayed
        immediately or later, depending on the toolkit.

        If is_visible_func is specified and returns False, this page will
        be skipped.
        """
        return None

    def prompt_input(self, page, prompt, default=None, password=False,
                     normalize_func=None, save_obj=None, save_var=None):
        """Prompt the user for some text. This may contain a default value."""
        raise NotImplementedError

    def prompt_choice(self, page, prompt, choices,
                      save_obj=None, save_var=None):
        """Prompt the user for an item amongst a list of choices."""
        raise NotImplementedError

    def text(self, page, text):
        """Display a block of text to the user."""
        raise NotImplementedError

    def disclaimer(self, page, text):
        """Display a block of disclaimer text to the user."""
        raise NotImplementedError

    def urllink(self, page, url):
        """Display a URL to the user."""
        raise NotImplementedError

    def itemized_list(self, page, title, items):
        """Display an itemized list."""
        raise NotImplementedError

    def step(self, page, text, func, step_num=None, total_steps=None):
        """Add a step of a multi-step operation.

        This will indicate when it's starting and when it's complete.

        If both ``step_num`` and ``total_steps`` are provided, some progress
        information will be shown.

        Args:
            page (object):
                The page handle.

            text (unicode):
                The step text to display.

            func (callable):
                The function to call to execute the step.

            step_num (int, optional):
                The 1-based step number.

            total_steps (int, optional):
                The total number of steps.
        """
        raise NotImplementedError

    def error(self, text, force_wait=False, done_func=None):
        """Display a block of error text to the user."""
        raise NotImplementedError


class ConsoleUI(UIToolkit):
    """A UI toolkit that simply prints to the console."""

    def __init__(self, allow_color=True):
        """Initialize the UI toolkit.

        Args:
            allow_color (bool, optional):
                Whether to allow color output in the UI.
        """
        super(UIToolkit, self).__init__()

        # Make color styling available, if Django determines the terminal
        # supports it.
        from django.utils import termcolors
        from django.core.management.color import color_style, no_style

        if allow_color:
            self.style = color_style()
            self.header_style = termcolors.make_style(fg='yellow',
                                                      bg='black',
                                                      opts=('bold',))
            self.header_sep_style = termcolors.make_style(fg='yellow',
                                                          bg='black')
            self.prompt_style = termcolors.make_style(opts=('bold',))
        else:
            self.style = no_style()

            def plain_style(text):
                return text

            self.header_style = plain_style
            self.header_sep_style = plain_style
            self.prompt_style = plain_style

        # Get the terminal width in order to best fit wrapped content.
        term_width = 70

        if hasattr(shutil, 'get_terminal_size'):
            try:
                term_width = shutil.get_terminal_size()[0]
            except OSError:
                pass

        header_padding = 2
        text_padding = 4

        self.term_width = term_width
        self.header_sep = '\u2014' * term_width

        header_indent_str = ' ' * header_padding
        self.header_wrapper = textwrap.TextWrapper(
            initial_indent=header_indent_str,
            subsequent_indent=header_indent_str,
            width=term_width - header_padding)

        text_indent_str = ' ' * text_padding
        self.text_wrapper = textwrap.TextWrapper(
            initial_indent=text_indent_str,
            subsequent_indent=text_indent_str,
            break_long_words=False,
            width=term_width - text_padding)

        self.error_wrapper = textwrap.TextWrapper(
            initial_indent=self.style.ERROR('[!] '),
            subsequent_indent='    ',
            break_long_words=False,
            width=term_width - text_padding)

    def page(self, text, allow_back=True, is_visible_func=None,
             on_show_func=None):
        """Add a new "page" to display to the user.

        In the console UI, we only care if we need to display or ask questions
        for this page. Our representation of a page in this case is simply
        a boolean value. If False, nothing associated with this page will
        be displayed to the user.
        """
        visible = not is_visible_func or is_visible_func()

        if not visible:
            return False

        if on_show_func:
            on_show_func()

        fmt_str = '%%-%ds' % self.term_width

        print()
        print()
        print(self.header_sep_style(self.header_sep))
        print(self.header_style(fmt_str % self.header_wrapper.fill(text)))
        print(self.header_sep_style(self.header_sep))

        return True

    def prompt_input(self, page, prompt, default=None, password=False,
                     yes_no=False, optional=False, normalize_func=None,
                     save_obj=None, save_var=None):
        """Prompt the user for some text. This may contain a default value."""
        assert save_obj
        assert save_var

        if not page:
            return

        if yes_no:
            if default:
                prompt = '%s [Y/n]' % prompt
            else:
                prompt = '%s [y/N]' % prompt
                default = False
        elif default:
            self.text(page, "The default is %s" % default)
            prompt = "%s [%s]" % (prompt, default)
        elif optional:
            prompt = '%s (optional)' % prompt

        print()

        prompt = self.prompt_style('%s: ' % prompt)
        value = None

        while not value:
            if password:
                temp_value = getpass.getpass(force_str(prompt))
                if save_var.startswith('reenter'):
                    if not self.confirm_reentry(save_obj, save_var,
                                                temp_value):
                        self.error("Passwords must match.")
                        continue
                value = temp_value
            else:
                value = input(prompt)

            if not value:
                if default:
                    value = default
                elif optional:
                    break

            if yes_no:
                if isinstance(value, bool):
                    # This came from the 'default' value.
                    norm_value = value
                else:
                    assert isinstance(value, six.string_types)
                    norm_value = value.lower()

                if norm_value not in (True, False, 'y', 'n', 'yes', 'no'):
                    self.error('Must specify one of Y/y/yes or N/n/no.')
                    value = None
                    continue
                else:
                    value = norm_value in (True, 'y', 'yes')
                    break
            elif not value:
                self.error("You must answer this question.")

        if normalize_func:
            value = normalize_func(value)

        setattr(save_obj, save_var, value)

    def confirm_reentry(self, obj, reenter_var, value):
        """Confirm whether a re-entered piece of data matches.

        This is used to ensure that secrets and passwords are what the user
        intended to type.
        """
        first_var = reenter_var.replace('reenter_', '')
        first_entry = getattr(obj, first_var)
        return first_entry == value

    def prompt_choice(self, page, prompt, choices,
                      save_obj=None, save_var=None):
        """Prompt the user for an item amongst a list of choices."""
        assert save_obj
        assert save_var

        if not page:
            return

        self.text(page, "You can type either the name or the number "
                        "from the list below.")

        prompt_style = self.prompt_style
        valid_choices = []
        i = 0

        for choice in choices:
            description = ''
            enabled = True

            if isinstance(choice, six.string_types):
                text = choice
            elif len(choice) == 2:
                text, enabled = choice
            else:
                text, description, enabled = choice

            if enabled:
                self.text(page,
                          '%s %s %s\n' % (prompt_style('(%d)' % (i + 1)),
                                          text, description),
                          leading_newline=(i == 0))
                valid_choices.append(text)
                i += 1

        print()

        prompt = self.prompt_style('%s: ' % prompt)
        choice = None

        while not choice:
            choice = input(prompt)

            if choice not in valid_choices:
                try:
                    i = int(choice) - 1
                    if 0 <= i < len(valid_choices):
                        choice = valid_choices[i]
                        break
                except ValueError:
                    pass

                self.error("'%s' is not a valid option." % choice)
                choice = None

        setattr(save_obj, save_var, choice)

    def text(self, page, text, leading_newline=True, wrap=True):
        """Display a block of text to the user.

        This will wrap the block to fit on the user's screen.
        """
        if not page:
            return

        if leading_newline:
            print()

        if wrap:
            print(self.text_wrapper.fill(text))
        else:
            print('    %s' % text)

    def disclaimer(self, page, text):
        """Display a disclaimer to the user."""
        self.text(page, '%s: %s' % (self.style.WARNING('NOTE'), text))

    def urllink(self, page, url):
        """Display a URL to the user."""
        self.text(page, url, wrap=False)

    def itemized_list(self, page, title, items):
        """Display an itemized list."""
        if title:
            self.text(page, "%s:" % title)

        for item in items:
            self.text(page, "    * %s" % item, False)

    def step(self, page, text, func, step_num=None, total_steps=None):
        """Add a step of a multi-step operation.

        This will indicate when it's starting and when it's complete.

        If both ``step_num`` and ``total_steps`` are provided, the step
        text will include a prefix showing what step it's on and how many
        there are total.

        Args:
            page (object):
                The page handle.

            text (unicode):
                The step text to display.

            func (callable):
                The function to call to execute the step.

            step_num (int, optional):
                The 1-based step number.

            total_steps (int, optional):
                The total number of steps.
        """
        if step_num is not None and total_steps is not None:
            text = '[%s/%s] %s' % (step_num, total_steps, text)

        sys.stdout.write('%s ... ' % text)
        func()
        print(self.style.SUCCESS('OK'))

    def error(self, text, force_wait=False, done_func=None):
        """Display a block of error text to the user."""
        print()

        for text_block in text.split('\n'):
            print(self.error_wrapper.fill(text_block))

        if force_wait:
            print()
            input('Press Enter to continue')

        if done_func:
            done_func()


class Command(object):
    """An abstract command."""

    needs_ui = False

    #: Whether the site paths passed to the command must exist.
    require_site_paths_exist = True

    def add_options(self, parser):
        """Add any command-specific options to the parser."""
        pass

    def get_site_paths(self, options):
        """Return site paths defined in the command options.

        Args:
            options (argparse.Namespace):
                The parsed options for the command.

        Returns:
            list of unicode:
            The list of site paths.
        """
        if not options.site_path:
            return []

        site_paths = options.site_path

        # When site_path is optional (due to UpgradeCommand), it will be
        # a list. Otherwise, it will be a string.
        if not isinstance(site_paths, list):
            site_paths = [site_paths]

        return site_paths

    def run(self):
        """Run the command."""
        pass


class InstallCommand(Command):
    """Installer command.

    This command installs a new Review Board site tree and generates web server
    configuration files. This will ask several questions about the site before
    performing the installation.
    """

    needs_ui = True
    require_site_paths_exist = False

    def add_options(self, parser):
        """Add any command-specific options to the parser."""
        group = OptionGroup(parser, "'install' command",
                            self.__doc__.strip())
        group.add_option('--advanced', action='store_true',
                         dest='advanced',
                         default=False,
                         help='provide more advanced configuration options')
        group.add_option("--copy-media", action="store_true",
                         dest="copy_media",
                         default=is_windows,
                         help="copy media files instead of symlinking")

        group.add_option('--no-color',
                         action='store_false',
                         dest='allow_term_color',
                         default=True,
                         help='disable color output in the terminal')
        group.add_option("--noinput", action="store_true", default=False,
                         help="run non-interactively using configuration "
                              "provided in command-line options")
        group.add_option('--opt-out-support-data',
                         action='store_false',
                         default=True,
                         dest='send_support_usage_stats',
                         help='opt out of sending data and stats for '
                              'improved user and admin support')
        group.add_option("--company",
                         help="the name of the company or organization that "
                              "owns the server")
        group.add_option("--domain-name",
                         help="fully-qualified host name of the site, "
                         "excluding the http://, port or path")
        group.add_option("--site-root", default="/",
                         help="path to the site relative to the domain name")
        group.add_option("--static-url", default="static/",
                         help="the URL containing the static (shipped) "
                              "media files")
        group.add_option("--media-url", default="media/",
                         help="the URL containing the uploaded media files")
        group.add_option("--db-type",
                         help="database type (mysql, postgresql or sqlite3)")
        group.add_option("--db-name", default="reviewboard",
                         help="database name (not for sqlite3)")
        group.add_option("--db-host", default="localhost",
                         help="database host (not for sqlite3)")
        group.add_option("--db-user",
                         help="database user (not for sqlite3)")
        group.add_option("--db-pass",
                         help="password for the database user "
                              "(not for sqlite3)")
        group.add_option("--cache-type",
                         default='memcached',
                         help="cache server type (memcached or file)")
        group.add_option("--cache-info",
                         default='localhost:11211',
                         help="cache identifier (memcached connection string "
                              "or file cache directory)")
        group.add_option("--web-server-type",
                         default='apache',
                         help="web server (apache or lighttpd)")
        group.add_option("--web-server-port",
                         help="port that the web server should listen on",
                         default='80')
        group.add_option("--python-loader",
                         default='wsgi',
                         help="python loader for apache (fastcgi or wsgi)")
        group.add_option("--admin-user", default="admin",
                         help="the site administrator's username")
        group.add_option("--admin-password",
                         help="the site administrator's password")
        group.add_option("--admin-email",
                         help="the site administrator's e-mail address")

        if not is_windows:
            group.add_option('--sitelist',
                             default=SITELIST_FILE_UNIX,
                             help='the path to a file storing a list of '
                                  'installed sites')

        parser.add_option_group(group)

    def run(self):
        """Run the command."""
        if not self.check_permissions():
            return

        site.__dict__.update(options.__dict__)

        self.print_introduction()

        if self.print_missing_dependencies():
            # There were required dependencies missing. Don't show any more
            # pages.
            return

        if not options.noinput:
            self.ask_domain()
            self.ask_site_root()

            if options.advanced:
                self.ask_shipped_media_url()
                self.ask_uploaded_media_url()

            self.ask_database_type()
            self.ask_database_name()
            self.ask_database_host()
            self.ask_database_login()

            if options.advanced:
                self.ask_cache_type()

            self.ask_cache_info()

            if options.advanced:
                self.ask_web_server_type()
                self.ask_python_loader()

            self.ask_admin_user()
            self.ask_support_data()

            # Do not ask for sitelist file, it should not be common.

        self.show_install_status()
        self.show_finished()
        self.show_get_more()

    def normalize_root_url_path(self, path):
        """Convert user-specified root URL paths to a normal format."""
        if not path.endswith("/"):
            path += "/"

        if not path.startswith("/"):
            path = "/" + path

        return path

    def normalize_media_url_path(self, path):
        """Convert user-specified media URLs to a normal format."""
        if not path.endswith("/"):
            path += "/"

        if path.startswith("/"):
            path = path[1:]

        return path

    def check_permissions(self):
        """Check that permissions are usable.

        If not, this will show an error to the user.
        """
        # Make sure we can create the directory first.
        try:
            # TODO: Do some chown tests too.

            if os.path.exists(site.install_dir):
                # Remove it first, to see if we own it and to handle the
                # case where the directory is empty as a result of a
                # previously canceled install.
                os.rmdir(site.install_dir)

            os.mkdir(site.install_dir)

            # Don't leave a mess. We'll actually do this at the end.
            os.rmdir(site.install_dir)
            return True
        except OSError:
            # Likely a permission error.
            ui.error("Unable to create the %s directory. Make sure "
                     "you're running as an administrator and that the "
                     "directory does not contain any files."
                     % site.install_dir,
                     done_func=lambda: sys.exit(1))
            return False

    def print_introduction(self):
        """Print an introduction to the site installer."""
        page = ui.page("Welcome to the Review Board site installation wizard")

        ui.text(page, "This will prepare a Review Board site installation in:")
        ui.text(page, site.abs_install_dir)
        ui.text(page, "We need to know a few things before we can prepare "
                      "your site for installation. This will only take a few "
                      "minutes.")

    def print_missing_dependencies(self):
        """Print information on any missing dependencies."""
        fatal, missing_dep_groups = Dependencies.get_missing()

        if missing_dep_groups:
            if fatal:
                page = ui.page("Required modules are missing")
                ui.text(page, "You are missing Python modules that are "
                              "needed before the installation process. "
                              "You will need to install the necessary "
                              "modules and restart the install.")
            else:
                page = ui.page("Make sure you have the modules you need")
                ui.text(page, "Depending on your installation, you may need "
                              "certain Python modules and servers that are "
                              "missing.")
                ui.text(page, "If you need support for any of the following, "
                              "you will need to install the necessary "
                              "modules and restart the install.")

            for group in missing_dep_groups:
                ui.itemized_list(page, group['title'], group['dependencies'])

        return fatal

    def ask_domain(self):
        """Ask the user what domain Review Board will be served from."""
        page = ui.page("What's the host name for this site?")

        ui.text(page, "This should be the fully-qualified host name without "
                      "the http://, port or path.")

        ui.prompt_input(page, "Domain Name", site.domain_name,
                        save_obj=site, save_var="domain_name")

    def ask_site_root(self):
        """Ask the user what site root they'd like."""
        page = ui.page("What URL path points to Review Board?")

        ui.text(page, "Typically, Review Board exists at the root of a URL. "
                      "For example, http://reviews.example.com/. In this "
                      "case, you would specify \"/\".")
        ui.text(page, "However, if you want to listen to, say, "
                      "http://example.com/reviews/, you can specify "
                      '"/reviews/".')
        ui.text(page, "Note that this is the path relative to the domain and "
                      "should not include the domain name.")

        ui.prompt_input(page, "Root Path", site.site_root,
                        normalize_func=self.normalize_root_url_path,
                        save_obj=site, save_var="site_root")

    def ask_shipped_media_url(self):
        """Ask the user the URL where shipped media files are served."""
        page = ui.page("What URL will point to the shipped media files?")

        ui.text(page, "While most installations distribute media files on "
                      "the same server as the rest of Review Board, some "
                      "custom installs may instead have a separate server "
                      "for this purpose.")
        ui.text(page, "If unsure, don't change the default.")

        ui.prompt_input(page, "Shipped Media URL", site.static_url,
                        normalize_func=self.normalize_media_url_path,
                        save_obj=site, save_var="static_url")

    def ask_uploaded_media_url(self):
        """Ask the user the URL where uploaded media files are served."""
        page = ui.page("What URL will point to the uploaded media files?")

        ui.text(page, "Note that this is different from shipped media. This "
                      "is where all uploaded screenshots, file attachments, "
                      "and extension media will go. It must be a different "
                      "location from the shipped media.")
        ui.text(page, "If unsure, don't change the default.")

        ui.prompt_input(page, "Uploaded Media URL", site.media_url,
                        normalize_func=self.normalize_media_url_path,
                        save_obj=site, save_var="media_url")

    def ask_database_type(self):
        """Ask the user for the database type."""
        page = ui.page("What database type will you be using?")

        ui.prompt_choice(
            page, "Database Type",
            [
                ("mysql", Dependencies.get_support_mysql()),
                ("postgresql", Dependencies.get_support_postgresql()),
                ("sqlite3", "(not supported for production use)",
                 Dependencies.get_support_sqlite())
            ],
            save_obj=site, save_var="db_type")

    def ask_database_name(self):
        """Ask the user for the database name."""
        def determine_sqlite_path():
            site.db_name = sqlite_db_name

        sqlite_db_name = os.path.join(site.abs_install_dir, "data",
                                      "reviewboard.db")

        # Appears only if using sqlite.
        page = ui.page("Determining database file path",
                       is_visible_func=lambda: site.db_type == "sqlite3",
                       on_show_func=determine_sqlite_path)

        ui.text(page, "The sqlite database file will be stored in %s" %
                      sqlite_db_name)
        ui.text(page, "If you are migrating from an existing "
                      "installation, you can move your existing "
                      "database there, or edit settings_local.py to "
                      "point to your old location.")

        # Appears only if not using sqlite.
        page = ui.page("What database name should Review Board use?",
                       is_visible_func=lambda: site.db_type != "sqlite3")

        ui.disclaimer(page, "You need to create this database and grant "
                            "user modification rights before continuing. "
                            "See your database documentation for more "
                            "information.")

        ui.prompt_input(page, "Database Name", site.db_name,
                        save_obj=site, save_var="db_name")

    def ask_database_host(self):
        """Ask the user for the database host."""
        page = ui.page("What is the database server's address?",
                       is_visible_func=lambda: site.db_type != "sqlite3")

        ui.text(page, "This should be specified in hostname:port form. "
                      "The port is optional if you're using a standard "
                      "port for the database type.")

        ui.prompt_input(page, "Database Server", site.db_host,
                        save_obj=site, save_var="db_host")

    def ask_database_login(self):
        """Ask the user for database login credentials."""
        page = ui.page("What is the login and password for this database?",
                       is_visible_func=lambda: site.db_type != "sqlite3")

        ui.text(page, "This must be a user that has table creation and "
                      "modification rights on the database you already "
                      "specified.")

        ui.prompt_input(page, "Database Username", site.db_user,
                        save_obj=site, save_var="db_user")
        ui.prompt_input(page, "Database Password", site.db_pass, password=True,
                        save_obj=site, save_var="db_pass")
        ui.prompt_input(page, "Confirm Database Password",
                        password=True, save_obj=site,
                        save_var="reenter_db_pass")

    def ask_cache_type(self):
        """Ask the user what type of caching they'd like to use."""
        page = ui.page("What cache mechanism should be used?")

        ui.text(page, "memcached is strongly recommended. Use it unless "
                      "you have a good reason not to.")

        ui.prompt_choice(page, "Cache Type",
                         [("memcached", "(recommended)",
                           Dependencies.get_support_memcached()),
                          "file"],
                         save_obj=site, save_var="cache_type")

    def ask_cache_info(self):
        """Ask the user for caching configuration."""
        # Appears only if using memcached.
        page = ui.page("What memcached host should be used?",
                       is_visible_func=lambda: site.cache_type == "memcached")

        ui.text(page, "This is in the format of hostname:port")

        ui.prompt_input(page, "Memcache Server",
                        site.cache_info,
                        save_obj=site, save_var="cache_info")

        # Appears only if using file caching.
        page = ui.page("Where should the temporary cache files be stored?",
                       is_visible_func=lambda: site.cache_type == "file")

        ui.prompt_input(page, "Cache Directory",
                        site.cache_info or DEFAULT_FS_CACHE_PATH,
                        save_obj=site, save_var="cache_info")

    def ask_web_server_type(self):
        """Ask the user which web server they're using."""
        page = ui.page("What web server will you be using?")

        ui.prompt_choice(page, "Web Server", ["apache", "lighttpd"],
                         save_obj=site, save_var="web_server_type")

    def ask_python_loader(self):
        """Ask the user which Python loader they're using."""
        page = ui.page("What Python loader module will you be using?",
                       is_visible_func=lambda: (site.web_server_type ==
                                                "apache"))

        ui.text(page, "Based on our experiences, we recommend using "
                      "wsgi with Review Board.")

        ui.prompt_choice(page, "Python Loader",
                         [
                             ("wsgi", "(recommended)", True),
                             "fastcgi",
                         ],
                         save_obj=site, save_var="python_loader")

    def ask_admin_user(self):
        """Ask the user to create an admin account."""
        page = ui.page("Create an administrator account")

        ui.text(page, "To configure Review Board, you'll need an "
                      "administrator account. It is advised to have one "
                      "administrator and then use that account to grant "
                      "administrator permissions to your personal user "
                      "account.")

        ui.text(page, "If you plan to use NIS or LDAP, use an account name "
                      "other than your NIS/LDAP account so as to prevent "
                      "conflicts.")

        ui.prompt_input(page, "Username", site.admin_user,
                        save_obj=site, save_var="admin_user")
        ui.prompt_input(page, "Password", site.admin_password, password=True,
                        save_obj=site, save_var="admin_password")
        ui.prompt_input(page, "Confirm Password",
                        password=True, save_obj=site,
                        save_var="reenter_admin_password")
        ui.prompt_input(page, "E-Mail Address", site.admin_email,
                        save_obj=site, save_var="admin_email")
        ui.prompt_input(page, "Company/Organization Name", site.company,
                        save_obj=site, save_var="company", optional=True)

    def ask_support_data(self):
        """Ask the user if they'd like to enable support data collection."""
        page = ui.page('Enable collection of data for better support')

        ui.text(page, 'We would like to periodically collect data and '
                      'statistics about your installation to provide a '
                      'better support experience for you and your users.')

        ui.text(page, 'The data collected includes basic information such as '
                      'your company name, the version of Review Board, and '
                      'the size of your install. It does NOT include '
                      'confidential data such as source code. Data collected '
                      'never leaves our server and is never given to any '
                      'third parties for any purposes.')

        ui.text(page, 'We use this to provide a user support page that\'s '
                      'more specific to your server. We also use it to '
                      'determine which versions to continue to support, and '
                      'to help track how upgrades affect our number of bug '
                      'reports and support incidents.')

        ui.text(page, 'You can choose to turn this off at any time in '
                      'Support Settings in Review Board.')

        ui.prompt_input(page, 'Allow us to collect support data?',
                        site.send_support_usage_stats, yes_no=True,
                        save_obj=site, save_var='send_support_usage_stats')

    def show_install_status(self):
        """Show the install status page."""
        page = ui.page("Installing the site...", allow_back=False)
        ui.step(page, "Building site directories",
                site.rebuild_site_directory)
        ui.step(page, "Building site configuration files",
                site.generate_config_files)
        ui.step(page, "Creating database",
                site.update_database)
        ui.step(page, "Creating administrator account",
                site.create_admin_user)
        ui.step(page, "Saving site settings",
                self.save_settings)
        ui.step(page, "Setting up support",
                self.setup_support)
        ui.step(page, 'Finishing the install',
                self.finalize_install)

    def show_finished(self):
        """Show the finished page."""
        page = ui.page("The site has been installed", allow_back=False)
        ui.text(page, "The site has been installed in %s" %
                      site.abs_install_dir)
        ui.text(page, "Sample configuration files for web servers and "
                      "cron are available in the conf/ directory.")
        ui.text(page, "You need to modify the ownership of the "
                      "following directories and their contents to be owned "
                      "by the web server:")

        ui.itemized_list(page, None, [
            os.path.join(site.abs_install_dir, 'htdocs', 'media', 'uploaded'),
            os.path.join(site.abs_install_dir, 'htdocs', 'media', 'ext'),
            os.path.join(site.abs_install_dir, 'htdocs', 'static', 'ext'),
            os.path.join(site.abs_install_dir, 'data'),
        ])

        ui.text(page, "For more information, visit:")
        ui.urllink(page,
                   "%sadmin/installation/creating-sites/" % get_manual_url())

    def show_get_more(self):
        """Show the "Get More out of Review Board" page."""
        from reviewboard.admin.support import get_install_key

        page = ui.page('Get more out of Review Board', allow_back=False)
        ui.text(page,
                'To enable PDF document review, code review reports, enhanced '
                'scalability, and support for GitHub Enterprise, Bitbucket '
                'Server, AWS CodeCommit, Team Foundation Server, and more, '
                'install Power Pack at:')
        ui.urllink(page, 'https://www.reviewboard.org/powerpack/')

        ui.text(page, 'Your install key for Power Pack is: %s'
                      % get_install_key())

        ui.text(page, 'Support contracts for Review Board are also available:')
        ui.urllink(page, SUPPORT_URL)

    def save_settings(self):
        """Save some settings in the database."""
        from django.contrib.sites.models import Site
        from djblets.siteconfig.models import SiteConfiguration

        cur_site = Site.objects.get_current()
        cur_site.domain = site.domain_name
        cur_site.save()

        if site.static_url.startswith("http"):
            site_static_url = site.static_url
        else:
            site_static_url = site.site_root + site.static_url

        if site.media_url.startswith("http"):
            site_media_url = site.media_url
        else:
            site_media_url = site.site_root + site.media_url

        htdocs_path = os.path.join(site.abs_install_dir, 'htdocs')
        site_media_root = os.path.join(htdocs_path, "media")
        site_static_root = os.path.join(htdocs_path, "static")

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("company", site.company)
        siteconfig.set("send_support_usage_stats",
                       site.send_support_usage_stats)
        siteconfig.set("site_static_url", site_static_url)
        siteconfig.set("site_static_root", site_static_root)
        siteconfig.set("site_media_url", site_media_url)
        siteconfig.set("site_media_root", site_media_root)
        siteconfig.set("site_admin_name", site.admin_user)
        siteconfig.set("site_admin_email", site.admin_email)
        siteconfig.set('manual-updates', {
            'static-media': True,
        })
        siteconfig.save()

        if not is_windows:
            abs_sitelist = os.path.abspath(site.sitelist)

            # Add the site to the sitelist file.
            print('Saving site %s to the sitelist %s'
                  % (site.install_dir, abs_sitelist))
            print()

            sitelist = SiteList(abs_sitelist)
            sitelist.add_site(site.install_dir)

    def setup_support(self):
        """Set up the support page for the installation."""
        if site.send_support_usage_stats:
            site.register_support_page()

    def finalize_install(self):
        """Finalize the installation."""
        finalize_setup()


class UpgradeCommand(Command):
    """Upgrades an existing site installation.

    This will synchronize media trees and upgrade the database, unless
    otherwise specified.
    """

    def add_options(self, parser):
        """Add any command-specific options to the parser."""
        group = OptionGroup(parser, "'upgrade' command",
                            self.__doc__.strip())
        group.add_option("--no-db-upgrade", action="store_false",
                         dest="upgrade_db", default=True,
                         help="don't upgrade the database")
        group.add_option("--all-sites", action="store_true",
                         dest="all_sites", default=False,
                         help="Upgrade all installed sites")
        parser.add_option_group(group)

    def get_site_paths(self, options):
        """Return site paths defined in the command options.

        Args:
            options (argparse.Namespace):
                The parsed options for the command.

        Returns:
            list of unicode:
            The list of site paths.

        Raises:
            MissingSiteError:
                Site paths were not defined.
        """
        # Check whether we've been asked to upgrade all installed sites
        # by 'rb-site upgrade' with no path specified.
        if options.all_sites:
            sitelist = SiteList(options.sitelist)
            site_paths = sitelist.sites

            if len(site_paths) == 0:
                raise MissingSiteError(
                    'No Review Board sites were listed in %s' % sitelist.path)
        else:
            site_paths = super(UpgradeCommand, self).get_site_paths(options)

        return site_paths

    def run(self):
        """Run the command."""
        site.setup_settings()

        from djblets.siteconfig.models import SiteConfiguration

        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.version != VERSION:
            print('Upgrading Review Board from %s to %s'
                  % (siteconfig.version, VERSION))
            print()

            # We'll save this later, in case things go wrong. This will at
            # least prevent reviewboard.admin.management.sites.init_siteconfig
            # from outputting the above message.
            siteconfig.version = VERSION
            siteconfig.save(update_fields=('version',))

        diff_dedup_needed = site.get_diff_dedup_needed()
        static_media_upgrade_needed = site.get_static_media_upgrade_needed()
        data_dir_exists = os.path.exists(
            os.path.join(site.install_dir, "data"))

        print('* Rebuilding directory structure')
        site.rebuild_site_directory()
        site.generate_cron_files()

        if site.get_settings_upgrade_needed():
            print('* Upgrading settings_local.py')
            site.upgrade_settings()

        if site.get_wsgi_upgrade_needed():
            print('* Upgrading reviewboard.wsgi')
            site.upgrade_wsgi()

        if options.upgrade_db:
            site.update_database(report_progress=True)

            print()
            print('* Resetting in-database caches.')
            site.run_manage_command("fixreviewcounts")

        siteconfig.save()

        site.harden_passwords()

        if siteconfig.get('send_support_usage_stats'):
            site.register_support_page()

        print()
        print("Upgrade complete!")

        if not data_dir_exists:
            # This is an upgrade of a site that pre-dates the new $HOME
            # directory ($sitedir/data). Tell the user how to upgrade things.
            print()
            print("A new 'data' directory has been created inside of your "
                  "site")
            print("directory. This will act as the home directory for "
                  "programs")
            print("invoked by Review Board.")
            print()
            print("You need to change the ownership of this directory so that")
            print("the web server can write to it.")

        if static_media_upgrade_needed:
            from django.conf import settings

            if 'manual-updates' not in siteconfig.settings:
                siteconfig.settings['manual-updates'] = {}

            siteconfig.settings['manual-updates']['static-media'] = False
            siteconfig.save()

            static_dir = "%s/htdocs/static" % \
                         site.abs_install_dir.replace('\\', '/')

            print()
            print("The location of static media files (CSS, JavaScript, "
                  "images)")
            print("has changed. You will need to make manual changes to ")
            print("your web server configuration.")
            print()
            print("For Apache, you will need to add:")
            print()
            print("    <Location \"%sstatic\">" % settings.SITE_ROOT)
            print("        SetHandler None")
            print("    </Location>")
            print()
            print("    Alias %sstatic \"%s\"" % (settings.SITE_ROOT,
                                                 static_dir))
            print()
            print("For lighttpd:")
            print()
            print("    alias.url = (")
            print("        ...")
            print("        \"%sstatic\" => \"%s\"," % (settings.SITE_ROOT,
                                                       static_dir))
            print("        ...")
            print("    )")
            print()
            print("    url.rewrite-once = (")
            print("        ...")
            print("        \"^(%sstatic/.*)$\" => \"$1\"," %
                  settings.SITE_ROOT)
            print("        ...")
            print("    )")
            print()
            print("Once you have made these changes, type the following ")
            print("to resolve this:")
            print()
            print("    $ rb-site manage %s resolve-check static-media" %
                  site.abs_install_dir)

        if diff_dedup_needed:
            print()
            print('There are duplicate copies of diffs in your database that '
                  'can be condensed.')
            print('These are the result of posting several iterations of a '
                  'change for review on')
            print('older versions of Review Board.')
            print()
            print('Removing duplicate diff data will save space in your '
                  'database and speed up')
            print('future upgrades.')
            print()
            print('To condense duplicate diffs, type the following:')
            print()
            print('    $ rb-site manage %s condensediffs'
                  % site.abs_install_dir)


class ManageCommand(Command):
    """Runs a Django management command on the site."""

    help_text = (
        'Runs a Django management command on the site. '
        'Usage: `rb-site manage <path> <command> -- <arguments>.` '
        'Run `manage -- --help` for the list of commands.'
    )

    def add_options(self, parser):
        """Add any command-specific options to the parser."""
        group = OptionGroup(parser, "'manage' command", self.help_text)
        parser.add_option_group(group)

    def run(self):
        """Run the command."""
        site.setup_settings()

        from reviewboard import initialize
        initialize()

        if len(args) == 0:
            ui.error("A manage command is needed.",
                     done_func=lambda: sys.exit(1))
        else:
            site.run_manage_command(args[0], args[1:])
            sys.exit(0)


# A list of all commands supported by rb-site.
COMMANDS = {
    "install": InstallCommand(),
    "upgrade": UpgradeCommand(),
    "manage": ManageCommand(),
}


def parse_options(args):
    """Parse the given options.

    Args:
        args (list of unicode):
            The command line arguments to parse.

    Returns:
        tuple:
        A tuple containing:

        1. The provided command name.
        2. The list of arguments for the command.

    Raises:
        CommandError:
            Option parsing or handling for the command failed.
    """
    global options

    parser = OptionParser(
        usage='%prog command [options] path',
        version=(
            '%%prog %s\n'
            'Python %s\n'
            'Installed to %s'
            % (VERSION, sys.version, os.path.dirname(reviewboard.__file__))
        ))

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=DEBUG,
                      help="display debug output")

    sorted_commands = list(COMMANDS.keys())
    sorted_commands.sort()

    for cmd_name in sorted_commands:
        command = COMMANDS[cmd_name]
        command.add_options(parser)

    (options, args) = parser.parse_args(args)

    if len(args) < 1:
        parser.print_help()
        sys.exit(1)

    command_name = args[0]

    if len(args) > 1:
        options.site_path = args[1]
        globals()['args'] = args[2:]
    else:
        options.site_path = None
        globals()['args'] = []

    command = COMMANDS[command_name]
    site_paths = command.get_site_paths(options)
    validate_site_paths(site_paths,
                        require_exists=command.require_site_paths_exist)

    return command_name, site_paths


def validate_site_paths(site_paths, require_exists=True):
    """Validate whether all site paths exist.

    Args:
        site_paths (list of unicode):
            The list of site paths.

        require_exists (bool, optional):
            Whether the site paths must exist.

    Raises:
        MissingSiteError:
            A site path does not exist, or no site paths were found.
    """
    if not site_paths:
        raise MissingSiteError(
            "You'll need to provide a site directory to run this command.")

    if require_exists:
        for site_path in site_paths:
            if not os.path.exists(site_path):
                raise MissingSiteError(
                    'The site directory "%s" does not exist.'
                    % site_path)


def main():
    """Main application loop."""
    global site
    global ui

    # Ensure we import djblets.log for it to monkey-patch the logging module.
    import_module('djblets.log')

    logging.basicConfig(level=logging.INFO)

    # Create an initial UI without color. We'll override this once we know
    # if color can be enabled.
    ui = ConsoleUI(allow_color=False)

    try:
        command_name, site_paths = parse_options(sys.argv[1:])
        command = COMMANDS[command_name]

        ui = ConsoleUI(allow_color=options.allow_term_color)

        for install_dir in site_paths:
            site = Site(install_dir, options)

            os.environ[str('HOME')] = force_str(
                os.path.join(site.install_dir, 'data'))

            command.run()
            ui.run()
    except CommandError as e:
        ui.error(six.text_type(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
