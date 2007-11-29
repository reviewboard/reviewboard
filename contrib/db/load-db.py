#!/usr/bin/env python
#
# Database load script
#
# This loads a JSON dump of the database into ReviewBoard. It first resets
# the database to ensure there are no duplicate entries.

import os
import re
import sys

sys.path.append(os.getcwd())

try:
    import settings
except ImportError:
    sys.stderr.write(("Error: Can't find the file 'settings.py' in the " +
                      "directory containing %r. Make sure you're running " +
                      "from the root reviewboard directory.") % __file__)
    sys.exit(1)


# This must be done before we import any models
from django.core.management import setup_environ
setup_environ(settings)

from django import db
from django.core import serializers
from django.db import transaction

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

if confirm != 'yes':
    sys.exit(0)

os.system("./manage.py reset --noinput accounts reviews diffviewer scmtools")

transaction_setup = False

try:
    f = open(filename, 'r')
    line = f.readline()

    if line.startswith("#"):
        m = re.match("^# dbdump v(\d+) - (\d+) objects$", line)
        if not m:
            sys.stderr.write("Unknown dump format\n")
            sys.exit(1)

        version = int(m.group(1))
        totalobjs = int(m.group(2))
        i = 0
        prev_pct = -1

        if version != 1:
            sys.stderr.write("Unknown dump version\n")
            sys.exit(1)

        transaction.commit_unless_managed()
        transaction.enter_transaction_management()
        transaction.managed(True)
        transaction_setup = True

        print "Importing new style dump format (v%s)" % version
        for line in f.xreadlines():
            if line[0] == "{":
                for obj in serializers.deserialize("json", "[%s]" % line):
                    obj.save()
            elif line[0] != "#":
                sys.stderr.write("Junk data on line %s" % i)

            db.reset_queries()

            i += 1
            pct = (i * 100 / totalobjs)
            if pct != prev_pct:
                sys.stdout.write("  [%s%%]\r" % pct)
                sys.stdout.flush()
                prev_pct = pct

        f.close()

        transaction.commit()
        transaction.leave_transaction_management()
    else:
        # Legacy dumpdata output. Try loading it directly.
        print "Importing old style dump format. This may take a while."
        f.close()
        os.system("./manage.py loaddata %s" % filename)
except Exception, e:
    f.close()
    sys.stderr.write("Problem installing '%s': %s\n" % (filename, str(e)))
    sys.exit(1)

    if transaction_setup:
        transaction.rollback()
        transaction.leave_transaction_management()

print
print "Done."
