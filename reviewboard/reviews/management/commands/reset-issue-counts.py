"""Management command to reset issue counters."""

from __future__ import unicode_literals

import logging

from django.core.management.base import CommandError
from django.utils.translation import ugettext as _
from djblets.util.compat.django.core.management.base import BaseCommand

from reviewboard.reviews.models import ReviewRequest


class Command(BaseCommand):
    """Management command to reset issue counters."""

    help = 'Resets all calculated issue counts for review requests.'

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            'review_request_ids',
            metavar='REVIEW_REQUEST_ID',
            nargs='*',
            help='Specific review request IDs to reset.')

        parser.add_argument(
            '-a',
            '--all',
            action='store_true',
            default=False,
            dest='all',
            help='Reset issue counts for all review requests.')

        parser.add_argument(
            '--recalculate',
            action='store_true',
            default=False,
            dest='recalculate',
            help='Recalculates issue counts for the review requests. '
                 'This is not compatible with --all')

    def handle(self, *args, **options):
        """Handle the command.

        Args:
            *args (tuple):
                Specific review request IDs to reset.

            **options (dict, unused):
                Options parsed on the command line. For this command, no
                options are available.
        """
        update_all = options.get('all')
        recalculate = options.get('recalculate')

        if update_all:
            if recalculate:
                raise CommandError(
                    _('--recalculate cannot be used with --all'))

            q = ReviewRequest.objects.all()
        else:
            pks = []

            for arg in args:
                try:
                    pks.append(int(arg))
                except ValueError:
                    raise CommandError(
                        _('%s is not a valid review request ID')
                        % arg)

            if not pks:
                raise CommandError(
                    _('One or more review request IDs must be provided.'))

            q = ReviewRequest.objects.filter(pk__in=pks)

        q.update(issue_open_count=None,
                 issue_resolved_count=None,
                 issue_dropped_count=None,
                 issue_verifying_count=None)

        if not update_all and recalculate:
            if int(options['verbosity']) > 1:
                root_logger = logging.getLogger('')
                root_logger.setLevel(logging.DEBUG)

            # Load each review request. The issue counters will recalculate,
            # and output will be shown if verbosity > 1.
            list(q)

        if update_all:
            self.stdout.write(_('All issue counts reset.'))
        else:
            self.stdout.write(_('Issue counts for review request(s) %s reset.')
                              % ', '.join(args))
