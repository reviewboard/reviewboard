"""Management command to condense stored diffs in the database."""

from __future__ import unicode_literals, division

import sys
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.translation import ugettext as _, ungettext_lazy as N_
from djblets.util.compat.django.core.management.base import BaseCommand

from reviewboard.diffviewer.models import FileDiff


class Command(BaseCommand):
    """Management command to condense stored diffs in the database."""

    help = _('Condenses the diffs stored in the database, reducing space '
             'requirements')

    DELAY_SHOW_REMAINING_SECS = 30

    TIME_REMAINING_CHUNKS = (
        (60 * 60 * 24 * 365, N_('%d year', '%d years')),
        (60 * 60 * 24 * 30, N_('%d month', '%d months')),
        (60 * 60 * 24 * 7, N_('%d week', '%d weeks')),
        (60 * 60 * 24, N_('%d day', '%d days')),
        (60 * 60, N_('%d hour', '%d hours')),
        (60, N_('%d minute', '%d minutes'))
    )

    # We add a bunch of spaces in order to override any previous
    # content on the line, for when it shrinks.
    TIME_REMAINING_STR = _('%s remaining                                  ')

    CALC_TIME_REMAINING_STR = _('Calculating time remaining')

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            '--show-counts-only',
            action='store_true',
            dest='show_counts',
            default=False,
            help=_("Show the number of diffs that are expected to be "
                   "migrated, but don't perform a migration."))
        parser.add_argument(
            '--no-progress',
            action='store_false',
            dest='show_progress',
            default=True,
            help=_("Don't show progress information or totals while "
                   "migrating. You might want to use this if your database "
                   "is taking too long to generate total migration counts."))
        parser.add_argument(
            '--max-diffs',
            action='store',
            dest='max_diffs',
            type=int,
            default=None,
            help=_("The maximum number of migrations to perform. This is "
                   "useful if you have a lot of diffs to migrate and want "
                   "to do it over several sessions."))

    def handle(self, **options):
        """Handle the command.

        Args:
            **options (dict, unused):
                Options parsed on the command line.

        Raises:
            django.core.management.CommandError:
                There was an error performing a diff migration.
        """
        self.show_progress = options['show_progress']
        max_diffs = options['max_diffs']

        if options['show_counts']:
            counts = FileDiff.objects.get_migration_counts()
            self.stdout.write(_('%d unmigrated Review Board pre-1.7 diffs\n')
                              % counts['filediffs'])
            self.stdout.write(_('%d unmigrated Review Board 1.7-2.5 diffs\n')
                              % counts['legacy_file_diff_data'])
            self.stdout.write(_('%d total unmigrated diffs\n')
                              % counts['total_count'])
            return
        elif self.show_progress:
            counts = FileDiff.objects.get_migration_counts()
            total_count = counts['total_count']

            if total_count == 0:
                self.stdout.write(_('All diffs have already been migrated.\n'))
                return

            warning = counts.get('warning')

            if warning:
                self.stderr.write(_('Warning: %s\n\n') % warning)

            if max_diffs is None:
                process_count = total_count
            else:
                process_count = min(max_diffs, total_count)

            self.stdout.write(_('Processing %(count)d unmigrated diffs...\n')
                              % {'count': process_count})
        else:
            # Set to an empty dictionary to force migrate_all() to not
            # look up its own counts.
            counts = {}

            self.stdout.write(_('Processing all unmigrated diffs...\n'))

        self.stdout.write(_(
          '\n'
          'This may take a while. It is safe to continue using '
          'Review Board while this is\n'
          'processing, but it may temporarily run slower.\n'
          '\n'))

        # Don't allow queries to be stored.
        settings.DEBUG = False

        self.start_time = datetime.now()
        self.prev_prefix_len = 0
        self.prev_time_remaining_s = ''
        self.show_remaining = False

        info = FileDiff.objects.migrate_all(batch_done_cb=self._on_batch_done,
                                            counts=counts,
                                            max_diffs=max_diffs)

        if info['diffs_migrated'] == 0:
            self.stdout.write(_('All diffs have already been migrated.\n'))
        else:
            old_diff_size = info['old_diff_size']
            new_diff_size = info['new_diff_size']

            self.stdout.write(
                _('\n'
                  '\n'
                  'Condensed stored diffs from %(old_size)s bytes to '
                  '%(new_size)s bytes (%(savings_pct)0.2f%% savings)\n')
                % {
                    'old_size': intcomma(old_diff_size),
                    'new_size': intcomma(new_diff_size),
                    'savings_pct': (float(old_diff_size - new_diff_size) /
                                    float(old_diff_size) * 100),
                })

    def _on_batch_done(self, total_diffs_migrated, total_count=None, **kwargs):
        """Handler for when a batch of diffs are processed.

        This will report the progress of the operation, showing the estimated
        amount of time remaining.

        Args:
            total_diffs_migrated (int):
                The total number of diffs migrated so far in this
                condensediffs operation.

            total_count (int, optional):
                The total number of diffs to migrate in the database. This
                may be ``None``, in which case the output won't contain
                progress and time estimation.

            **kwargs (dict, unused):
                Unused keyword arguments.
        """
        # NOTE: We use sys.stdout when writing instead of self.stderr in order
        #       to control newlines. Command.stderr will force a \n for each
        #       write.
        if self.show_progress:
            # We may be receiving an estimate for the total number of diffs
            # that is less than the actual count. If we've gone past the
            # initial total, just bump up the total to the current count.
            total_count = max(total_diffs_migrated, total_count)

            pct = total_diffs_migrated * 100 / total_count

            delta = datetime.now() - self.start_time
            delta_secs = delta.total_seconds()

            if (not self.show_remaining and
                delta_secs >= self.DELAY_SHOW_REMAINING_SECS):
                self.show_remaining = True

            if self.show_remaining:
                secs_left = ((delta_secs // total_diffs_migrated) *
                             (total_count - total_diffs_migrated))

                time_remaining_s = (self.TIME_REMAINING_STR
                                    % self._time_remaining(secs_left))
            else:
                time_remaining_s = self.CALC_TIME_REMAINING_STR

            prefix_s = '  [%d%%] %s/%s - ' % (pct, total_diffs_migrated,
                                              total_count)

            sys.stdout.write(prefix_s)

            # Only write out the time remaining string if it has changed or
            # there's been a shift in the length of the prefix. This reduces
            # how much we have to write to the terminal, and how often, by
            # a fair amount.
            if (self.prev_prefix_len != len(prefix_s) or
                self.prev_time_remaining_s != time_remaining_s):
                # Something has changed, so output the string and then cache
                # the values for the next call.
                sys.stdout.write(time_remaining_s)

                self.prev_prefix_len = len(prefix_s)
                self.prev_time_remaining_s = time_remaining_s
        else:
            sys.stdout.write(' %s diffs migrated' % total_diffs_migrated)

        sys.stdout.write('\r')
        sys.stdout.flush()

    def _time_remaining(self, secs_left):
        """Return a string representing the time remaining for the operation.

        This is a simplified version of Django's timeuntil() function that
        does fewer calculations in order to reduce the amount of time we
        have to spend every loop. For instance, it doesn't bother with
        constructing datetimes and recomputing deltas, since we already
        have those, and it doesn't rebuild the TIME_REMAINING_CHUNKS
        every time it's called. It also handles seconds.

        Args:
            secs_left (int):
                The estimated number of seconds remaining.

        Returns:
            unicode:
            The text containing the time remaining.
        """
        delta = timedelta(seconds=secs_left)
        since = delta.days * 24 * 60 * 60 + delta.seconds

        if since < 60:
            return N_('%d second', '%d seconds') % since

        for i, (seconds, name) in enumerate(self.TIME_REMAINING_CHUNKS):
            count = since // seconds

            if count != 0:
                break

        result = name % count

        if i + 1 < len(self.TIME_REMAINING_CHUNKS):
            seconds2, name2 = self.TIME_REMAINING_CHUNKS[i + 1]
            count2 = (since - (seconds * count)) // seconds2

            if count2 != 0:
                result += ', ' + name2 % count2

        return result
