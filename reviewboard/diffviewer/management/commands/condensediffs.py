from __future__ import unicode_literals, division

import sys
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.management.base import NoArgsCommand
from django.utils.translation import ugettext as _, ungettext_lazy as N_

from reviewboard.diffviewer.models import FileDiff


class Command(NoArgsCommand):
    help = ('Condenses the diffs stored in the database, reducing space '
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

    def handle_noargs(self, **options):
        counts = FileDiff.objects.get_migration_counts()
        total_count = counts['total_count']

        if total_count == 0:
            self.stdout.write(_('All diffs have already been migrated.\n'))
            return

        self.stdout.write(
            _('Processing %(count)d diffs for duplicates...\n'
              '\n'
              'This may take a while. It is safe to continue using '
              'Review Board while this is\n'
              'processing, but it may temporarily run slower.\n'
              '\n')
            % {'count': total_count})

        # Don't allow queries to be stored.
        settings.DEBUG = False

        self.start_time = datetime.now()
        self.prev_prefix_len = 0
        self.prev_time_remaining_s = ''
        self.show_remaining = False

        info = FileDiff.objects.migrate_all(self._on_batch_done, counts)

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

    def _on_batch_done(self, processed_count, total_count):
        """Handler for when a batch of diffs are processed.

        This will report the progress of the operation, showing the estimated
        amount of time remaining.
        """
        pct = processed_count * 100 / total_count
        delta = datetime.now() - self.start_time

        # XXX: This can be replaced with total_seconds() once we no longer have
        # to support Python 2.6
        delta_secs = (
            (delta.microseconds +
             (delta.seconds + delta.days * 24 * 3600) * 10 ** 6) /
            10 ** 6)

        if (not self.show_remaining and
            delta_secs >= self.DELAY_SHOW_REMAINING_SECS):
            self.show_remaining = True

        if self.show_remaining:
            secs_left = ((delta_secs // processed_count) *
                         (total_count - processed_count))

            time_remaining_s = (self.TIME_REMAINING_STR
                                % self._time_remaining(secs_left))
        else:
            time_remaining_s = self.CALC_TIME_REMAINING_STR

        prefix_s = '  [%d%%] %s/%s - ' % (pct, processed_count, total_count)

        # NOTE: We use sys.stdout here instead of self.stderr in order
        #       to control newlines. Command.stderr will force a \n for
        #       each write.
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

        sys.stdout.write('\r')
        sys.stdout.flush()

    def _time_remaining(self, secs_left):
        """Returns a string representing the time remaining for the operation.

        This is a simplified version of Django's timeuntil() function that
        does fewer calculations in order to reduce the amount of time we
        have to spend every loop. For instance, it doesn't bother with
        constructing datetimes and recomputing deltas, since we already
        have those, and it doesn't rebuild the TIME_REMAINING_CHUNKS
        every time it's called. It also handles seconds.
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
