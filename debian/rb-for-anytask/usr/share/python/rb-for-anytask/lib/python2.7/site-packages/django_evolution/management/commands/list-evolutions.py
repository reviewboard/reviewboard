from django.core.management.base import BaseCommand
from django.db.models import get_apps

from django_evolution.models import Evolution


class Command(BaseCommand):
    """Lists the applied evolutions for one or more apps."""
    def handle(self, *app_labels, **options):
        if not app_labels:
            app_labels = [app.__name__.split('.')[-2] for app in get_apps()]

        for app_label in app_labels:
            evolutions = list(Evolution.objects.filter(app_label=app_label))

            if evolutions:
                print "Applied evolutions for '%s':" % app_label

                for evolution in evolutions:
                    print '    %s' % evolution.label

                print
