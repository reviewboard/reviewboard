#!/usr/bin/env python

import getopt
import os
import sys


DEFAULT_PORT = "8080"


def usage():
    print "usage:  %s options" % sys.argv[0]
    print
    print "OPTIONS:"
    print "   -h           Show this message"
    print "   -p PORT      Set server port (defaults to %s)" % DEFAULT_PORT


def main():
    # Assign default settings
    server_port = DEFAULT_PORT

    # Do any command-line argument processing
    (opts, args) = getopt.getopt(sys.argv[1:], 'hp:')

    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit(1)
        elif opt == '-p':
            server_port = arg
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

    # Next, make sure we're in the Djblets media path
    if not os.path.exists(os.path.join('reviewboard', 'htdocs',
                                       'media', 'djblets')):
	sys.stderr.write('You must set up the Djblets media path. Create '
	                 'a symlink pointing\n'
	                 'to a development djblets/media directory and name '
	                 'it\n'
	                 'reviewboard/htdocs/media/djblets\n'
	                 '\n'
	                 'For example:\n'
	                 '$ ln -s /path/to/djblets/djblets/media '
	                 'reviewboard/htdocs/media/djblets\n')
        sys.exit(1)

    # Build ReviewBoard.egg-info if it doesn't already exist
    if not os.path.exists('ReviewBoard.egg-info'):
        os.system("./setup.py egg_info")

    # And now just boot up the server
    os.system('./reviewboard/manage.py runserver 0.0.0.0:%s'
              ' --adminmedia=reviewboard/htdocs/media/admin/'
              % server_port)

if __name__ == "__main__":
    main()
