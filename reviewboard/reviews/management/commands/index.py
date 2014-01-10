import optparse

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        optparse.make_option('--full', action='store_true',
                             dest='rebuild', default=False,
                             help='Rebuild the database index'),
    )
    help = "Creates a search index of review requests"
    requires_model_validation = True

    def handle(self, *args, **options):
        # Call the appropriate Haystack command to refresh the search index.
        if options['rebuild']:
            call_command('rebuild_index', interactive=False)
        else:
            call_command('update_index')
