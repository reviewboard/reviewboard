from __future__ import unicode_literals

from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('{{package_name}}.views',
    url(r'^$', 'dashboard'),
)
