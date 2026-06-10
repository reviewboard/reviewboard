"""URLs for hosting services."""

from __future__ import annotations

from django.urls import include, path
from djblets.urls.resolvers import DynamicURLResolver


hosting_service_urls = DynamicURLResolver()
repository_urls = DynamicURLResolver()


urlpatterns = [
    path('hosting-services/', include([hosting_service_urls])),
    path('repos/<int:repository_id>/', include([repository_urls])),
]
