"""Management command for listing extensions."""

from __future__ import unicode_literals

from django.utils.translation import ugettext as _
from djblets.extensions.models import RegisteredExtension
from djblets.util.compat.django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Management command for listing extensions."""

    help = _('Lists available Review Board extensions.')

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            '--enabled',
            action='store_true',
            default=False,
            dest='list_enabled',
            help=_('List only enabled extensions'))

    def handle(self, **options):
        """Handle the command.

        Args:
            **options (dict):
                Options parsed on the command line.
        """
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
