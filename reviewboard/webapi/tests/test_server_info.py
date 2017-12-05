from __future__ import unicode_literals

from django.conf import settings
from django.utils import six

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.admin.server import get_server_url
from reviewboard.webapi.resources import resources
from reviewboard.webapi.server_info import get_capabilities
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import server_info_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_server_info_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
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

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        return (get_server_info_url(local_site_name),
                server_info_mimetype,
                None)
