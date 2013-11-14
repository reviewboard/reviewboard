from __future__ import unicode_literals

from djblets.testing.decorators import add_fixtures
from djblets.util.compat import six

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import root_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_root_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the RootResource APIs."""
    fixtures = ['test_users']
    sample_api_url = '/'
    resource = resources.root
    test_http_methods = ('DELETE', 'PUT', 'POST')

    def setup_http_not_allowed_item_test(self, user):
        return get_root_url()

    def setup_http_not_allowed_list_test(self, user):
        return get_root_url()

    def test_get(self):
        """Testing the GET / API"""
        rsp = self.apiGet(get_root_url(),
                          expected_mimetype=root_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('uri_templates' in rsp)
        self.assertTrue('repository' in rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/api/repositories/{repository_id}/')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_with_site(self):
        """Testing the GET / API with local sites"""
        self._login_user(local_site=True)
        rsp = self.apiGet(get_root_url('local-site-1'),
                          expected_mimetype=root_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('uri_templates' in rsp)
        self.assertTrue('repository' in rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-1/api/'
                         'repositories/{repository_id}/')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET / API without access to local site"""
        self.apiGet(get_root_url('local-site-1'), expected_status=403)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_with_site_and_cache(self):
        """Testing the GET / API with multiple local sites"""
        # djblets had a bug where the uri_templates were cached without any
        # consideration of the local site (or, more generally, the base uri).
        # In this case, fetching /s/<local_site>/api/ might return uri
        # templates for someone else's site. This was breaking rbt post.
        self.test_get_with_site()

        rsp = self.apiGet(get_root_url('local-site-2'),
                          expected_mimetype=root_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('uri_templates' in rsp)
        self.assertTrue('repository' in rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-2/api/'
                         'repositories/{repository_id}/')
