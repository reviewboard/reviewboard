#!/usr/bin/env python
"""Prepare a Review Board tree for development."""

from __future__ import print_function, unicode_literals

import argparse
import os
import platform
import stat
import subprocess
import sys
from random import choice

# This is one of the few things in Django that is safe to import here.
from django.utils import six


FAQ_URL = \
    'https://notion.so/reviewboard/FAQ-6a19618dd534476ea844cba9a3576868'


# Our git post-checkout hook script which ensures stale .pyc files are not left
# around when switching branches, especially when switching between releases.
_POST_CHECKOUT = (
    "#!/bin/sh\n"
    "find . -iname '*.pyc' -delete\n"
)


#: The console instance to use for all output.
#:
#: Type:
#:     reviewboard.cmdline.utils.console.Console
console = None


class SiteOptions(object):
    """The site options."""

    copy_media = platform.system() == "Windows"


def create_settings(options):
    """Create a settings_local.py file if it doesn't exist.

    Args:
        options (argparse.Namespace):
            The options parsed from :py:mod:`argparse`.
    """
    if not os.path.exists('settings_local.py'):
        console.header('Creating your settings_local.py')

        console.print(
            'This settings_local.py will be placed in the current directory. '
            'It can be modified to point to a different database, or to '
            'enable custom Django settings.')

        # TODO: Use an actual templating system.
        src_path = os.path.join('contrib', 'conf', 'settings_local.py.tmpl')

        # XXX: Once we switch to Python 2.7+, use the multiple form of 'with'
        in_fp = open(src_path, 'r')
        out_fp = open('settings_local.py', 'w')

        for line in in_fp:
            if line.startswith('SECRET_KEY = '):
                secret_key = ''.join([
                    choice(
                        'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
                    for i in range(50)
                ])

                out_fp.write('SECRET_KEY = "%s"\n' % secret_key)
            elif line.strip().startswith("'ENGINE': "):
                out_fp.write("        'ENGINE': 'django.db.backends.%s',\n" %
                             options.db_type)
            elif line.strip().startswith("'NAME': "):
                if options.db_type == 'sqlite3':
                    if options.db_name is not None:
                        name = os.path.abspath(options.db_name)
                        out_fp.write("        'NAME': '%s',\n" % name)
                    else:
                        out_fp.write("        'NAME': os.path.join(ROOT_PATH,"
                                     " 'reviewboard-%d.%d.db' % (VERSION[0], "
                                     "VERSION[1])),\n")
                else:
                    name = options.db_name
                    out_fp.write("        'NAME': '%s',\n" % name)
            elif line.strip().startswith("'USER': "):
                out_fp.write("        'USER': '%s',\n" % options.db_user)
            elif line.strip().startswith("'PASSWORD': "):
                out_fp.write("        'PASSWORD': '%s',\n"
                             % options.db_password)
            else:
                out_fp.write(line)

        in_fp.close()
        out_fp.close()


def install_git_hooks():
    """Install a post-checkout hook to delete pyc files."""
    console.header('Setting up your Git tree')
    console.print(
        'Your Git tree will be set up with a default post-checkout hook '
        'that clears any compiled Python files when switching branches.')

    try:
        gitdir = (
            subprocess.check_output(['git', 'rev-parse', '--git-common-dir'])
            .decode('utf-8')
            .strip()
        )
    except subprocess.CalledProcessError:
        console.error('Could not determine git directory. Are you in a '
                      'checkout?')
        return

    hook_path = os.path.join(gitdir, 'hooks', 'post-checkout')

    exc_mask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

    try:
        statinfo = os.stat(hook_path)
    except OSError:
        # The file does not exist.
        statinfo = None

    if statinfo:
        # The file exists. We need to determine if we should write to it.

        if statinfo.st_size != 0 and statinfo.st_mode & exc_mask:
            # The file is non-empty and executable, which means this *isn't*
            # the default hook that git installs when you create a new
            # repository.
            #
            # Let's check the hook's contents to see if its a hook we installed
            # previously or if the user has already set up their own hook.
            with open(hook_path, 'r') as f:
                contents = f.read()

            if contents != _POST_CHECKOUT:
                console.error(
                    'The hook "%(hook_path)s" already exists and differs '
                    'from the hook we would install. The existing hook '
                    'will be left alone.'
                    '\n'
                    'If you want this hook installed, please add the '
                    'following to that file:'
                    '\n'
                    '%(script)s'
                    % {
                        'hook_path': hook_path,
                        'script': '\n'.join(_POST_CHECKOUT.split('\n')[1:]),
                    })

                return

    # At this point we know we are safe to write to the hook file. This is
    # because one of the following is true:
    #
    # 1. The hook file does not exist.
    # 2. The hook file exists but is empty.
    # 3. The hook file exists but is non-executable (i.e., it contains a
    #    sample git hook).
    with open(hook_path, 'w') as f:
        f.write(_POST_CHECKOUT)
        os.fchmod(f.fileno(), 0o740)

    console.print('The post-checkout hook has been installed.')


def install_media(site):
    """Install static media.

    Args:
        site (reviewboard.cmdline.rbsite.Site):
            The site to install media for.

            This will be the site corresponding to the current working
            directory.
    """
    from pipeline.collector import default_collector
    from pipeline.packager import Packager

    console.header('Setting up static media files')

    media_path = os.path.join('htdocs', 'media')
    uploaded_path = os.path.join(site.install_dir, media_path, 'uploaded')
    ext_media_path = os.path.join(site.install_dir, media_path, 'ext')

    site.mkdir(uploaded_path)
    site.mkdir(os.path.join(uploaded_path, 'images'))
    site.mkdir(ext_media_path)

    # Run Pipeline on all the files, so we can prime the static media
    # directory. This cuts down on the very long initial load times, in
    # exchange for a somewhat long up-front time. Pipeline will at least
    # compile files within each bundle in parallel.
    default_collector.collect()

    packager = Packager()

    package_types = (
        ('css', 'CSS'),
        ('js', 'JavaScript'),
    )

    total_packages = sum(
        len(packager.packages[package_type])
        for package_type, package_type_desc in package_types
    )

    i = 1

    for package_type, package_type_desc in package_types:
        packages = packager.packages[package_type]

        for package_name, package in sorted(six.iteritems(packages),
                                            key=lambda pair: pair[0]):
            console.progress_step(
                'Compiling %s bundle %s' % (package_type_desc,
                                            package.output_filename),
                step_num=i,
                total_steps=total_packages,
                func=lambda: packager.compile(package.paths))

            i += 1


def install_dependencies(options):
    """Install dependencies via setup.py and pip (and therefore npm).

    Args:
        options (argparse.Namespace):
            The parsed command line arguments.
    """
    # We can't use console.print() or console.header() here, since we're
    # running before we know we even have Django installed.
    print('Bootstrapping: Installing the Review Board package and '
          'dependencies..')

    cmdline = [sys.executable, 'setup.py', '-q', 'develop']

    if options.all_pyvers:
        cmdline.append('--all-pyvers')

    os.system(subprocess.list2cmdline(cmdline))


def create_superuser(site):
    """Create an initial superuser for the site.

    This will ask for a username, password, and e-mail address for the
    initial superuser account.

    If a superuser already exists (due to re-running this script on an
    existing database), it will be displayed for reference, and the user
    will be instructed on how to create a new one.

    Args:
        site (reviewboard.cmdline.rbsite.Site):
            The site to create the superuser on.
    """
    from django.contrib.auth.management import get_default_username
    from django.contrib.auth.models import User

    console.header('Set up an administrator account')

    admins = list(
        User.objects.filter(is_superuser=True)
        .values_list('username', flat=True)
    )

    if admins:
        console.print(
            'Existing admin account(s) were found: %(admins)s'
            '\n'
            'To create a new one, run:'
            % {
                'admins': ', '.join(admins),
            })
        console.print()
        console.print(
            '    ./reviewboard/manage.py createsuperuser',
            wrap=False)
    else:
        console.print("Now you'll need to set up a superuser (an admin "
                      "account). This will be used to log in and configure "
                      "Review Board.")

        site.admin_user = console.prompt_input(
            'Username',
            default=get_default_username() or 'admin')
        site.admin_password = console.prompt_input(
            'Password',
            prompt_type=console.PROMPT_TYPE_PASSWORD)

        while True:
            confirmed_password = console.prompt_input(
                'Confirm Password',
                prompt_type=console.PROMPT_TYPE_PASSWORD)

            if confirmed_password == site.admin_password:
                break

            console.error('Passwords must match.')

        site.admin_email = console.prompt_input('E-Mail Address')

        site.create_admin_user()


def parse_options(args):
    """Parse the command-line arguments and return the results.

    Args:
        args (list of bytes):
            The arguments to parse.

    Returns:
        argparse.Namespace:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        'Prepare a Review Board tree for development.',
        usage='%(prog)s [options]')

    parser.add_argument(
        '--all-pyvers',
        action='store_true',
        default=False,
        help=(
            'Set up the package using all supported versions of Python. '
            'This requires a multi-Python virtualenv supporting all the '
            'versions required.'
        ))

    parser.add_argument(
        '--only',
        action='store_true',
        dest='only',
        help=(
            'Disable all feature by default (implying --no-<feature> for each '
            'feature) unless explicitly specified (e.g., "--only --media '
            '--deps" to only install media and dependencies).'
        ))

    parser.add_argument(
        '--media',
        action='store_true',
        dest='install_media',
        default=None,
        help='Install media files when --only specified')
    parser.add_argument(
        '--no-media',
        action='store_false',
        dest='install_media',
        help="Don't install media files")

    parser.add_argument(
        '--db',
        action='store_true',
        dest='sync_db',
        default=None,
        help='Synchronize database when --only specified')
    parser.add_argument(
        '--no-db',
        action='store_false',
        dest='sync_db',
        help="Don't synchronize the database")

    parser.add_argument(
        '--deps',
        action='store_true',
        dest='install_deps',
        default=None,
        help='Install dependencies when --only specified')
    parser.add_argument(
        '--no-deps',
        action='store_false',
        dest='install_deps',
        help="Don't install dependencies")

    parser.add_argument(
        '--hooks',
        action='store_true',
        dest='install_hooks',
        default=None,
        help='Install repository hooks when --only specified')
    parser.add_argument(
        '--no-hooks',
        action='store_false',
        dest='install_hooks',
        help="Don't install repository hooks")

    parser.add_argument(
        '--database-type',
        dest='db_type',
        default='sqlite3',
        help="Database type (postgresql, mysql, sqlite3)")
    parser.add_argument(
        '--database-name',
        dest='db_name',
        default=None,
        help="Database name (or path, for sqlite3)")
    parser.add_argument(
        '--database-user',
        dest='db_user',
        default='',
        help="Database user")
    parser.add_argument(
        '--database-password',
        dest='db_password',
        default='',
        help="Database password")

    options = parser.parse_args(args)

    # Post-process the options so that anything that didn't get explicitly set
    # will have a boolean value.
    for attr in ('install_media', 'install_hooks', 'install_deps', 'sync_db'):
        if getattr(options, attr) is None:
            setattr(options, attr, not options.only)

    return options


def main():
    """The entry point of the prepare-dev script."""
    global console

    if not os.path.exists(os.path.join("reviewboard", "manage.py")):
        sys.stderr.write("This must be run from the top-level Review Board "
                         "directory\n")
        sys.exit(1)

    options = parse_options(sys.argv[1:])

    if options.install_deps:
        install_dependencies(options)

    # Insert the current directory first in the module path so we find the
    # correct reviewboard package.
    sys.path.insert(0, os.getcwd())

    from reviewboard.cmdline import rbsite
    from reviewboard.cmdline.rbsite import Site, setup_rbsite
    from reviewboard.cmdline.utils.console import get_console

    setup_rbsite()

    console = get_console()
    console.allow_color = True

    console.header('Welcome to Review Board!',
                   leading_newlines=False)
    console.print(
        "Let's get your development environment set up and ready to go. This "
        "will set up your settings_local.py file, your database, initial "
        "static media files, and prepare an administrator account."
        "\n"
        "If you have any issues, first see if it's answered in our FAQ:"
        "\n"
        "%(faq_url)s"
        "\n"
        "If you're a student working on Review Board, you can also get help "
        "from your mentors. If you're a contributor, please contact:"
        "\n"
        "reviewboard-dev@googlegroups.com"
        % {
            'faq_url': FAQ_URL,
        })

    # Re-use the Site class, since it has some useful functions.
    site_path = os.path.abspath('reviewboard')
    site = Site(site_path, SiteOptions)

    create_settings(options)

    if options.install_hooks:
        install_git_hooks()

    try:
        if options.sync_db:
            site.abs_install_dir = os.getcwd()

            console.header('Setting up the Review Board database')
            site.setup_settings()
            site.update_database(allow_input=True,
                                 report_progress=True)
    except KeyboardInterrupt:
        console.error(
            'The process was canceled in the middle of creating the database, '
            'which can result in a corrupted setup. Please remove the '
            'database file and run:')
        console.error(
            '    ./reviewboard/manage.py createdb',
            wrap=False)
        return

    if options.install_media:
        install_media(site)

    create_superuser(site)

    console.header('Your Review Board tree is ready for development!')
    console.print('You can now run your development server by running:')
    console.print()
    console.print('    ./contrib/internal/devserver.py',
                  wrap=False)
    console.print()


if __name__ == "__main__":
    main()
