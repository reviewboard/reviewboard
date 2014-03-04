from __future__ import unicode_literals

from django.conf.urls import patterns, url

from {{package_name}}.extension import {{class_name}}


urlpatterns = patterns(
    '{{package_name}}.views',

    url(r'^$', 'configure'),
)
