"""Management command to register SCMTools in the database."""

from __future__ import unicode_literals

from django.utils.translation import ugettext as _, ungettext
from djblets.util.compat.django.core.management.base import BaseCommand

from reviewboard.scmtools.models import Tool


class Command(BaseCommand):
    """Management command to register SCMTools in the database."""

    help = _('Register available SCMTools in the database.')

    def handle(self, **options):
        """Handle the command.

        Args:
            **options (dict, unused):
                Options parsed on the command line. For this command, no
                options are available.
        """
        new_tools = Tool.objects.register_from_entrypoints()

        if new_tools:
            count = len(new_tools)

            self.stdout.write(
                ungettext('Registered %(count)d new SCMTool: %(tools)s\n',
                          'Registered %(count)d new SCMTools: %(tools)s\n',
                          count)
                % {
                    'count': count,
                    'tools': ', '.join(
                        tool.name
                        for tool in new_tools
                    )
                })
        else:
            self.stdout.write(_('No new SCMTools were found.\n'))
