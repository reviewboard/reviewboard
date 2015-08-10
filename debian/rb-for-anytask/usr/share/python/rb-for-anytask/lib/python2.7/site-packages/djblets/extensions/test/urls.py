from __future__ import unicode_literals

from django.conf.urls import patterns


urlpatterns = patterns(
    'djblets.extensions.views',

    (r'^$', 'test_url')
)
