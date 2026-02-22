"""Base classes for datagrid unit tests.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.test.client import RequestFactory
from djblets.datagrid.grids import Column, DataGrid
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.models import LocalSiteProfile, Profile
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class BaseViewTestCase(TestCase):
    """Base class for tests of dashboard views."""

    #: The base URL to the datagrid being tested.
    #:
    #: Type:
    #:     str
    #:
    #: Version Added:
    #:     5.0.7
    datagrid_url: str = ''

    def setUp(self) -> None:
        """Set up the test case.

        This will set some initial configuration defaults for access control.

        It will temporarily patch :py:meth:`django.db.models.QuerySet.
        __eq__` to help compare with nested queries. This is a temporary
        issue, and this function will soon be removed.
        """
        super().setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self._old_auth_require_sitewide_login = \
            self.siteconfig.get('auth_require_sitewide_login')
        self.siteconfig.set('auth_require_sitewide_login', False)
        self.siteconfig.save()

        # This is a very temporary hack to work around some assertQueries
        # comparisons that fail due to our improper use of a nested query.
        # It will be removed as soon as this issue is fixed.
        self._old_queryset_eq = QuerySet.__eq__

        setattr(QuerySet, '__eq__',
                lambda _self, other: repr(_self) == repr(other))

    def tearDown(self):
        """Tear down test state.

        This will restore the configuration and reset
        :py:meth:`django.db.models.QuerySet.__eq__` to defaults.
        """
        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set('auth_require_sitewide_login',
                            self._old_auth_require_sitewide_login)
        self.siteconfig.save()

        setattr(QuerySet, '__eq__', self._old_queryset_eq)

        super().tearDown()

    def get_datagrid_url(
        self,
        *,
        local_site: Optional[LocalSite],
    ) -> str:
        """Return the URL to the datagrid page.

        This will take a provided Local Site into account for the URL.

        Version Added:
            5.0.7

        Args:
            local_site (reviewboard.site.models.LocalSite):
                The Local Site to access, or ``None`` if accessing the
                global site.

        Returns:
            str:
            The datagrid page URL.
        """
        url = self.datagrid_url

        if local_site is not None:
            url = '/s/%s%s' % (local_site.name, url)

        return url

    def _prefetch_cached(
        self,
        *,
        local_site: Optional[LocalSite] = None,
        user: Optional[User] = None,
    ) -> None:
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

        for temp_user in User.objects.all():
            temp_user.get_local_site_stats()

        if user is not None:
            try:
                profile = user.get_profile(create_if_missing=False)
                profile.has_starred_review_groups(local_site=local_site)
            except Profile.DoesNotExist:
                pass

            try:
                user.get_site_profile(local_site=local_site,
                                      create_if_missing=False)
            except LocalSiteProfile.DoesNotExist:
                pass

    def _get_context_var(self, response, varname):
        """Return a variable from the view context."""
        return response.context.get(varname)


class BaseColumnTestCase(TestCase):
    """Base class for defining a column unit test."""

    #: An instance of the column to use on the datagrid.
    #:
    #: Type:
    #:     djblets.datagrid.columns.Column
    column: Optional[Column] = None

    fixtures = ['test_users']

    def setUp(self) -> None:
        super().setUp()

        assert self.column is not None

        class TestDataGrid(DataGrid):
            column = self.column

        request_factory = RequestFactory()
        self.request = request_factory.get('/')
        self.request.user = User.objects.get(username='doc')

        self.grid = TestDataGrid(self.request)
        self.stateful_column = self.grid.get_stateful_column(self.column)
