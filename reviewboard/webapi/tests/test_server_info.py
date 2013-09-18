from djblets.testing.decorators import add_fixtures

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import server_info_mimetype
from reviewboard.webapi.tests.urls import get_server_info_url


class ResourceTests(BaseWebAPITestCase):
    """Testing the ServerInfoResource APIs."""

    #
    # HTTP GET tests
    #

    def test_get_server_info(self):
        """Testing the GET info/ API"""
        rsp = self.apiGet(get_server_info_url(),
                          expected_mimetype=server_info_mimetype)
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
        rsp = self.apiGet(get_server_info_url(self.local_site_name),
                          expected_mimetype=server_info_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('info' in rsp)
        self.assertTrue('product' in rsp['info'])
        self.assertTrue('site' in rsp['info'])

    @add_fixtures(['test_users', 'test_site'])
    def test_get_server_info_with_site_no_access(self):
        """Testing the GET info/ API
        with a local site and Permission Denied error
        """
        self.apiGet(get_server_info_url(self.local_site_name),
                    expected_status=403)
