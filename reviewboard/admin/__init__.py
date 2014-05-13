from __future__ import unicode_literals

from django.db.models.signals import post_save, post_delete

from reviewboard.admin.widgets import increment_sync_num
from reviewboard.reviews.models import Group
from reviewboard.scmtools.models import Repository


def _delete_widget_cache(*args, **kwargs):
    """Clear the cache to keep the admin dashboard up to date."""
    increment_sync_num()


post_save.connect(_delete_widget_cache, sender=Group)
post_save.connect(_delete_widget_cache, sender=Repository)
post_delete.connect(_delete_widget_cache, sender=Group)
post_delete.connect(_delete_widget_cache, sender=Repository)
