from __future__ import unicode_literals

from django.conf.urls import include, url
from djblets.urls.resolvers import DynamicURLResolver


dynamic_urls = DynamicURLResolver()


urlpatterns = [
    url(r'^repos/(?P<repository_id>\d+)/', include([dynamic_urls])),
]
