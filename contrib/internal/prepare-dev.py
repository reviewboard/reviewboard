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


# Our git post-checkout hook script which ensures stale .pyc files are not left
# around when switching branches, especially when switching between releases.
_POST_CHECKOUT = (
    "#!/bin/sh\n"
    "find . -iname '*.pyc' -delete\n"
)


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
        print('Creating a settings_local.py in the current directory.')
        print('This can be modified with custom settings.')

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
    """Install a post-checkout hook to delete `pyc` files."""
    try:
        gitdir = subprocess.check_output(
            ['git', 'rev-parse', '--git-common-dir']).strip()
    except subprocess.CalledProcessError:
        sys.stderr.write(
            'Could not determine git directory. Are you in a checkout?')

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
                    rest_hook = '\n'.join(_POST_CHECKOUT.split('\n')[1:])
                    sys.stderr.write(
                        'The hook "%s" already exists and differs from the '
                        'hook we would install -- refusing to overwrite.\n\n'
                        'Please add the following lines to your hook:\n\n'
                        '%s\n'
                        % (hook_path, rest_hook))

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
        os.fchmod(f.fileno(), 0740)

    print('Installed post-checkout hook.')


def install_media(site):
    """Install static media.

    Args:
        site (reviewboard.cmdline.rbsite.Site):
            The site to install media for.

            This will be the site corresponding to the current working
            directory.
    """
    print('Rebuilding media paths...')

    media_path = os.path.join('htdocs', 'media')
    uploaded_path = os.path.join(site.install_dir, media_path, 'uploaded')
    ext_media_path = os.path.join(site.install_dir, media_path, 'ext')

    site.mkdir(uploaded_path)
    site.mkdir(os.path.join(uploaded_path, 'images'))
    site.mkdir(ext_media_path)


def install_dependencies():
    """Install dependencies via setup.py and pip (and therefore npm)."""
    os.system('%s setup.py develop' % sys.executable)


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
        'Prepare Review Board tree for development.',
        usage='%(prog)s [options]')

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
    if not os.path.exists(os.path.join("reviewboard", "manage.py")):
        sys.stderr.write("This must be run from the top-level Review Board "
                         "directory\n")
        sys.exit(1)

    options = parse_options(sys.argv[1:])

    if options.install_deps:
        install_dependencies()

    # Insert the current directory first in the module path so we find the
    # correct reviewboard package.
    sys.path.insert(0, os.getcwd())
    from reviewboard.cmdline.rbsite import Site, ConsoleUI

    import reviewboard.cmdline.rbsite
    reviewboard.cmdline.rbsite.ui = ConsoleUI()

    # Re-use the Site class, since it has some useful functions.
    site_path = os.path.abspath('reviewboard')
    site = Site(site_path, SiteOptions)

    create_settings(options)

    if options.install_hooks:
        install_git_hooks()

    if options.install_media:
        install_media(site)

    try:
        if options.sync_db:
            print('Synchronizing database...')
            site.abs_install_dir = os.getcwd()
            site.sync_database(allow_input=True)
    except KeyboardInterrupt:
        sys.stderr.write(
            'The process was canceled in the middle of creating the database, '
            'which can result in a corrupted setup. Please remove the '
            'database file and run ./reviewboard/manage.py syncdb.')
        return

    print()
    print('Your Review Board tree is ready for development.')
    print()


if __name__ == "__main__":
    main()
