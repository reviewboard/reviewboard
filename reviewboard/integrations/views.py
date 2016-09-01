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

    def get_form_kwargs(self):
        """Return keyword arguments to pass to the form.

        This will, by default, provide ``integration`` and configuration
        ``instance`` keyword arguments to the form during initialization,
        along with the ``request`` and ``local_site`` (if any).

        Subclases can override it with additional arguments if needed.

        Returns:
            dict:
            A dictionary of keyword arguments to pass to the form.
        """
        form_kwargs = \
            super(AdminIntegrationConfigFormView, self).get_form_kwargs()
        form_kwargs['limit_to_local_site'] = \
            getattr(form_kwargs['request'], 'local_site', None)

        return form_kwargs


class AdminIntegrationListView(GetIntegrationManagerMixin,
                               BaseAdminIntegrationListView):
    """Administration view for listing integrations."""
