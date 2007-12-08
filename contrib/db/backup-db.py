#!/usr/bin/env python
#
# Database backup script
#
# This dumps the database of ReviewBoard into a JSON file and then
# reorders the models so that dependencies are met. The result should
# be loadable by running:
#
#   $ ./contrib/db/load-db.py dbdump.json

import os
import sys
import gc

sys.path.append(os.getcwd())

try:
    import settings
except ImportError:
    sys.stderr.write(("Error: Can't find the file 'settings.py' in the " +
                      "directory containing %r. Make sure you're running " +
                      "from the root reviewboard directory.") % __file__)
    sys.exit(1)


# This must be done before we import any models
from django.core.management import setup_environ
settings.DEBUG = False
setup_environ(settings)

from django.core import serializers

import reviewboard.accounts.models as accounts
import reviewboard.diffviewer.models as diffviewer
import reviewboard.reviews.models as reviews
import reviewboard.scmtools.models as scmtools


models = (scmtools.Tool, scmtools.Repository,
          diffviewer.DiffSetHistory, diffviewer.DiffSet,
          diffviewer.FileDiff,
          reviews.DefaultReviewer, reviews.Group,
          reviews.Screenshot, reviews.ScreenshotComment,
          reviews.Comment, reviews.ReviewRequest,
          reviews.ReviewRequestDraft, reviews.Review,
          accounts.Profile)

OBJECT_LIMIT = 150

serializer = serializers.get_serializer("json")()

totalobjs = 0
for model in models:
    totalobjs += model.objects.count()

prev_pct = -1
i = 0

sys.stderr.write("Backing up database. This may take a while...\n")

print "# dbdump v1 - %s objects" % totalobjs

for model in models:
    count = model.objects.count()
    j = 0

    while j < count:
        for obj in model.objects.all()[j:j+OBJECT_LIMIT].iterator():
            value = serializer.serialize([obj])

            if value != "[]":
                print value[1:-1] # Skip the "[" and "]"

            i += 1
            pct = (i * 100 / totalobjs)
            if pct != prev_pct:
                sys.stderr.write("  [%s%%]\r" % pct)
                sys.stderr.flush()
                prev_pct = pct

        j += OBJECT_LIMIT

sys.stderr.write("\n")
sys.stderr.write("Done.\n")
