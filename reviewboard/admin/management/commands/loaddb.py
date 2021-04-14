from __future__ import unicode_literals

import importlib
import os
import re
import textwrap

from django import db
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import get_apps
from django.utils.six.moves import input


class Command(BaseCommand):
    """Management command to load data into the database."""

    help = (
        "[Deprecated] Loads data formatted by dumpdb, for migration across "
        "types of databases.\n"
        "\n"
        "This will not be available in newer versions of Review Board, and "
        "is not compatible with production installs. Please use your "
        "database's native tools instead, or contact support@beanbaginc.com "
        "for alternative solutions."
    )

    def handle(self, *args, **options):
        """Handle the command."""
        if len(args) != 1:
            raise CommandError("You must specify a filename on the command "
                               "line.")

        filename = args[0]

        if not os.path.exists(filename):
            raise CommandError("%s does not exist." % filename)

        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            "dumpdb and loaddb are considered deprecated, and aren't meant "
            "for production installs. We recommend using your database's "
            "native SQL dumping and loading tools instead.\n",
            initial_indent='NOTE: ',
            subsequent_indent='      '))
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            'This will wipe out your existing database prior to loading. It '
            'is highly recommended that you have a full SQL database dump in '
            'case things go wrong.'))
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            "You should only use this if you're migrating from one type "
            "of database to another, with the same version of Review Board "
            "on each, in a development environment. Otherwise, use your "
            "native database tools, or contact support@beanbaginc.com to "
            "learn about alternative approaches."))
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            'Are you sure you want to continue?'))
        self.stderr.write('\n')
        self.stderr.write("Type 'yes' to continue, or 'no' to cancel.")

        confirm = input('> ')

        if confirm != 'yes':
            return

        try:
            importlib.import_module('django_reset')
        except ImportError:
            raise CommandError("Before using this command, you need to "
                               "install the 'django-reset' package")

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
            if transaction_setup:
                transaction.rollback()
                transaction.leave_transaction_management()

            raise CommandError("Problem installing '%s': %s\n" % (filename, e))

        self.stdout.write('\nDone.')
