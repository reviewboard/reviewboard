from __future__ import unicode_literals

import os

from django.core.management.base import NoArgsCommand

from reviewboard.reviews.models import Screenshot


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        prefix = os.path.join("images", "uploaded")
        new_prefix = os.path.join("uploaded", "images")

        for screenshot in Screenshot.objects.all():
            if screenshot.image.startswith(prefix):
                screenshot.image = \
                    os.path.join(new_prefix,
                                 os.path.basename(screenshot.image))
                screenshot.save()
