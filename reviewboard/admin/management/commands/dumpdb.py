import sys

from django.core import serializers
from django.core.management.base import NoArgsCommand
from django.db.models import get_apps, get_models


class Command(NoArgsCommand):
    help = 'Dump a common serialized version of the database to stdout.'

    def handle_noargs(self, **options):
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

        sys.stderr.write("Dump the database. This may take a while...\n")

        print "# dbdump v1 - %s objects" % totalobjs

        for model in models:
            count = model.objects.count()
            j = 0

            while j < count:
                for obj in model.objects.all()[j:j+OBJECT_LIMIT].iterator():
                    value = serializer.serialize([obj])

                    if value != "[]":
                        print value[1:-1] # Skip the "[" and "]"

                    i += 1
                    pct = i * 100 / totalobjs
                    if pct != prev_pct:
                        sys.stderr.write("  [%s%%]\r" % pct)
                        sys.stderr.flush()
                        prev_pct = pct

                j += OBJECT_LIMIT

        sys.stderr.write("\nDone.\n")
