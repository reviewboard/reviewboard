from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'djblets.log.views',

    url(r'^server/$', 'server_log', name='server-log')
)
