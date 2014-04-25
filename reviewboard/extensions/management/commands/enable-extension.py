from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _
from djblets.extensions.errors import (EnablingExtensionError,
                                       InvalidExtensionError)

from reviewboard.extensions.base import get_extension_manager


class Command(BaseCommand):
    help = _('Enables an extension.')

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError(
                _('You must specify an extension ID to enable.'))

        extension_id = args[0]
        extension_mgr = get_extension_manager()

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
            raise CommandError(_('Unexpected error enabling extension: %s')
                               % e)
