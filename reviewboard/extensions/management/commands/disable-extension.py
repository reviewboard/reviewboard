from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _

from reviewboard.extensions.base import get_extension_manager


class Command(BaseCommand):
    help = _('Disables an extension.')

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError(
                _('You must specify an extension ID to disable.'))

        extension_id = args[0]
        extension_mgr = get_extension_manager()

        try:
            extension_mgr.disable_extension(extension_id)
        except Exception as e:
            raise CommandError(_('Unexpected error disabling extension: %s')
                               % e)
