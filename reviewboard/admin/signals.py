import datetime

from django.core.cache import cache
from django.db.models import signals
from djblets.util.misc import make_cache_key


_CACHED_WIDGETS = ("w-user-activity-", "w-request-statuses-",
                   "w-repositories-", "w-groups-", "w-stats-")


def _delete_widget_cache(*args, **kwargs):
    """Clear the cache to keep the admin dashboard up to date."""
    timestamp = str(datetime.date.today())

    cache.delete_many([make_cache_key(widget + timestamp)
                       for widget in _CACHED_WIDGETS])


signals.post_save.connect(_delete_widget_cache)
signals.post_delete.connect(_delete_widget_cache)
