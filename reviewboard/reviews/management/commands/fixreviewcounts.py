from __future__ import unicode_literals

from django.core.management.base import NoArgsCommand

from reviewboard.accounts.admin import fix_review_counts


class Command(NoArgsCommand):
    help = "Fixes all incorrect review request-related counters."

    def handle_noargs(self, **options):
        fix_review_counts()
