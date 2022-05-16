from django.urls import include, path
from djblets.urls.resolvers import DynamicURLResolver


dynamic_urls = DynamicURLResolver()


urlpatterns = [
    path('repos/<int:repository_id>/', include([dynamic_urls])),
]
