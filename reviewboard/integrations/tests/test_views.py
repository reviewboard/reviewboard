from __future__ import unicode_literals

from django.test import RequestFactory

from reviewboard.integrations.base import Integration, get_integration_manager
from reviewboard.integrations.models import IntegrationConfig
from reviewboard.integrations.views import AdminIntegrationConfigFormView
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class MyIntegration(Integration):
    pass


class AdminIntegrationConfigFormViewTests(TestCase):
    """Unit tests for AdminIntegrationConfigFormView."""

    def setUp(self):
        super(AdminIntegrationConfigFormViewTests, self).setUp()

        self.integration = MyIntegration(get_integration_manager())
        self.config = IntegrationConfig()
        self.request = RequestFactory().request()

        # NOTE: integration and config are normally set in dispatch(), but
        #       we're not calling into all that, so we're taking advantage of
        #       the fact that Django's class-based generic views will set any
        #       attribute passed in during construction.
        self.view = AdminIntegrationConfigFormView(
            request=self.request,
            integration=self.integration,
            config=self.config)

    def test_get_form_kwargs(self):
        """Testing AdminIntegrationConfigFormView.get_form_kwargs"""
        form_kwargs = self.view.get_form_kwargs()

        self.assertIsNone(form_kwargs['limit_to_local_site'])

    def test_get_form_kwargs_with_local_site(self):
        """Testing AdminIntegrationConfigFormView.get_form_kwargs with
        LocalSite
        """
        # This is normally set by LocalSiteMiddleware.
        local_site = LocalSite.objects.create(name='local-site-1')
        self.request.local_site = local_site

        form_kwargs = self.view.get_form_kwargs()
        self.assertEqual(form_kwargs['limit_to_local_site'], local_site)
