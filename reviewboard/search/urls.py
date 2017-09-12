from __future__ import unicode_literals

from django.conf.urls import url

from reviewboard.search.views import RBSearchView


urlpatterns = [
    url(r'^$', RBSearchView.as_view(), name='search'),
]
