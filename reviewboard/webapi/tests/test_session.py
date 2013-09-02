from djblets.testing.decorators import add_fixtures

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class SessionResourceTests(BaseWebAPITestCase):
    """Testing the SessionResource APIs."""
    item_mimetype = _build_mimetype('session')

    @add_fixtures(['test_users'])
    def test_get_session_with_logged_in_user(self):
        """Testing the GET session/ API with logged in user"""
        rsp = self.apiGet(self.get_url(),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertTrue(rsp['session']['authenticated'])
        self.assertEqual(rsp['session']['links']['user']['title'],
                         self.user.username)

    def test_get_session_with_anonymous_user(self):
        """Testing the GET session/ API with anonymous user"""
        rsp = self.apiGet(self.get_url(),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertFalse(rsp['session']['authenticated'])

    @add_fixtures(['test_users', 'test_site'])
    def test_get_session_with_site(self):
        """Testing the GET session/ API with a local site"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_url(self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertTrue(rsp['session']['authenticated'])
        self.assertEqual(rsp['session']['links']['user']['title'], 'doc')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_session_with_site_no_access(self):
        """Testing the GET session/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_url(self.local_site_name),
                    expected_status=403)

    def get_url(self, local_site_name=None):
        return local_site_reverse('session-resource',
                                  local_site_name=local_site_name)
