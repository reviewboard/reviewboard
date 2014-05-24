from __future__ import unicode_literals

import sys

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.management.base import NoArgsCommand

from reviewboard.diffviewer.models import FileDiff


class Command(NoArgsCommand):
    help = ('Condenses the diffs stored in the database, reducing space '
            'requirements')

    def handle_noargs(self, **options):
        self.count = FileDiff.objects.unmigrated().count()

        if self.count == 0:
            self.stdout.write('All diffs have already been migrated.\n')
            return

        self.stdout.write(
            'Processing %(count)d diffs for duplicates...\n'
            '\n'
            'This may take a while. It is safe to continue using '
            'Review Board while this is\n'
            'processing, but it may temporarily run slower.\n'
            '\n'
            % {
                'count': self.count,
            })

        # Don't allow queries to be stored.
        settings.DEBUG = False

        self.i = 0
        self.prev_pct = -1

        info = FileDiff.objects.migrate_all(self._on_processed_filediff)

        old_diff_size = info['old_diff_size']
        new_diff_size = info['new_diff_size']

        self.stdout.write(
            '\n'
            '\n'
            'Condensed stored diffs from %s bytes to %s bytes '
            '(%d%% savings)\n'
            % (intcomma(old_diff_size), intcomma(new_diff_size),
               float(new_diff_size) / float(old_diff_size) * 100.0))

    def _on_processed_filediff(self, filediff):
        self.i += 1
        pct = self.i * 100 / self.count

        if pct != self.prev_pct:
            # NOTE: We use sys.stdout here instead of self.stderr in order
            #       to control newlines. Command.stderr will force a \n for
            #       each write.
            sys.stdout.write("  [%s%%]\r" % pct)
            sys.stdout.flush()
            self.prev_pct = pct
