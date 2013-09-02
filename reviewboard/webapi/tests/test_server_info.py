from djblets.testing.decorators import add_fixtures

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class ServerInfoResourceTests(BaseWebAPITestCase):
    """Testing the ServerInfoResource APIs."""
    item_mimetype = _build_mimetype('server-info')

    def test_get_server_info(self):
        """Testing the GET info/ API"""
        rsp = self.apiGet(self.get_url(),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('info' in rsp)
        self.assertTrue('product' in rsp['info'])
        self.assertTrue('site' in rsp['info'])
        self.assertTrue('capabilities' in rsp['info'])

        caps = rsp['info']['capabilities']
        self.assertTrue('diffs' in caps)

        diffs_caps = caps.get('diffs')
        self.assertTrue(diffs_caps.get('moved_files', False))
        self.assertTrue(diffs_caps.get('base_commit_ids', False))

    @add_fixtures(['test_users', 'test_site'])
    def test_get_server_info_with_site(self):
        """Testing the GET info/ API with a local site"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_url(self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('info' in rsp)
        self.assertTrue('product' in rsp['info'])
        self.assertTrue('site' in rsp['info'])

    @add_fixtures(['test_users', 'test_site'])
    def test_get_server_info_with_site_no_access(self):
        """Testing the GET info/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_url(self.local_site_name),
                    expected_status=403)

    def get_url(self, local_site_name=None):
        return local_site_reverse('info-resource',
                                  local_site_name=local_site_name)
