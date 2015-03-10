from __future__ import unicode_literals

from django.utils import six

from reviewboard.webapi.resources import resources
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

        caps = item_rsp['capabilities']
        self.assertIn('diffs', caps)

        diffs_caps = caps['diffs']
        self.assertTrue(diffs_caps['moved_files'])
        self.assertTrue(diffs_caps['base_commit_ids'])

        diff_validation_caps = diffs_caps['validation']
        self.assertTrue(diff_validation_caps['base_commit_ids'])

        review_request_caps = caps['review_requests']
        self.assertTrue(review_request_caps['commit_ids'])

        text_caps = caps['text']
        self.assertTrue(text_caps['markdown'])

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        return (get_server_info_url(local_site_name),
                server_info_mimetype,
                None)
