"""URLs for processing license-related state.

Version Added:
    7.1
"""

from __future__ import annotations

from django.urls import path

from reviewboard.licensing.views import LicensesView


urlpatterns = [
    path('',
         LicensesView.as_view(),
         name='admin-licenses'),
]
