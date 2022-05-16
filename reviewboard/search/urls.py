from django.urls import path

from reviewboard.search.views import RBSearchView


urlpatterns = [
    path('', RBSearchView.as_view(), name='search'),
]
