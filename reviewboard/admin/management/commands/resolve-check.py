from __future__ import unicode_literals

import sys

from django.core.management.base import BaseCommand, CommandError
from djblets.siteconfig.models import SiteConfiguration


class Command(BaseCommand):
    help = 'Resolves a manual update check'

    def handle(self, *args, **options):
        if len(args) != 1:
            self.stderr.write('You must specify a check to resolve')
            sys.exit(1)

        check_name = args[0]

        siteconfig = SiteConfiguration.objects.get_current()
        updates = siteconfig.settings.get('manual-updates', {})

        if check_name not in updates:
            raise CommandError("Couldn't find manual update check '%s'\n" %
                               check_name)

        if updates[check_name]:
            self.stdout.write("Already resolved manual update check '%s'" %
                              check_name)
        else:
            updates[check_name] = True
            siteconfig.save()

            self.stdout.write("Resolved manual update check '%s'" % check_name)
