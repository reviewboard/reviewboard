"""Base classes for datagrid unit tests.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from djblets.datagrid.grids import DataGrid
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class BaseViewTestCase(TestCase):
    """Base class for tests of dashboard views."""

    def setUp(self):
        """Set up the test case."""
        super(BaseViewTestCase, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self._old_auth_require_sitewide_login = \
            self.siteconfig.get('auth_require_sitewide_login')
        self.siteconfig.set('auth_require_sitewide_login', False)
        self.siteconfig.save()

    def tearDown(self):
        super(BaseViewTestCase, self).tearDown()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set('auth_require_sitewide_login',
                            self._old_auth_require_sitewide_login)
        self.siteconfig.save()

    def _prefetch_cached(self, local_site=None):
        """Pre-fetch cacheable statistics and data.

        Version Added:
            5.0

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site being used for the test.
        """
        SiteConfiguration.objects.get_current()

        if local_site is not None:
            LocalSite.objects.get_local_site_acl_stats(local_site)

        for user in User.objects.all():
            user.get_local_site_stats()

    def _get_context_var(self, response, varname):
        """Return a variable from the view context."""
        for context in response.context:
            if varname in context:
                return context[varname]

        return None


class BaseColumnTestCase(TestCase):
    """Base class for defining a column unit test."""

    #: An instance of the column to use on the datagrid.
    column = None

    fixtures = ['test_users']

    def setUp(self):
        super(BaseColumnTestCase, self).setUp()

        class TestDataGrid(DataGrid):
            column = self.column

        request_factory = RequestFactory()
        self.request = request_factory.get('/')
        self.request.user = User.objects.get(username='doc')

        self.grid = TestDataGrid(self.request)
        self.stateful_column = self.grid.get_stateful_column(self.column)
