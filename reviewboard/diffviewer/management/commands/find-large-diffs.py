"""Management command to find large diffs in the database.

Version Added:
    5.0.3
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import timedelta
from typing import Counter, Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext as _

from reviewboard.diffviewer.models import FileDiff
from reviewboard.reviews.models import ReviewRequest


class Command(BaseCommand):
    """Management command to find large diffs in the database.

    This can be useful when diagnosing performance problems on a Review Board
    server.

    Version Added:
        5.0.3
    """

    help = _(
        'Find large diffs stored in the database, for diagnosing performance '
        'problems.'
    )

    def add_arguments(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            '--min-size',
            type=int,
            default=100000,
            metavar='MIN_SIZE_BYTES',
            help=_(
                'Minimum diff or parent diff size to include in a result. '
                ' A review request is included if a diff meets --min-size '
                'or --min-files. Defaults to 100000 (100KB).'
            ))
        parser.add_argument(
            '--min-files',
            type=int,
            default=50,
            help=_(
                'Minimum number of files to include in a result. A review '
                'request is included if a diff meets --min-size or '
                '--min-files. Defaults to 50.'
            ))
        parser.add_argument(
            '--start-id',
            type=int,
            help=_(
                'Starting review request ID for the scan. Either --start-id '
                'or --num-days must be specified.'
            ))
        parser.add_argument(
            '--end-id',
            type=int,
            default=None,
            help=_(
                'Last review request ID for the scan. Defaults to the last '
                'ID in the database.'
            ))
        parser.add_argument(
            '--num-days',
            type=int,
            help=_(
                'Number of days back to scan for diffs. Either --num-days or '
                '--start-id must be specified.'
            ))
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            help=_(
                'Disable prompting for confirmation before performing the '
                'scan.'
            ))

    def handle(
        self,
        **options,
    ) -> None:
        """Handle the command.

        This will perform the large diff scan, based on the provided options.

        Args:
            **options (dict, unused):
                Options parsed on the command line.

        Raises:
            django.core.management.CommandError:
                There was an error performing a diff migration.
        """
        min_size: int = options['min_size']
        min_files: int = options['min_files']
        num_days: Optional[int] = options['num_days']
        start_id: Optional[int] = options['start_id']
        end_id: Optional[int] = options['end_id']

        if num_days is None and start_id is None:
            raise CommandError(_(
                'Either --num-days or --start-id must be specified.'
            ))

        queryset = (
            ReviewRequest.objects
            .only('diffset_history', 'last_updated', 'pk', 'submitter')
            .order_by()
        )

        if start_id is not None:
            if end_id is None:
                queryset = queryset.filter(pk__gte=start_id)
            else:
                queryset = queryset.filter(pk__range=(start_id, end_id))

        if num_days is not None:
            queryset = queryset.filter(
                last_updated__gte=timezone.now() - timedelta(days=num_days))

        # Check whether to confirm before performing the scan, in case there's
        # a larger number of review requests than expected.
        if options['interactive']:
            num_review_requests = queryset.count()

            answer = input(
                f'This will scan {num_review_requests} review requests. '
                f'Continue? [Y/n] '
            )

            if answer not in ('Y', 'y'):
                self.stderr.write('Canceling the scan.')
                sys.exit(1)

        csv_writer = csv.writer(self.stdout)
        csv_writer.writerow([
            'Review Request ID',
            'Last Updated',
            'User ID',
            'Max Files',
            'Max Diff Size',
            'Max Parent Diff Size',
            'Diffset ID for Max Files',
            'Diffset ID for Max Diff Size',
            'Diffset ID for Max Parent Diff Size',
        ])

        for review_request in queryset.all():
            # Each of these default to 0, so we can safely run max() later
            # in the event that a dictionary is otherwise empty.
            diff_size_by_diffset = Counter[int]({0: 0})
            parent_diff_size_by_diffset = Counter[int]({0: 0})
            num_files_by_diffset = Counter[int]({0: 0})

            filediffs = (
                FileDiff.objects
                .filter(diffset__history=review_request.diffset_history_id)
                .only('pk', 'diffset', 'diff_hash', 'parent_diff_hash')
                .prefetch_related('diff_hash', 'parent_diff_hash')
            )

            for filediff in filediffs:
                diffset_id = filediff.diffset_id
                num_files_by_diffset[diffset_id] += 1

                try:
                    diff_size_by_diffset[diffset_id] += \
                        len(filediff.diff_hash.content or '')
                except Exception:
                    pass

                try:
                    parent_diff_size_by_diffset[diffset_id] += \
                        len(filediff.parent_diff_hash.content or '')
                except Exception:
                    pass

            # Figure out the largest values and diffsets.
            max_diffset_id_by_diff, max_diff_size = \
                max(diff_size_by_diffset.items(),
                    key=lambda pair: pair[1])
            max_diffset_id_by_parent_diff, max_parent_diff_size = \
                max(parent_diff_size_by_diffset.items(),
                    key=lambda pair: pair[1])
            max_diffset_id_by_num_files, max_num_files = \
                max(num_files_by_diffset.items(),
                    key=lambda pair: pair[1])

            if (max_diff_size > min_size or
                max_parent_diff_size > min_size or
                max_num_files > min_files):
                csv_writer.writerow([
                    review_request.pk,
                    review_request.last_updated,
                    review_request.submitter_id,
                    max_num_files,
                    max_diff_size,
                    max_parent_diff_size,
                    max_diffset_id_by_num_files,
                    max_diffset_id_by_diff,
                    max_diffset_id_by_parent_diff,
                ])
