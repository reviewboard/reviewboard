"""Management command for disabling an extension."""

from __future__ import unicode_literals

from django.core.management.base import CommandError
from django.utils.translation import ugettext as _
from djblets.util.compat.django.core.management.base import BaseCommand

from reviewboard.extensions.base import get_extension_manager


class Command(BaseCommand):
    """Management command for disabling an extension."""

    help = _('Disables an extension.')

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            'extension_ids',
            metavar='EXTENSION_ID',
            nargs='*',
            help=_('The ID of the extension to disable.'))

    def handle(self, *args, **options):
        """Handle the command.

        Args:
            *args (tuple):
                The name of the check to resolve.

            **options (dict, unused):
                Options parsed on the command line. For this command, no
                options are available.

        Raises:
            django.core.management.CommandError:
                There was an error with arguments or enabling the extension.
        """
        extension_ids = options['extension_ids']

        if not extension_ids:
            raise CommandError(
                _('You must specify an extension ID to disable.'))

        extension_mgr = get_extension_manager()

        for extension_id in extension_ids:
            try:
                extension_mgr.disable_extension(extension_id)
            except Exception as e:
                raise CommandError(
                    _('Unexpected error disabling extension %s: %s')
                    % (extension_id, e))
