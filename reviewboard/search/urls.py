from __future__ import unicode_literals

from django.conf.urls import patterns, url
from haystack.views import search_view_factory

from reviewboard.search.views import RBSearchView


urlpatterns = patterns(
    '',

    url(r'^$',
        search_view_factory(view_class=RBSearchView),
        name='search'),
)
