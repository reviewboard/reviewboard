from datetime import date
import datetime
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from djblets.util import misc


"""
    These signals listen to database changes
    and clear the cache to keep the admin dashboard up to date.
"""
def deleteWidgetCache():
    cached_widgets = ("w-user-activity-", "w-request-statuses-",
                      "w-repositories-", "w-groups-", "w-stats-")

    for widget in cached_widgets:
        key = widget + str(datetime.date.today())
        cache.delete(misc.make_cache_key(key))


@receiver(post_save)
def my_handler(sender,**kwargs):
    deleteWidgetCache()


@receiver(post_delete)
def my_handler(sender,**kwargs):
    deleteWidgetCache()