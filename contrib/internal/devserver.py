#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import getopt
import os
import sys


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = "8080"


def usage():
    print("usage:  %s options" % sys.argv[0])
    print()
    print("OPTIONS:")
    print("   -h           Show this message")
    print("   -H HOST      Set server host (defaults to %s)" % DEFAULT_HOST)
    print("   -p PORT      Set server port (defaults to %s)" % DEFAULT_PORT)


def main():
    # Assign default settings
    server_host = DEFAULT_HOST
    server_port = DEFAULT_PORT

    # Do any command-line argument processing
    (opts, args) = getopt.getopt(sys.argv[1:], 'hH:p:')

    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit(1)
        elif opt == '-p':
            server_port = arg
        elif opt == '-H':
            server_host = arg
        else:
            usage()
            sys.exit(1)

    # Ensure we're at the top-level Review Board directory
    if not os.path.exists(os.path.join('reviewboard', 'manage.py')):
        sys.stderr.write('This must be run from the top-level Review Board'
                         ' directory\n')
        sys.exit(1)

    # Next, ensure settings_local.py exists where we expect it
    if not os.path.exists('settings_local.py'):
        sys.stderr.write('You must create a settings_local.py in the '
                         'top-level source \n'
                         'directory. You can use '
                         'contrib/conf/settings_local.py.tmpl\n'
                         'as a basis.\n')
        sys.exit(1)

    # Build ReviewBoard.egg-info if it doesn't already exist
    if not os.path.exists('ReviewBoard.egg-info'):
        os.system("python ./setup.py egg_info")

    # And now just boot up the server
    os.system('%s ./reviewboard/manage.py runserver %s:%s --nostatic'
              % (sys.executable, server_host, server_port))

if __name__ == "__main__":
    main()
