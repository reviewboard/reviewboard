from __future__ import unicode_literals

import os

from djblets.util.compat.django.core.management.base import BaseCommand

from reviewboard.reviews.models import Screenshot


class Command(BaseCommand):
    def handle(self, **options):
        prefix = os.path.join("images", "uploaded")
        new_prefix = os.path.join("uploaded", "images")

        for screenshot in Screenshot.objects.all():
            if screenshot.image.startswith(prefix):
                screenshot.image = \
                    os.path.join(new_prefix,
                                 os.path.basename(screenshot.image))
                screenshot.save()
