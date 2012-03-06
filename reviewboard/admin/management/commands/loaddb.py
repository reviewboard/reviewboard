import os
import re
import sys

from django import db
from django.core import serializers
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import get_apps


class Command(BaseCommand):
    help = 'Loads data formatted by dumpdb, for migration across types ' \
           'of databases.'

    def handle(self, *args, **options):
        if len(args) != 1:
            print "You must specify a filename on the command line."
            sys.exit(1)

        filename = args[0]

        if not os.path.exists(filename):
            print "%s does not exist." % filename
            sys.exit(1)

        confirm = raw_input("""
This will wipe out your existing database prior to loading. It is highly
recommended that you have a full SQL database dump in case things go wrong.

You should only use this if you're migrating from one type of database to
another, with the same version of Review Board on each.

Are you sure you want to continue?"

Type 'yes' to continue, or 'no' to cancel: """)

        if confirm != 'yes':
            return

        apps = [app.__name__.split('.')[-2] for app in get_apps()]

        os.system("./reviewboard/manage.py reset --noinput %s" % ' '.join(apps))

        transaction_setup = False

        try:
            f = open(filename, 'r')
            line = f.readline()

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
                    for obj in serializers.deserialize("json",
                                                       "[%s]" % line):
                        try:
                            obj.save()
                        except Exception, e:
                            sys.stderr.write("Error: %s\n" % e)
                            sys.stderr.write("Line %s: '%s'" % (i, line))
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
        except Exception, e:
            f.close()
            sys.stderr.write("Problem installing '%s': %s\n" %
                             (filename, str(e)))
            sys.exit(1)

            if transaction_setup:
                transaction.rollback()
                transaction.leave_transaction_management()

        print
        print "Done."
