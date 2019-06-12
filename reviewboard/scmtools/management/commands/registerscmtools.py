"""Management command to register SCMTools in the database."""

from __future__ import unicode_literals

import pkg_resources
import sys

from django.utils.translation import ugettext as _
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
        registered_tools = {}

        for tool in Tool.objects.all():
            registered_tools[tool.class_name] = True

        for entry in pkg_resources.iter_entry_points('reviewboard.scmtools'):
            try:
                scmtool_class = entry.load()
            except Exception as e:
                sys.stderr.write(_('Unable to load SCMTool %s: %s\n')
                                 % (entry, e))
                continue

            class_name = '%s.%s' % (scmtool_class.__module__,
                                    scmtool_class.__name__)

            if class_name not in registered_tools:
                registered_tools[class_name] = True
                name = (scmtool_class.name or
                        scmtool_class.__name__.replace('Tool', ''))

                self.stdout.write(
                    _('Registering new SCM Tool %s (%s) in the database.')
                    % (name, class_name))

                Tool.objects.create(name=name, class_name=class_name)
