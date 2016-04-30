"""URLs for integration listing and configuration."""

from __future__ import unicode_literals

from djblets.integrations.urls import build_integration_urlpatterns

from reviewboard.integrations.views import (AdminIntegrationConfigFormView,
                                            AdminIntegrationListView)


#: URL patterns for the administration UI views for configuring integrations.
urlpatterns = build_integration_urlpatterns(
    list_view_cls=AdminIntegrationListView,
    config_form_view_cls=AdminIntegrationConfigFormView)
