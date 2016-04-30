from __future__ import unicode_literals

import os
import re

from django import db
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import get_apps
from django.utils.six.moves import input


class Command(BaseCommand):
    """Management command to load data into the database."""

    help = ('Loads data formatted by dumpdb, for migration across types '
            'of databases.')

    def handle(self, *args, **options):
        """Handle the command."""
        if len(args) != 1:
            raise CommandError("You must specify a filename on the command "
                               "line.")

        filename = args[0]

        if not os.path.exists(filename):
            raise CommandError("%s does not exist." % filename)

        try:
            import django_reset
        except ImportError:
            raise CommandError("Before using this command, you need to "
                               "install the 'django-reset' package")

        confirm = input("""
This will wipe out your existing database prior to loading. It is highly
recommended that you have a full SQL database dump in case things go wrong.

You should only use this if you're migrating from one type of database to
another, with the same version of Review Board on each.

Are you sure you want to continue?"

Type 'yes' to continue, or 'no' to cancel: """)

        if confirm != 'yes':
            return

        apps = [app.__name__.split('.')[-2] for app in get_apps()]

        os.system('./reviewboard/manage.py reset --noinput %s'
                  % ' '.join(apps))

        transaction_setup = False

        try:
            with open(filename, 'r') as f:
                line = f.readline()

                m = re.match("^# dbdump v(\d+) - (\d+) objects$", line)
                if not m:
                    raise CommandError("Unknown dump format\n")

                version = int(m.group(1))
                totalobjs = int(m.group(2))
                i = 0
                prev_pct = -1

                if version != 1:
                    raise CommandError("Unknown dump version\n")

                transaction.commit_unless_managed()
                transaction.enter_transaction_management()
                transaction.managed(True)
                transaction_setup = True

                self.stdout.write("Importing new style dump format (v%s)" %
                                  version)
                for line in f:
                    if line[0] == "{":
                        for obj in serializers.deserialize("json",
                                                           "[%s]" % line):
                            try:
                                obj.save()
                            except Exception as e:
                                self.stderr.write("Error: %s\n" % e)
                                self.stderr.write("Line %s: '%s'" % (i, line))
                    elif line[0] != "#":
                        self.stderr.write("Junk data on line %s" % i)

                    db.reset_queries()

                    i += 1
                    pct = (i * 100 / totalobjs)
                    if pct != prev_pct:
                        self.stdout.write("  [%s%%]\r" % pct)
                        self.stdout.flush()
                        prev_pct = pct

            transaction.commit()
            transaction.leave_transaction_management()
        except Exception as e:
            raise CommandError("Problem installing '%s': %s\n" % (filename, e))

            if transaction_setup:
                transaction.rollback()
                transaction.leave_transaction_management()

        self.stdout.write('\nDone.')
