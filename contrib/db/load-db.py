#!/usr/bin/env python
#
# Database load script
#
# This loads a JSON dump of the database into ReviewBoard. It first resets
# the database to ensure there are no duplicate entries.

import os, simplejson, sys

if not os.path.exists("manage.py"):
    print "This must be run in the directory containing manage.py."
    sys.exit(1)


if len(sys.argv) != 2:
    print "You must specify a filename on the command line."
    sys.exit(1)

filename = sys.argv[1]

if not os.path.exists(filename):
    print "%s does not exist." % filename
    sys.exit(1)

confirm = raw_input("""
This will wipe out your existing database
prior to loading. It is highly recommended
that you have a full SQL database dump in case
things go wrong.

Are you sure you want to continue?"

Type 'yes' to continue, or 'no' to cancel: """)

if confirm == 'yes':
    os.system("./manage.py reset --noinput accounts reviews diffviewer scmtools")
    os.system("./manage.py loaddata %s" % filename)

    print "Done."
