from __future__ import unicode_literals

import logging
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from reviewboard.reviews.models import ReviewRequest


class Command(BaseCommand):
    help = 'Resets all calculated issue counts for review requests.'

    option_list = BaseCommand.option_list + (
        make_option('-a', '--all',
                    action='store_true',
                    default=False,
                    dest='all',
                    help='Reset issue counts for all review requests.'),
        make_option('--recalculate',
                    action='store_true',
                    default=False,
                    dest='recalculate',
                    help='Recalculates issue counts for the review requests. '
                         'This is not compatible with --all'),
    )

    def handle(self, *args, **options):
        update_all = options.get('all')
        recalculate = options.get('recalculate')

        if update_all:
            if recalculate:
                raise CommandError('--recalculate cannot be used with --all')

            q = ReviewRequest.objects.all()
        else:
            pks = []

            for arg in args:
                try:
                    pks.append(int(arg))
                except ValueError:
                    raise CommandError('%s is not a valid review request ID'
                                       % arg)

            if not pks:
                raise CommandError(
                    'One or more review request IDs must be provided.')

            q = ReviewRequest.objects.filter(pk__in=pks)

        q.update(issue_open_count=None,
                 issue_resolved_count=None,
                 issue_dropped_count=None)

        if not update_all and recalculate:
            if int(options['verbosity']) > 1:
                root_logger = logging.getLogger('')
                root_logger.setLevel(logging.DEBUG)

            # Load each review request. The issue counters will recalculate,
            # and output will be shown if verbosity > 1.
            list(q)

        if update_all:
            self.stdout.write('All issue counts reset.')
        else:
            self.stdout.write('Issue counts for review request(s) %s reset.'
                              % ', '.join(args))
