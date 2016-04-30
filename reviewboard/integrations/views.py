"""Views for listing and configuring integrations."""

from __future__ import unicode_literals

from djblets.integrations.views import (BaseAdminIntegrationConfigFormView,
                                        BaseAdminIntegrationListView)

from reviewboard.integrations.base import GetIntegrationManagerMixin
from reviewboard.site.urlresolvers import local_site_reverse


class AdminIntegrationConfigFormView(GetIntegrationManagerMixin,
                                     BaseAdminIntegrationConfigFormView):
    """Administration view for configuration an integration."""

    def get_success_url(self):
        """Return the URL to redirect to after saving the form.

        This will take the user back to the list of integrations.

        Returns:
            unicode:
            The URL to the integration list page.
        """
        return local_site_reverse('integration-list', request=self.request)


class AdminIntegrationListView(GetIntegrationManagerMixin,
                               BaseAdminIntegrationListView):
    """Administration view for listing integrations."""
