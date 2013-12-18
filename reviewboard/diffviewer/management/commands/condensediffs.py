from __future__ import unicode_literals

from django.core.management.base import NoArgsCommand

from reviewboard.diffviewer.models import FileDiff


class Command(NoArgsCommand):
    help = ('Condenses the diffs stored in the database, reducing space '
            'requirements')

    def handle_noargs(self, **options):
        count = FileDiff.objects.unmigrated().count()

        if count == 0:
            self.stdout.write('All diffs have already been migrated.\n')
            return

        self.stdout.write(
            'Processing %(count)d diffs for duplicates...\n'
            '\n'
            'This may take a while. It is safe to continue using '
            'Review Board while this is\n'
            'processing, but it may temporarily run slower.\n'
            % {
                'count': count,
            });

        info = FileDiff.objects.migrate_all()

        old_diff_size = info['old_diff_size']
        new_diff_size = info['new_diff_size']

        self.stdout.write(
            '\n'
            'Condensed stored diffs from %s bytes to %s bytes '
            '(%d%% savings)\n'
            % (old_diff_size, new_diff_size,
               float(new_diff_size) / float(old_diff_size) * 100.0))
