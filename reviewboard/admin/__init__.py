from __future__ import unicode_literals

from django.db.models.signals import post_save, post_delete

from reviewboard.admin.signals import _delete_widget_cache
from reviewboard.reviews.models import Group
from reviewboard.scmtools.models import Repository


post_save.connect(_delete_widget_cache, sender=Group)
post_save.connect(_delete_widget_cache, sender=Repository)
post_delete.connect(_delete_widget_cache, sender=Group)
post_delete.connect(_delete_widget_cache, sender=Repository)
