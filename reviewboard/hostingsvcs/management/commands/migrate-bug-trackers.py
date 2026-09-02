"""Management command to migrate legacy bug tracker data.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from reviewboard.hostingsvcs.bug_tracker_migration import materialize_configs
from reviewboard.reviews.models import Bug, ReviewRequest, ReviewRequestDraft
from reviewboard.reviews.models.bug import BUGS_MIGRATED_KEY

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    """Management command to migrate legacy bug tracker data.

    Version Added:
        9.0
    """

    help = _(
        'Migrates legacy per-repository bug tracker settings into bug '
        'tracker configurations, and optionally converts stored '
        'bugs_closed data into bug relations.'
    )

    def add_arguments(
        self,
        parser: ArgumentParser,
    ) -> None:
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            '--backfill-bugs',
            action='store_true',
            default=False,
            dest='backfill_bugs',
            help=_('Convert stored bugs_closed data on all review '
                   'requests into bug relations. Searching and querying '
                   'by bug ID is supported only once this finishes.'))
        parser.add_argument(
            '--batch-size',
            default=500,
            dest='batch_size',
            type=int,
            help=_('The number of review requests to process at a time '
                   'when backfilling.'))

    def handle(self, **options) -> None:
        """Handle the command.

        Args:
            **options (dict):
                Options parsed on the command line.
        """
        stats = materialize_configs()

        self.stdout.write(
            _('Bug tracker configurations: %(created)d created, '
              '%(updated)d repositories updated, %(skipped)d unchanged.')
            % stats)

        if options['backfill_bugs']:
            self._backfill_bugs(batch_size=options['batch_size'])
        else:
            remaining = self._count_unmigrated()

            if remaining:
                self.stdout.write(
                    _('%(count)d review requests have bug data that has '
                      'not been converted to bug relations. Querying by '
                      'bug ID is supported only after conversion. To '
                      'convert them, run this command with '
                      '--backfill-bugs.')
                    % {
                        'count': remaining,
                    })

    def _backfill_bugs(
        self,
        *,
        batch_size: int,
    ) -> None:
        """Convert stored bugs_closed data into bug relations.

        This processes review requests and drafts in batches, ordered by
        ID. It is safe to interrupt and re-run.

        Args:
            batch_size (int):
                The number of rows to process at a time.
        """
        for model in (ReviewRequest, ReviewRequestDraft):
            migrated = 0
            last_pk = 0

            while True:
                rows = list(
                    model.objects
                    .filter(pk__gt=last_pk)
                    .exclude(bugs_closed='')
                    .order_by('pk')[:batch_size]
                )

                if not rows:
                    break

                for row in rows:
                    last_pk = row.pk

                    if (row.extra_data or {}).get(BUGS_MIGRATED_KEY):
                        continue

                    Bug.objects.materialize_for(row)
                    row.save(update_fields=('extra_data',))
                    migrated += 1

                self.stdout.write(
                    _('Migrated %(count)d %(model)s rows...')
                    % {
                        'count': migrated,
                        'model': model.__name__,
                    })

            self.stdout.write(
                _('Done. Migrated bugs on %(count)d %(model)s rows.')
                % {
                    'count': migrated,
                    'model': model.__name__,
                })

        remaining = self._count_unmigrated()

        if remaining:
            self.stdout.write(
                _('%(count)d review requests still have unconverted bug '
                  'data. Re-run with --backfill-bugs to continue.')
                % {
                    'count': remaining,
                })
        else:
            self.stdout.write(
                _('All bug data has been converted. Querying by bug ID '
                  'now covers all review requests.'))

    def _count_unmigrated(self) -> int:
        """Return the number of review requests with unconverted bugs.

        Returns:
            int:
            The number of review requests with a non-empty legacy bug
            list and no migration marker.
        """
        count = 0

        for review_request in (
            ReviewRequest.objects
            .exclude(bugs_closed='')
            .only('pk', 'extra_data')
            .iterator()
        ):
            if not (review_request.extra_data or {}).get(BUGS_MIGRATED_KEY):
                count += 1

        return count
