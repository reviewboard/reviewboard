from __future__ import unicode_literals

from django.dispatch import Signal


local_site_user_added = Signal(providing_args=['user', 'localsite'])
