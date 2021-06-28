#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, os.getcwd())

    import django
    import djblets
    import reviewboard

    print('Review Board %s' % reviewboard.get_version_string())
    print('Djblets %s' % djblets.get_version_string())
    print('Django %s' % django.__version__)
    print('Python %s.%s.%s' % sys.version_info[:3])
    print()

    # We're just wrapping the manage script. Both that script and the test
    # runner are expecting sys.argv to be set. Fake it here so we don't have
    # to shell out to another process just to get a proper set of arguments.
    sys.argv = [sys.argv[0], 'test', '--'] + sys.argv[1:]

    os.environ[str('RB_RUNNING_TESTS')] = str('1')
    os.environ[str('RBSSH_STORAGE_BACKEND')] = \
        str('reviewboard.ssh.storage.FileSSHStorage')

    from reviewboard.manage import run as run_manage
    run_manage()
