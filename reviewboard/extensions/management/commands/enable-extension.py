"""Management command for enabling an extension."""

from __future__ import unicode_literals

from django.core.management.base import CommandError
from django.utils.translation import ugettext as _
from djblets.extensions.errors import (EnablingExtensionError,
                                       InvalidExtensionError)
from djblets.util.compat.django.core.management.base import BaseCommand

from reviewboard.extensions.base import get_extension_manager


class Command(BaseCommand):
    """Management command for enabling an extension."""

    help = _('Enables an extension.')

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
            help=_('The ID of the extension to enable.'))

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
                There was an error with arguments or disabling the extension.
        """
        extension_ids = options['extension_ids']

        if not extension_ids:
            raise CommandError(
                _('You must specify an extension ID to enable.'))

        extension_mgr = get_extension_manager()

        for extension_id in extension_ids:
            try:
                extension_mgr.enable_extension(extension_id)
            except InvalidExtensionError:
                raise CommandError(_('%s is not a valid extension ID.')
                                   % extension_id)
            except EnablingExtensionError as e:
                raise CommandError(
                    _('Error enabling extension: %(message)s\n\n%(error)s') % {
                        'message': e.message,
                        'error': e.load_error,
                    })
            except Exception as e:
                raise CommandError(
                    _('Unexpected error enabling extension %s: %s')
                    % (extension_id, e))
