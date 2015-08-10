from __future__ import unicode_literals

from django.conf.urls import patterns, url, include


urlpatterns = patterns(
    'djblets.extensions.tests',

    url(r'^$', 'test_view_method', name="test-url-name"),
    url(r'^admin/extensions/', include('djblets.extensions.urls')),
)
