"""Unit tests for the ServerInfoResource API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple

from django.conf import settings
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.admin.server import get_server_url
from reviewboard.webapi.resources import resources
from reviewboard.webapi.server_info import get_capabilities
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import server_info_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_server_info_url

if TYPE_CHECKING:
    from django.contrib.auth.models import User


class ResourceTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Testing the ServerInfoResource APIs."""

    fixtures = ['test_users']
    sample_api_url = 'info/'
    resource = resources.server_info

    def setup_http_not_allowed_list_test(self, user):
        return get_server_info_url()

    def setup_http_not_allowed_item_test(self, user):
        return get_server_info_url()

    def compare_item(self, item_rsp, obj):
        self.assertIn('product', item_rsp)
        self.assertIn('site', item_rsp)
        self.assertIn('capabilities', item_rsp)

        product_rsp = item_rsp['product']
        self.assertEqual(product_rsp['name'], 'Review Board')
        self.assertEqual(product_rsp['version'], get_version_string())
        self.assertEqual(product_rsp['package_version'], get_package_version())
        self.assertEqual(product_rsp['is_release'], is_release())

        site_rsp = item_rsp['site']
        self.assertTrue(site_rsp['url'].startswith(get_server_url()))
        self.assertEqual(site_rsp['administrators'], [
            {
                'name': name,
                'email': email,
            }
            for name, email in settings.ADMINS
        ])
        self.assertEqual(site_rsp['time_zone'], settings.TIME_ZONE)

        self.assertEqual(item_rsp['capabilities'], get_capabilities())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
    ) -> Tuple[str, str, Any]:
        """Set up a basic HTTP GET unit test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

            local_site_name (str or None):
                The name of the Local Site to test against.

                This will be ``None`` if testing against the global site.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (object):
                    The item to compare to in :py:meth:`compare_item`.
        """
        return (get_server_info_url(local_site_name),
                server_info_mimetype,
                None)

    @webapi_test_template
    def test_get_registered_scmtools(self) -> None:
        """Testing the GET <URL> API registered SCMTools"""
        url, mimetype, obj = self.setup_basic_get_test(self.user, False, None)

        rsp = self.api_get(url, expected_mimetype=mimetype)
        assert rsp is not None

        capabilities = rsp['info']['capabilities']

        self.assertIn('git',
                      capabilities['scmtools']['supported_tools'])
