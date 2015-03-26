from __future__ import unicode_literals

from django.conf.urls import patterns, url

from reviewboard.search.views import search


urlpatterns = patterns(
    '',

    url(r'^$', search, name='search'),
)
