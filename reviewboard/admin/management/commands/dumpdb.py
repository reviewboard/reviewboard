from __future__ import unicode_literals

import textwrap

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_apps, get_models
from django.utils.six.moves import input

from reviewboard import VERSION


class Command(BaseCommand):
    """Management command to dump data from the database."""

    help = (
        "[Deprecated] Dump a common serialized version of the database to "
        "a file.\n"
        "\n"
        "This is not compatible with newer versions of Review Board, or "
        "production installs. Please use your database's native tools "
        "instead, or contact support@beanbaginc.com for alternative "
        "solutions."
    )

    def handle(self, *args, **options):
        """Handle the command."""
        if len(args) != 1:
            raise CommandError(
                'You must specify a filename on the command line.')

        filename = args[0]

        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            "dumpdb and loaddb are considered deprecated, and aren't meant "
            "for production installs. We recommend using your database's "
            "native SQL dumping and loading tools instead.\n"))
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            'This dump file can only be loaded by Review Board %s.%s.x, on a '
            'development install.'
            % VERSION[:2]))
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            'If you need to move between types of databases, contact '
            'support@beanbaginc.com to learn about alternatives.\n'))
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            "Are you sure you want to continue?"))
        self.stderr.write('\n')
        self.stderr.write("Type 'yes' to continue, or 'no' to cancel.")

        confirm = input('> ')

        if confirm != 'yes':
            return

        models = []

        for app in get_apps():
            models.extend(get_models(app))

        OBJECT_LIMIT = 150

        serializer = serializers.get_serializer("json")()

        totalobjs = 0
        for model in models:
            totalobjs += model.objects.count()

        prev_pct = -1
        i = 0

        self.stdout.write("Dump the database. This may take a while...\n")

        with open(filename, 'w') as fp:
            fp.write('# dbdump v1 - %s objects\n' % totalobjs)

            for model in models:
                count = model.objects.count()
                j = 0

                while j < count:
                    models_iter = (
                        model.objects.all()
                        [j:j + OBJECT_LIMIT]
                        .iterator()
                    )

                    for obj in models_iter:
                        value = serializer.serialize([obj])

                        if value != '[]':
                            fp.write(value[1:-1])  # Skip the "[" and "]"
                            fp.write('\n')

                        i += 1
                        pct = i * 100 / totalobjs

                        if pct != prev_pct:
                            self.stdout.write('  [%s%%]\r' % pct)
                            self.stdout.flush()
                            prev_pct = pct

                    j += OBJECT_LIMIT

        self.stdout.write("\nDone.\n")
