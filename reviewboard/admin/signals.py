from __future__ import unicode_literals

from reviewboard.admin.widgets import increment_sync_num


_CACHED_WIDGETS = ("w-user-activity-", "w-request-statuses-",
                   "w-repositories-", "w-groups-", "w-stats-")


def _delete_widget_cache(*args, **kwargs):
    """Clear the cache to keep the admin dashboard up to date."""
    increment_sync_num()
