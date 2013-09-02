from djblets.testing.decorators import add_fixtures

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class RootResourceTests(BaseWebAPITestCase):
    """Testing the RootResource APIs."""
    item_mimetype = _build_mimetype('root')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_api_root_with_local_site(self):
        """Testing the GET / API with local sites"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_url('local-site-1'),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('uri_templates' in rsp)
        self.assertTrue('repository' in rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-1/api/'
                         'repositories/{repository_id}/')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_api_root_with_local_site_and_cache(self):
        """Testing the GET / API with multiple local sites"""
        # djblets had a bug where the uri_templates were cached without any
        # consideration of the local site (or, more generally, the base uri).
        # In this case, fetching /s/<local_site>/api/ might return uri
        # templates for someone else's site. This was breaking rbt post.
        self.test_get_api_root_with_local_site()

        rsp = self.apiGet(self.get_url('local-site-2'),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('uri_templates' in rsp)
        self.assertTrue('repository' in rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-2/api/'
                         'repositories/{repository_id}/')

    def get_url(self, local_site_name=None):
        return local_site_reverse('root-resource',
                                  local_site_name=local_site_name)
