#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import argparse
import imp
import json
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
from collections import OrderedDict
from importlib import import_module
from random import choice as random_choice

from django.db.utils import OperationalError
from django.dispatch import receiver
from django.utils import six
from django.utils.encoding import force_str, force_text
from django.utils.six.moves.urllib.request import urlopen

import reviewboard
from reviewboard import finalize_setup, get_manual_url, get_version_string
from reviewboard.admin.import_utils import has_module
from reviewboard.cmdline.utils.console import (ConsoleUI,
                                               get_console,
                                               init_console)
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

    SECRET_KEY_LEN = 50

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
        self.secret_key = None
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

        self.generate_settings_local()

    def generate_settings_local(self):
        """Generate the settings_local.py file."""
        # Generate a secret key based on Django's code.
        secret_key = self.secret_key or ''.join(
            random_choice('abcdefghijklmnopqrstuvwxyz0123456789'
                          '!@#$%^&*(-_=+)')
            for i in range(Site.SECRET_KEY_LEN)
        )

        db_engine = self.db_type

        db_info = OrderedDict()
        db_info['ENGINE'] = 'django.db.backends.%s' % db_engine
        db_info['NAME'] = self.db_name.replace('\\', '\\\\')

        if db_engine != 'sqlite3':
            if ':' in self.db_host:
                self.db_host, self.db_port = self.db_host.split(':', 1)

            db_info['USER'] = self.db_user or ''
            db_info['PASSWORD'] = self.db_pass or ''
            db_info['HOST'] = self.db_host or ''
            db_info['PORT'] = self.db_port or ''

        cache_info = OrderedDict()
        cache_info['BACKEND'] = self.CACHE_BACKENDS[self.cache_type]
        cache_info['LOCATION'] = self.cache_info

        encoder = json.JSONEncoder(indent=4,
                                   separators=(',', ': '))

        self.process_template(
            template_path=(self.settings_local_template or
                           'cmdline/conf/settings_local.py.in'),
            template_is_local=self.settings_local_template is not None,
            dest_filename=os.path.join(self.install_dir, 'conf',
                                       'settings_local.py'),
            extra_context={
                'allowed_hosts_json': encoder.encode([self.domain_name or
                                                      '*']),
                'caches_json': encoder.encode({
                    'default': cache_info,
                }),
                'databases_json': encoder.encode({
                    'default': db_info,
                }),
                'secret_key': encoder.encode(secret_key),
                'site_root': encoder.encode(self.site_root or ''),
            })

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
                ui.error(
                    'There was an error connecting to the database. '
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
            ui.error(
                'There was an error updating the database. Make sure the '
                'database is created and has the appropriate permissions, '
                'and then try again.'
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

    def get_settings_local(self):
        """Return the current local settings module.

        This exists primarily to allow unit tests to override the results.

        Returns:
            module:
            The ``settings_local`` module.

        Raises:
            ImportError:
                The module could not be imported.
        """
        import settings_local

        return settings_local

    def get_settings_upgrade_needed(self):
        """Return whether a settings upgrade is needed.

        Returns:
            bool:
            ``True`` if a settings upgrade is needed. ``False`` if it is not.
        """
        try:
            settings_local = self.get_settings_local()

            if (hasattr(settings_local, 'DATABASE_ENGINE') or
                hasattr(settings_local, 'CACHE_BACKEND')):
                return True

            if hasattr(settings_local, 'DATABASES'):
                engine = settings_local.DATABASES['default']['ENGINE']

                if ('.' not in engine or
                    engine == 'django.db.backends.postgresql_psycopg2'):
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
        buf = []
        database_info = OrderedDict()
        cache_info = OrderedDict()

        old_db_engine_path = None
        new_db_engine_path = None

        perform_upgrade = False
        needs_databases_upgrade = False
        needs_db_engine_path_upgrade = False
        needs_caches_upgrade = False

        from django.core.cache import InvalidCacheBackendError
        from djblets.util.compat.django.core.cache import parse_backend_uri

        try:
            settings_local = self.get_settings_local()

            if hasattr(settings_local, 'DATABASE_ENGINE'):
                # Django 1.3/Review Board 1.6 moved away from individual
                # DATABASE_* settings and introduced DATABASES.
                engine = settings_local.DATABASE_ENGINE

                # Don't convert anything other than the ones we know about,
                # or third parties with custom databases may have problems.
                if engine == 'postgresql_psycopg2':
                    engine = 'postgresql'

                if engine in ('sqlite3', 'mysql', 'postgresql'):
                    engine = 'django.db.backends.%s' % engine

                database_info['ENGINE'] = engine

                for key in ('NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
                    database_info[key] = getattr(settings_local,
                                                 'DATABASE_%s' % key, '')

                needs_databases_upgrade = True
                perform_upgrade = True

            if hasattr(settings_local, 'DATABASES'):
                engine = settings_local.DATABASES['default']['ENGINE']

                if '.' not in engine:
                    # Review Board 1.5 moved from DATABASE_* to DATABASES,
                    # but kept the legacy engine names (short names and not
                    # full paths).
                    old_db_engine_path = engine
                    new_db_engine_path = 'django.db.backends.%s' % {
                        'postgresql_psycopg2': 'postgresql',
                    }.get(engine, engine)

                    needs_db_engine_path_upgrade = True
                    perform_upgrade = True
                elif engine == 'django.db.backends.postgresql_psycopg2':
                    # Django 1.9 made this engine an alias. The legacy engine
                    # was deprecated officially in 2.0.
                    old_db_engine_path = engine
                    new_db_engine_path = 'django.db.backends.postgresql'
                    needs_db_engine_path_upgrade = True
                    perform_upgrade = True

            if hasattr(settings_local, 'CACHE_BACKEND'):
                # Django 1.3/Review Board 1.6 moved away from CACHE_BACKEND
                # to CACHES.
                try:
                    backend_info = parse_backend_uri(
                        settings_local.CACHE_BACKEND)

                    cache_info['BACKEND'] = \
                        self.CACHE_BACKENDS[backend_info[0]]
                    cache_info['LOCATION'] = backend_info[1]

                    needs_caches_upgrade = True
                    perform_upgrade = True
                except InvalidCacheBackendError:
                    pass
        except ImportError:
            sys.stderr.write("Unable to import settings_local for upgrade.\n")
            return

        if not perform_upgrade:
            return

        # Compute new settings for the file.
        encoder = json.JSONEncoder(indent=4,
                                   separators=(',', ': '))

        if needs_db_engine_path_upgrade:
            db_engine_re = re.compile(
                r'^(?P<pre>\s*[\'"]ENGINE[\'"]:\s*[\'"])' +
                re.escape(old_db_engine_path) +
                r'(?P<post>[\'"].*)$')
        else:
            db_engine_re = None

        with open(settings_file, 'r') as fp:
            # Track which settings we've found and no longer want to process.
            # This is important so that we know to skip all but the first
            # "DATABASE_"-prefixed setting, for instance.
            found_database = False
            found_cache = False

            for line in fp.readlines():
                if needs_databases_upgrade and line.startswith('DATABASE_'):
                    if not found_database:
                        found_database = True

                        buf.append('DATABASES = %s\n' % encoder.encode({
                            'default': database_info,
                        }))
                elif (needs_caches_upgrade and
                      line.startswith('CACHE_BACKEND') and
                      backend_info):
                    if not found_cache:
                        found_cache = True

                        buf.append('CACHES = %s\n' % encoder.encode({
                            'default': cache_info,
                        }))
                elif (needs_db_engine_path_upgrade and
                      db_engine_re.match(line)):
                    buf.append(db_engine_re.sub(
                        r'\g<pre>' + new_db_engine_path + r'\g<post>',
                        line))
                else:
                    buf.append(line)

        with open(settings_file, 'w') as fp:
            fp.writelines(buf)

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

    def process_template(self, template_path, dest_filename,
                         template_is_local=False, extra_context={}):
        """Generate a file from a template.

        Args:
            template_path (unicode):
                The path to the template file within the ReviewBoard package.

            dest_filename (unicode):
                The absolute path on the filesystem to write the generated
                file.

            template_is_local (bool, optional):
                Whether or not the template path provided is a local file
                on the filesystem.

            extra_context (dict, optional):
                Extra variable context for the template.
        """
        domain_name = self.domain_name or ''
        domain_name_escaped = domain_name.replace('.', '\\.')

        if template_is_local:
            with open(template_path, 'r') as fp:
                template = force_text(fp.read())
        else:
            template = (
                pkg_resources.resource_string('reviewboard', template_path)
                .decode('utf-8')
            )

        sitedir = os.path.abspath(self.install_dir).replace('\\', '/')

        if self.site_root:
            site_root = self.site_root
            site_root_noslash = site_root[1:-1]
        else:
            site_root = '/'
            site_root_noslash = ''

        # Check if this is a .exe.
        if (hasattr(sys, 'frozen') or     # new py2exe
            hasattr(sys, 'importers') or  # new py2exe
            imp.is_frozen('__main__')):   # tools/freeze
            rbsite_path = sys.executable
        else:
            rbsite_path = '"%s" "%s"' % (sys.executable, sys.argv[0])

        context = {
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
            extra_context['apache_auth'] = self.apache_auth

        context.update(extra_context)

        template = re.sub(r'@([a-z_]+)@', lambda m: context.get(m.group(1)),
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


class RBSiteHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Formats help text by preserving paragraphs."""

    indent_len = 2

    def _fill_text(self, text, width, indent):
        """Return wrapped description text.

        This will wrap each contained paragraph (separated by a newline)
        individually.

        Args:
            text (unicode):
                The text to wrap.

            width (int, unused):
                The terminal width.

            indent (unicode, unused):
                The string to prefix each line with, for indentation.

        Returns:
            unicode:
            The wrapped text.
        """
        indent_len_str = ' ' * self.indent_len

        return '\n'.join(
            ui.wrap_text(paragraph, indent=indent or indent_len_str)
            for paragraph in text.split('\n')
        )


class RBSiteVersionAction(argparse.Action):
    """Display the rb-site/Review Board version.

    This is used instead of :py:mod:`argparse`'s default version handling
    in order to print text unindented and unwrapped.
    """

    def __init__(self, **kwargs):
        """Initialize the action.

        Args:
            **kwargs (dict):
                Keyword arguments for the action.
        """
        super(RBSiteVersionAction, self).__init__(nargs=0, **kwargs)

    def __call__(self, parser, *args, **kwargs):
        """Call the action.

        This will display the version information directly to the terminal
        and then exit.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser that called this action.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.
        """
        print('Review Board/rb-site %s' % VERSION)
        print('Python %s' % (sys.version,))
        print('Installed to %s' % os.path.dirname(reviewboard.__file__))
        parser.exit()


class Command(object):
    """An abstract command."""

    #: Command line usage information for the command's help output.
    usage = '%(prog)s <site-path> [<options>]'

    #: Help text for the command, shown in the main rb-site help output.
    help_text = None

    #: A description of the command, when displaying the command's own help.
    description_text = None

    #: Formatter class for help output.
    help_formatter_cls = RBSiteHelpFormatter

    #: An error message used if a site directory was not provided.
    no_site_error = None

    #: Whether the command absolutely requires a site positional argument.
    requires_site_arg = True

    needs_ui = False

    #: Whether the site paths passed to the command must exist.
    require_site_paths_exist = True

    def add_options(self, parser):
        """Add any command-specific options to the parser.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for this subcommand.
        """
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

    def run(self, site, options):
        """Run the command.

        Args:
            site (Site):
                The site to operate on.

            options (argparse.Namespace):
                The parsed options for the command.
        """
        raise NotImplementedError


class InstallCommand(Command):
    """Installer command.

    This command installs a new Review Board site tree and generates web server
    configuration files. This will ask several questions about the site before
    performing the installation.
    """

    help_text = (
        'install a new Review Board site, setting up the database and '
        'web server configuration'
    )

    description_text = (
        'This will guide you through installing a new Review Board site, '
        'asking you questions in order to connect up to a database and '
        'set up configuration for your web server.'
    )

    needs_ui = True
    require_site_paths_exist = False

    def add_options(self, parser):
        """Add any command-specific options to the parser.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for this subcommand.
        """
        parser.add_argument(
            '--advanced',
            action='store_true',
            dest='advanced',
            default=False,
            help='provide more advanced configuration options')
        parser.add_argument(
            '--copy-media',
            action='store_true',
            dest='copy_media',
            default=is_windows,
            help='copy media files instead of symlinking')
        parser.add_argument(
            '--opt-in-support-data',
            action='store_true',
            default=False,
            dest='send_support_usage_stats',
            help='opt out of sending data and stats for improved user and '
                 'admin support')
        parser.add_argument(
            '--opt-out-support-data',
            action='store_false',
            default=False,
            dest='send_support_usage_stats',
            help='opt out of sending data and stats for improved user and '
                 'admin support (default)')
        parser.add_argument(
            '--company',
            help='the name of the company or organization that owns the '
                 'server')
        parser.add_argument(
            '--domain-name',
            help='fully-qualified host name of the site, excluding the '
                 'https://, port, or path')
        parser.add_argument(
            '--site-root',
            default='/',
            help='path to the site relative to the domain name')
        parser.add_argument(
            '--static-url',
            default='static/',
            help='the URL containing the static (shipped) media files')
        parser.add_argument(
            '--media-url',
            default='media/',
            help='the URL containing the uploaded media files')
        parser.add_argument(
            '--db-type',
            help='database type (mysql, postgresql or sqlite3)')
        parser.add_argument(
            '--db-name',
            default='reviewboard',
            help='database name (not for sqlite3)')
        parser.add_argument(
            '--db-host',
            default='localhost',
            help='database host (not for sqlite3)')
        parser.add_argument(
            '--db-user',
            help='database user (not for sqlite3)')
        parser.add_argument(
            '--db-pass',
            help='password for the database user (not for sqlite3)')
        parser.add_argument(
            '--cache-type',
            default='memcached',
            help='cache server type (memcached or file)')
        parser.add_argument(
            '--cache-info',
            default='localhost:11211',
            help='cache identifier (memcached connection string or file '
                 'cache directory)')
        parser.add_argument(
            '--web-server-type',
            default='apache',
            help='web server (apache or lighttpd)')
        parser.add_argument(
            '--web-server-port',
            help='port that the web server should listen on',
            default='80')
        parser.add_argument(
            '--python-loader',
            default='wsgi',
            help='Python loader for apache (fastcgi or wsgi)')
        parser.add_argument(
            '--admin-user',
            default='admin',
            help="the site administrator's username")
        parser.add_argument(
            '--admin-password',
            help="the site administrator's password")
        parser.add_argument(
            '--admin-email',
            help="the site administrator's e-mail address")
        parser.add_argument(
            '--secret-key',
            default=None,
            help="an explicit value for SECRET_KEY (%s characters long) -- "
                 "if automating an install with an existing/shared database, "
                 "each server must use the same value, which you can find "
                 "in an existing site's conf/settings_local.py"
                 % Site.SECRET_KEY_LEN)
        parser.add_argument(
            '--settings-local-template',
            default=None,
            metavar='PATH',
            help='a custom template used for the settings_local.py file '
                 '(defaults to %s)'
                 % pkg_resources.resource_filename(
                     'reviewboard', 'cmdline/conf/settings_local.py.in'))

        if not is_windows:
            parser.add_argument(
                '--sitelist',
                default=SITELIST_FILE_UNIX,
                help='the path to a file storing a list of installed sites')

    def run(self, site, options):
        """Run the command.

        Args:
            site (Site):
                The site to operate on.

            options (argparse.Namespace):
                The parsed options for the command.
        """
        self.site = site

        if not self.check_permissions():
            return

        if (options.secret_key and
            len(options.secret_key) < Site.SECRET_KEY_LEN):
            ui.error('The value for --secret-key must be at least %s '
                     'characters long. It can contain letters, numbers, '
                     'and symbols.'
                     % Site.SECRET_KEY_LEN,
                     done_func=lambda: sys.exit(1))
            return

        if options.settings_local_template is not None:
            if not os.path.exists(options.settings_local_template):
                ui.error('The path specified in --settings-local-template '
                         '(%s) could not be found.'
                         % options.settings_local_template,
                         done_func=lambda: sys.exit(1))
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
        install_dir = self.site.install_dir

        # Make sure we can create the directory first.
        try:
            # TODO: Do some chown tests too.

            if os.path.exists(install_dir):
                # Remove it first, to see if we own it and to handle the
                # case where the directory is empty as a result of a
                # previously canceled install.
                os.rmdir(install_dir)

            os.mkdir(install_dir)

            # Don't leave a mess. We'll actually do this at the end.
            os.rmdir(install_dir)
            return True
        except OSError:
            # Likely a permission error.
            ui.error("Unable to create the %s directory. Make sure "
                     "you're running as an administrator and that the "
                     "directory does not contain any files."
                     % install_dir,
                     done_func=lambda: sys.exit(1))
            return False

    def print_introduction(self):
        """Print an introduction to the site installer."""
        page = ui.page("Welcome to the Review Board site installation wizard")

        ui.text(
            page,
            'This will prepare a Review Board site installation in:')
        ui.text(page, self.site.abs_install_dir)
        ui.text(
            page,
            'We need to know a few things before we can prepare your site '
            'for installation. This will only take a few minutes.')

    def print_missing_dependencies(self):
        """Print information on any missing dependencies."""
        fatal, missing_dep_groups = Dependencies.get_missing()

        if missing_dep_groups:
            if fatal:
                page = ui.page('Required modules are missing')
                ui.text(
                    page,
                    'You are missing Python modules that are needed before '
                    'the installation process. You will need to install the '
                    'necessary modules and restart the install.')
            else:
                page = ui.page('Make sure you have the modules you need')
                ui.text(
                    page,
                    'Depending on your installation, you may need certain '
                    'Python modules and servers that are currently missing.')
                ui.text(
                    page,
                    'If you need support for any of the following, you will '
                    'need to install the necessary modules and restart the '
                    'install.')

            for group in missing_dep_groups:
                ui.itemized_list(page, group['title'], group['dependencies'])

        return fatal

    def ask_domain(self):
        """Ask the user what domain Review Board will be served from."""
        site = self.site

        page = ui.page("What's the host name for this site?")

        ui.text(
            page,
            'This should be the fully-qualified host name without the '
            'http://, port or path.')

        ui.prompt_input(page, 'Domain Name', site.domain_name,
                        save_obj=site, save_var='domain_name')

    def ask_site_root(self):
        """Ask the user what site root they'd like."""
        site = self.site

        page = ui.page('What URL path points to Review Board?')

        ui.text(
            page,
            'Typically, Review Board exists at the root of a URL. For '
            'example, http://reviews.example.com/. In this case, you would '
            'specify "/".')
        ui.text(
            page,
            'However, if you want to listen to, say, '
            'http://example.com/reviews/, you can specify "/reviews/".')
        ui.text(
            page,
            'Note that this is the path relative to the domain and should '
            'not include the domain name.')

        ui.prompt_input(page, 'Root Path', site.site_root,
                        normalize_func=self.normalize_root_url_path,
                        save_obj=site, save_var='site_root')

    def ask_shipped_media_url(self):
        """Ask the user the URL where shipped media files are served."""
        site = self.site

        page = ui.page("What URL will point to the shipped media files?")

        ui.text(
            page,
            "While most installations distribute media files on the same "
            "server as the rest of Review Board, some custom installs may "
            "instead have a separate server for this purpose.")
        ui.text(
            page,
            "If unsure, don't change the default.")

        ui.prompt_input(page, 'Shipped Media URL', site.static_url,
                        normalize_func=self.normalize_media_url_path,
                        save_obj=site, save_var='static_url')

    def ask_uploaded_media_url(self):
        """Ask the user the URL where uploaded media files are served."""
        site = self.site

        page = ui.page('What URL will point to the uploaded media files?')

        ui.text(
            page,
            "Note that this is different from shipped media. This is where "
            "all uploaded screenshots, file attachments, and extension media "
            "will go. It must be a different location from the shipped media.")
        ui.text(
            page,
            "If unsure, don't change the default.")

        ui.prompt_input(page, 'Uploaded Media URL', site.media_url,
                        normalize_func=self.normalize_media_url_path,
                        save_obj=site, save_var='media_url')

    def ask_database_type(self):
        """Ask the user for the database type."""
        page = ui.page('What database type will you be using?')

        ui.prompt_choice(
            page, 'Database Type',
            [
                ('mysql', Dependencies.get_support_mysql()),
                ('postgresql', Dependencies.get_support_postgresql()),
                ('sqlite3', '(not supported for production use)',
                 Dependencies.get_support_sqlite())
            ],
            save_obj=self.site, save_var='db_type')

    def ask_database_name(self):
        """Ask the user for the database name."""
        site = self.site

        def determine_sqlite_path():
            site.db_name = sqlite_db_name

        sqlite_db_name = os.path.join(site.abs_install_dir, 'data',
                                      'reviewboard.db')

        # Appears only if using sqlite.
        page = ui.page('Determining database file path',
                       is_visible_func=lambda: site.db_type == 'sqlite3',
                       on_show_func=determine_sqlite_path)

        ui.text(
            page,
            'The sqlite database file will be stored in: %s' % sqlite_db_name)
        ui.text(
            page,
            'If you are migrating from an existing installation, you can '
            'move your existing database there, or edit '
            'conf/settings_local.py to point to your old location.')

        # Appears only if not using sqlite.
        page = ui.page('What database name should Review Board use?',
                       is_visible_func=lambda: site.db_type != 'sqlite3')

        ui.disclaimer(
            page,
            'You need to create this database and grant user modification '
            'rights before continuing. See your database documentation for '
            'more information.')

        ui.prompt_input(page, 'Database Name', site.db_name,
                        save_obj=site, save_var='db_name')

    def ask_database_host(self):
        """Ask the user for the database host."""
        site = self.site

        page = ui.page("What is the database server's address?",
                       is_visible_func=lambda: site.db_type != "sqlite3")

        ui.text(
            page,
            "This should be specified in hostname:port form. The port is "
            "optional if you're using a standard port for the database type.")

        ui.prompt_input(page, 'Database Server', site.db_host,
                        save_obj=site, save_var='db_host')

    def ask_database_login(self):
        """Ask the user for database login credentials."""
        site = self.site

        page = ui.page("What is the login and password for this database?",
                       is_visible_func=lambda: site.db_type != "sqlite3")

        ui.text(
            page,
            'This must be a user that has table creation and modification '
            'rights on the database you already specified.')

        ui.prompt_input(page, 'Database Username', site.db_user,
                        save_obj=site, save_var='db_user')
        ui.prompt_input(page, 'Database Password', site.db_pass, password=True,
                        save_obj=site, save_var='db_pass')
        ui.prompt_input(page, 'Confirm Database Password',
                        password=True, save_obj=site,
                        save_var='reenter_db_pass')

    def ask_cache_type(self):
        """Ask the user what type of caching they'd like to use."""
        site = self.site

        page = ui.page('What cache mechanism should be used?')

        ui.text(
            page,
            'memcached is strongly recommended. Use it unless you have '
            'a good reason not to.')

        ui.prompt_choice(
            page,
            'Cache Type',
            [
                ('memcached', '(recommended)',
                 Dependencies.get_support_memcached()),
                'file',
            ],
            save_obj=site,
            save_var='cache_type')

    def ask_cache_info(self):
        """Ask the user for caching configuration."""
        site = self.site

        # Appears only if using memcached.
        page = ui.page('What memcached host should be used?',
                       is_visible_func=lambda: site.cache_type == 'memcached')

        ui.text(page, 'This is in the format of hostname:port')

        ui.prompt_input(page, 'Memcache Server',
                        site.cache_info,
                        save_obj=site, save_var='cache_info')

        # Appears only if using file caching.
        page = ui.page('Where should the temporary cache files be stored?',
                       is_visible_func=lambda: site.cache_type == 'file')

        ui.prompt_input(page, 'Cache Directory',
                        site.cache_info or DEFAULT_FS_CACHE_PATH,
                        save_obj=site, save_var='cache_info')

    def ask_web_server_type(self):
        """Ask the user which web server they're using."""
        page = ui.page("What web server will you be using?")

        ui.prompt_choice(page, "Web Server", ["apache", "lighttpd"],
                         save_obj=self.site, save_var="web_server_type")

    def ask_python_loader(self):
        """Ask the user which Python loader they're using."""
        site = self.site

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
        site = self.site

        page = ui.page('Create an administrator account')

        ui.text(
            page,
            "To configure Review Board, you'll need an administrator "
            "account. It is advised to have one administrator and then use "
            "that account to grant administrator permissions to your "
            "personal user account.")

        ui.text(
            page,
            "If you plan to use NIS or LDAP, use an account name other "
            "than your NIS/LDAP account so as to prevent conflicts.")

        ui.prompt_input(page, 'Username', site.admin_user,
                        save_obj=site, save_var='admin_user')
        ui.prompt_input(page, 'Password', site.admin_password, password=True,
                        save_obj=site, save_var='admin_password')
        ui.prompt_input(page, 'Confirm Password',
                        password=True, save_obj=site,
                        save_var='reenter_admin_password')
        ui.prompt_input(page, 'E-Mail Address', site.admin_email,
                        save_obj=site, save_var='admin_email')
        ui.prompt_input(page, 'Company/Organization Name', site.company,
                        save_obj=site, save_var='company', optional=True)

    def ask_support_data(self):
        """Ask the user if they'd like to enable support data collection."""
        site = self.site

        page = ui.page('Enable collection of data for better support')

        ui.text(
            page,
            'We would like to periodically collect some general data and '
            'statistics about your installation to provide a better support '
            'experience for you and your users.')

        ui.itemized_list(
            page,
            title='The following is collected',
            items=[
                'Review Board and Python version',
                'Server domain and install key',
                'Your company name (if provided above)',
                'Administrator name and e-mail',
                'Number of user accounts (but no identifying information)',
            ])

        ui.text(
            page,
            'It does NOT include confidential data such as source code or '
            'user information. Data collected NEVER leaves our server and '
            'is NEVER given to any third parties for ANY purposes.')

        ui.itemized_list(
            page,
            title='We use this to',
            items=[
                'Provide a support page for your users to help contact you',
                'Determine which versions of Review Board are actively in use',
                'Track how upgrades affect numbers of bug reports and '
                'support incidents',
            ])

        ui.text(
            page,
            "You can choose to turn this on or off at any time in Support "
            "Settings in Review Board's Administration UI.")

        ui.text(page, 'See our privacy policy:')
        ui.urllink(page, 'https://www.beanbaginc.com/privacy/')

        ui.prompt_input(page,
                        'Allow us to collect support data?',
                        default=None,
                        yes_no=True,
                        save_obj=site,
                        save_var='send_support_usage_stats')

    def show_install_status(self):
        """Show the install status page."""
        site = self.site

        page = ui.page('Installing the site...', allow_back=False)
        ui.step(page, 'Building site directories',
                site.rebuild_site_directory)
        ui.step(page, 'Building site configuration files',
                site.generate_config_files)
        ui.step(page, 'Creating database',
                site.update_database)
        ui.step(page, 'Creating administrator account',
                site.create_admin_user)
        ui.step(page, 'Saving site settings',
                self.save_settings)
        ui.step(page, 'Setting up support',
                self.setup_support)
        ui.step(page, 'Finishing the install',
                self.finalize_install)

    def show_finished(self):
        """Show the finished page."""
        site = self.site

        page = ui.page('The site has been installed', allow_back=False)
        ui.text(
            page,
            'The site has been installed in %s' % site.abs_install_dir)
        ui.text(
            page,
            'Sample configuration files for web servers and cron are '
            'available in the conf/ directory.')
        ui.text(
            page,
            'You need to modify the ownership of the following directories '
            'and their contents to be owned by the web server:')

        ui.itemized_list(page, None, [
            os.path.join(site.abs_install_dir, 'htdocs', 'media', 'uploaded'),
            os.path.join(site.abs_install_dir, 'htdocs', 'media', 'ext'),
            os.path.join(site.abs_install_dir, 'htdocs', 'static', 'ext'),
            os.path.join(site.abs_install_dir, 'data'),
        ])

        ui.text(page, 'For more information, visit:')
        ui.urllink(page,
                   '%sadmin/installation/creating-sites/' % get_manual_url())

    def show_get_more(self):
        """Show the "Get More out of Review Board" page."""
        from reviewboard.admin.support import get_install_key

        page = ui.page('Get more out of Review Board', allow_back=False)
        ui.text(
            page,
            'To enable PDF document review, code review reports, enhanced '
            'scalability, and support for GitHub Enterprise, Bitbucket '
            'Server, AWS CodeCommit, Team Foundation Server, and more, '
            'install Power Pack at:')
        ui.urllink(page, 'https://www.reviewboard.org/powerpack/')

        ui.text(
            page,
            'Your install key for Power Pack is: %s'
            % get_install_key())

        ui.text(
            page,
            'Support contracts for Review Board are also available:')
        ui.urllink(page, SUPPORT_URL)

    def save_settings(self):
        """Save some settings in the database."""
        from django.contrib.sites.models import Site
        from djblets.siteconfig.models import SiteConfiguration

        site = self.site

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
        site = self.site

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

    help_text = (
        'upgrade an existing site to Review Board %s' % get_version_string()
    )

    description_text = (
        'This will upgrade your existing Review Board site directory, '
        'applying any changes needed to your database, configuration, and '
        'media files to move to a newer version of Review Board.\n'
        '\n'
        'An upgrade is required any time the Review Board software has been '
        'upgraded. Please note that an upgrade may take some time.'
    )

    requires_site_arg = False

    def add_options(self, parser):
        """Add any command-specific options to the parser.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for this subcommand.
        """
        parser.add_argument(
            '--copy-media',
            action='store_true',
            dest='copy_media',
            default=is_windows,
            help='copy media files instead of symlinking')
        parser.add_argument(
            '--no-db-upgrade',
            action='store_false',
            dest='upgrade_db',
            default=True,
            help="don't upgrade the database")

        if not is_windows:
            parser.add_argument(
                '--all-sites',
                action='store_true',
                dest='all_sites',
                default=False,
                help='Upgrade all installed sites')
            parser.add_argument(
                '--sitelist',
                default=SITELIST_FILE_UNIX,
                help='the path to a file storing a list of installed sites')

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

        return list(sorted(site_paths))

    def run(self, site, options):
        """Run the command.

        Args:
            site (Site):
                The site to operate on.

            options (argparse.Namespace):
                The parsed options for the command.
        """
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

    help_text = 'run a management command on the site'

    description_text = (
        'This runs a site management command on your Review Board site.\n'
        '\n'
        'Management commands are generally used to perform administrative '
        'tasks (such as changing a password or generating a search index), '
        'and can be provided by Review Board, Django, any enabled '
        'extensions, or custom commands placed in your site directory\'s '
        '"commands" directory.\n'
        '\n'
        'Common commands include:\n'
        '\n'
        '%(commands)s\n'
        '\n'
        'You can pass --help to any command to see usage information.\n'
        '\n'
        'Use "list-commands" to see the full list of available commands. '
        'Note that commands not listed above may not be suitable for '
        'production, even if shown in "list-commands".'
    )

    common_commands = {
        'Configuration': {
            'get-siteconfig': (
                'Retrieve the value for a configuration key.'
            ),
            'list-siteconfig': (
                'Display the configuration for Review Board.'
            ),
            'resolve-check': 'Resolve a manual setup check.',
            'set-siteconfig': 'Set the value for a configuration key.',
        },
        'Data': {
            'condensediffs': (
                'Upgrade diff storage and condense the diffs in the database. '
                'This can reduce database size when upgrading Review Board.'
            ),
            'import-ssh-keys': (
                "Import the host's SSH keys into the database, for shared "
                "SSH storage. This requires Power Pack."
            ),
        },
        'Debugging': {
            'dbshell': (
                'Open a database shell using your standard database '
                'tools (e.g., mysql or psql).'
            ),
            'shell': (
                'Open a Python shell in the Review Board environment.'
            ),
        },
        'Extensions': {
            'enable-extension': 'Enable an extension.',
            'disable-extension': 'Disable an extension.',
            'list-extensions': (
                'List all installed and available extensions.'
            ),
        },
        'Search': {
            'clear_index': 'Clear the search index.',
            'rebuild_index': 'Rebuild the search index from scratch.',
            'update_index': 'Create or update the configured search index.',
        },
        'Users': {
            'changepassword': 'Change the password for a user.',
            'createsuperuser': 'Create a new Review Board administrator.',
        },
    }

    def add_options(self, parser):
        """Add any command-specific options to the parser.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for this subcommand.
        """
        parser.description = self.description_text % {
            'commands': self._get_commands_help(),
        }

        parser.add_argument(
            'manage_command',
            metavar='<command> <args>',
            nargs=argparse.PARSER,
            help='the management command to run')

    def run(self, site, options):
        """Run the command.

        Args:
            site (Site):
                The site to operate on.

            options (argparse.Namespace, unused):
                The parsed options for the command.
        """
        site.setup_settings()

        from reviewboard import initialize
        initialize()

        manage_command = options.manage_command[0]
        manage_args = options.manage_command[1:]

        if manage_command == 'list-commands':
            manage_command = 'help'

        if manage_args and manage_args[0] == '--':
            # Prior to 4.0, users had to add a standalone "--" argument before
            # any management commands. Since this is no longer required from
            # 4.0 onward, this must be removed.
            manage_args = manage_args[1:]

        site.run_manage_command(manage_command, manage_args)

        sys.exit(0)

    def _get_commands_help(self):
        """Return help text for common commands.

        Returns:
            unicode:
            The help text.
        """
        commands_help = []
        common_commands = self.common_commands

        # This mirrors the indentation default for HelpFormatter.
        initial_indent_len = RBSiteHelpFormatter.indent_len

        indent_len = initial_indent_len + max(
            len(command_name)
            for topic_commands in six.itervalues(common_commands)
            for command_name in six.iterkeys(topic_commands)
        )

        initial_indent = ' ' * initial_indent_len
        subsequent_indent = '    %s' % (' ' * indent_len)
        wrap_width = get_console().term_width - (2 * initial_indent_len)

        for topic, topic_commands in sorted(six.iteritems(common_commands),
                                            key=lambda pair: pair[0]):
            commands_help.append('%s%s:' % (initial_indent, topic))

            for name, help_text in sorted(six.iteritems(topic_commands),
                                          key=lambda pair: pair[0]):
                commands_help.append(textwrap.fill(
                    help_text,
                    initial_indent='%s%s' % (initial_indent * 2,
                                             name.ljust(indent_len)),
                    subsequent_indent=subsequent_indent,
                    width=wrap_width))

            commands_help.append('')

        return '\n'.join(commands_help)


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
        dict:
        A dictionary containing the following keys:

        ``command`` (:py:class:`BaseCommand`):
            An instance of the command being run.

        ``options`` (:py:class:`argparse.Namespace`):
            The options derived from the parsed arguments.

        ``site_paths`` (list of unicode):
            The list of site paths being operated on.

    Raises:
        CommandError:
            Option parsing or handling for the command failed.
    """
    parser = argparse.ArgumentParser(
        prog='rb-site',
        formatter_class=RBSiteHelpFormatter,
        description=(
            'rb-site helps create, upgrade, and manage Review Board '
            'installations (or "sites"). A site is located on the local '
            'file system, identified as a directory, which you\'ll pass to '
            'all rb-site commands.\n'
            '\n'
            'To learn more about setting up your Review Board site, read the '
            'administration documentation at %sadmin/'
            % get_manual_url()
        ))

    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        dest='debug',
        default=DEBUG,
        help='display debug output')
    parser.add_argument(
        '--version',
        action=RBSiteVersionAction)
    parser.add_argument(
        '--no-color',
        action='store_false',
        dest='allow_term_color',
        default=True,
        help='disable color output in the terminal')
    parser.add_argument(
        '--noinput',
        action='store_true',
        default=False,
        help='run non-interactively using configuration provided in '
             'command-line options')

    sorted_commands = list(COMMANDS.keys())
    sorted_commands.sort()

    subparsers = parser.add_subparsers(
        help='the site command to run.',
        description='To get additional help for these commands, run: '
                    'rb-site <command> --help')

    for cmd_name in sorted_commands:
        command = COMMANDS[cmd_name]

        subparser = subparsers.add_parser(
            cmd_name,
            formatter_class=command.help_formatter_cls,
            prog='%s %s' % (parser.prog, cmd_name),
            description=command.description_text,
            help=command.help_text)

        if command.requires_site_arg:
            site_path_nargs = 1
        else:
            site_path_nargs = '?'

        subparser.add_argument(
            'site_path',
            metavar='<site-path>',
            nargs=site_path_nargs,
            help='the path to the Review Board site directory')
        subparser.set_defaults(command=command)

        command.add_options(subparser)

    if len(args) == 0:
        parser.print_help()
        return None

    options = parser.parse_args(args)
    command = options.command

    site_paths = command.get_site_paths(options)
    validate_site_paths(site_paths,
                        require_exists=command.require_site_paths_exist)

    return {
        'command': command,
        'options': options,
        'site_paths': site_paths,
    }


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


def setup_rbsite():
    """Set up rb-site's console and logging."""
    global ui

    # Ensure we import djblets.log for it to monkey-patch the logging module.
    import_module('djblets.log')

    logging.basicConfig(level=logging.INFO)

    init_console(default_text_padding=2)
    ui = ConsoleUI()


def main():
    """Main application handler.

    This will set up rb-site for operation on the command line, parse any
    command line options, and invoke the handler for the requested command.
    """
    setup_rbsite()

    try:
        parsed_options = parse_options(sys.argv[1:])

        if not parsed_options:
            sys.exit(1)

        command = parsed_options['command']
        options = parsed_options['options']

        get_console().allow_color = options.allow_term_color

        for install_dir in parsed_options['site_paths']:
            site = Site(install_dir, options)

            os.environ[str('HOME')] = force_str(
                os.path.join(site.install_dir, 'data'))

            command.run(site, options)
    except CommandError as e:
        ui.error(six.text_type(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
