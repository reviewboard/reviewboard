from __future__ import unicode_literals

from django.db.models import signals

from reviewboard.admin.management.evolutions import init_evolutions
from reviewboard.admin.management.sites import init_siteconfig


signals.post_syncdb.connect(init_evolutions)
signals.post_syncdb.connect(init_siteconfig)
