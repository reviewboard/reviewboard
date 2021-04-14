"""Management command to load data into the database."""

from __future__ import unicode_literals

import textwrap
import sys

from djblets.util.compat.django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Management command to load data into the database."""

    help = (
        "[No longer supported] Loads data formatted by dumpdb.\n"
        "\n"
        "This functionality has been removed. Please use your database's "
        "native tools instead, or contact support@beanbaginc.com for "
        "alternative solutions."
    )

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            'filename',
            metavar='NAME',
            nargs='*',
            help='The name of the file to load.')

    def handle(self, **options):
        """Handle the command.

        Args:
            **options (dict, unused):
                Options parsed on the command line.

        Raises:
            django.core.management.CommandError:
                There was an error with arguments or disabling the extension.
        """
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            "dumpdb and loaddb are no longer supported. They weren't meant "
            "for production installs, and we weren't able to retain "
            "compatibility with the version of Django now used by "
            "Review Board. We recommend using your database's "
            "native SQL dumping and loading tools instead.\n"))
        self.stderr.write('\n')
        self.stderr.write(textwrap.fill(
            "If you need this functionality, or assistance with "
            "transitioning databases, you can contact us at "
            "support@beanbaginc.com for options."))

        sys.exit(1)
