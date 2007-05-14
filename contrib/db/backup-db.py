#!/usr/bin/env python
#
# Database backup script
#
# This dumps the database of ReviewBoard into a JSON file and then
# reorders the models so that dependencies are met. The result should
# be loadable by running:
#
#   $ ./contrib/db/load-db.py dbdump.json

import os, simplejson, sys

if not os.path.exists("manage.py"):
    print "This must be run in the directory containing manage.py."
    sys.exit(1)


fp = os.popen("./manage.py dumpdata accounts reviews diffviewer scmtools", "r")
buffer = fp.read()
fp.close()

data = simplejson.loads(buffer)

new_data = {}

for entry in data:
    model = entry["model"]

    if not new_data.has_key(model):
        new_data[model] = []

    new_data[model].append(entry)


a = []

for model in ('scmtools.tool', 'scmtools.repository',
              'diffviewer.diffsethistory', 'diffviewer.diffset',
              'diffviewer.filediff',
              'reviews.group',
              'reviews.screenshot', 'reviews.screenshotcomment',
              'reviews.comment', 'reviews.reviewrequest',
              'reviews.reviewrequestdraft', 'reviews.review',
              'accounts.profile'):
    if new_data.has_key(model):
        for entry in new_data[model]:
            a.append(entry)

print simplejson.dumps(a)
