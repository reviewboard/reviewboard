"""OAuth2-related URLs."""

from django.urls import path
from oauth2_provider import views as oauth2_provider_views

from reviewboard.oauth import views


urlpatterns = [
    path('authorize/', views.AuthorizationView.as_view(), name='authorize'),
    path('token/', oauth2_provider_views.TokenView.as_view(), name='token'),
]
