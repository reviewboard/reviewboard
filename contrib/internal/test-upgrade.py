#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import shutil
import subprocess
import sys
import tempfile
from optparse import OptionParser


options = None


def die(msg):
    sys.stderr.write(msg)
    sys.exit(1)


def clone_git_tree(git_dir):
    new_git_dir = tempfile.mkdtemp(prefix='reviewboard-test-upgrade.')

    os.chdir(new_git_dir)
    execute(['git', 'clone', git_dir, '.'])

    return new_git_dir


def execute(cmdline, return_errcode=False, show_output=True):
    if isinstance(cmdline, list):
        print(">>> %s" % subprocess.list2cmdline(cmdline))
    else:
        print(">>> %s" % cmdline)

    p = subprocess.Popen(cmdline,
                         shell=False,
                         stdout=subprocess.PIPE)

    s = ''

    for data in p.stdout.readlines():
        s += data

        if show_output:
            sys.stdout.write(data)

    rc = p.wait()

    if return_errcode:
        return s, rc

    if rc != 0:
        die("!!! Error invoking command.")

    return s


def run_python(cmdline, *args, **kwargs):
    return execute([sys.executable] + cmdline, *args, **kwargs)


def clean_pyc():
    for root, dirs, files in os.walk(os.getcwd()):
        for filename in files:
            if filename.endswith('.pyc'):
                os.unlink(os.path.join(root, filename))


def parse_options(args):
    global options

    parser = OptionParser(usage='%prog [options]')
    parser.add_option('--database-type', dest='db_type',
                      default='sqlite3',
                      help="Database type (postgresql, mysql, sqlite3)")
    parser.add_option('--database-name', dest='db_name',
                      default='reviewboard.db',
                      help="Database name (or path, for sqlite3)")
    parser.add_option('--database-user', dest='db_user',
                      default='',
                      help="Database user")
    parser.add_option('--database-password', dest='db_password',
                      default='',
                      help="Database password")

    options, args = parser.parse_args(args)

    return args


def main():
    if len(sys.argv) <= 2:
        die('Usage: test-upgrade.py branch1 branch2 [branchN...]\n')

    if not os.path.exists("setup.py"):
        die("This must be run from the root of the Review Board tree.\n")

    branches = parse_options(sys.argv[1:])

    # Validate the branches
    for branch in branches:
        errcode = execute(['git', 'rev-parse', branch],
                          return_errcode=True, show_output=False)[1]

        if errcode != 0:
            die('Unable to resolve branch %s\n' % branch)

    # Clone the tree
    cur_dir = os.getcwd()
    git_dir = clone_git_tree(cur_dir)

    print('Review Board cloned to %s' % git_dir)

    # Prepare for a dev installation
    run_python(['./contrib/internal/prepare-dev.py',
                '--no-media',
                '--no-db',
                '--database-type=%s' % options.db_type,
                '--database-name=%s' % options.db_name,
                '--database-user=%s' % options.db_user,
                '--database-password=%s' % options.db_password])

    for branch in branches:
        execute(['git', 'checkout', branch])
        clean_pyc()
        run_python(['./reviewboard/manage.py', 'syncdb', '--noinput'])
        run_python(['./reviewboard/manage.py', 'evolve', '--execute',
                    '--noinput'])

    os.chdir(cur_dir)
    shutil.rmtree(git_dir)

    print()
    print("***")
    print("*** Success!")
    print("***")


if __name__ == '__main__':
    main()
