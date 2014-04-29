from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy as _
from djblets.extensions.models import RegisteredExtension


class Command(BaseCommand):
    help = _('Lists available Review Board extensions.')

    option_list = BaseCommand.option_list + (
        make_option('--enabled',
                    action='store_true',
                    default=False,
                    dest='list_enabled',
                    help=_('List only enabled extensions')),
    )

    def handle(self, *args, **options):
        extensions = RegisteredExtension.objects.all()

        if options['list_enabled']:
            extensions = extensions.filter(enabled=True)

        for extension in extensions:
            self.stdout.write(_('* Name: %s\n') % extension.name)

            if extension.enabled:
                self.stdout.write(_('  Status: enabled\n'))
            else:
                self.stdout.write(_('  Status: disabled\n'))

            self.stdout.write(_('  ID: %s\n') % extension.class_name)
            self.stdout.write('\n')
