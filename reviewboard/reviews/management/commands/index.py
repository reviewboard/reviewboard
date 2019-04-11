"""Management command to manage the search index."""

from django.core.management import call_command
from django.utils.translation import ugettext as _
from djblets.util.compat.django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Management command to manage the search index."""

    help = _('Creates a search index of review requests.')
    requires_model_validation = True

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            '--full',
            action='store_true',
            dest='rebuild',
            default=False,
            help='Rebuild the database index')

    def handle(self, **options):
        """Handle the command.

        Args:
            **options (dict):
                Options parsed on the command line.
        """
        # Call the appropriate Haystack command to refresh the search index.
        if options['rebuild']:
            call_command('rebuild_index', interactive=False)
        else:
            call_command('update_index')
