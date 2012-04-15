import sys

from django.core.management.base import BaseCommand
from djblets.siteconfig.models import SiteConfiguration


class Command(BaseCommand):
    help = 'Resolves a manual update check'

    def handle(self, *args, **options):
        if len(args) != 1:
            print 'You must specify a check to resolve'
            sys.exit(1)

        check_name = args[0]

        siteconfig = SiteConfiguration.objects.get_current()
        updates = siteconfig.settings.get('manual-updates', {})

        if check_name in updates and not updates[check_name]:
            updates[check_name] = True
            siteconfig.save()

            print "Resolved manual update check '%s'" % check_name
        else:
            sys.stderr.write("Couldn't find manual update check '%s'\n" %
                             check_name)
            sys.exit(1)
