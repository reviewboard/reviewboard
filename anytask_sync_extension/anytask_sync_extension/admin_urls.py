from __future__ import unicode_literals

from django.conf.urls import patterns, url

from anytask_sync_extension.extension import AnytaskSyncExtension


urlpatterns = patterns(
    'anytask_sync_extension.views',

    url(r'^$', 'configure'),
)
