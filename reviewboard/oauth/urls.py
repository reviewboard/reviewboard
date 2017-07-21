"""OAuth2-related URLs."""

from __future__ import unicode_literals

from django.conf.urls import url
from oauth2_provider import views as oauth2_provider_views

from reviewboard.oauth import views


urlpatterns = [
    url(r'^authorize/$', views.AuthorizationView.as_view(), name='authorize'),
    url(r'^token/$', oauth2_provider_views.TokenView.as_view(), name='token'),
]
