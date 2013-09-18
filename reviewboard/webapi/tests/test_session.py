from djblets.testing.decorators import add_fixtures

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import session_mimetype
from reviewboard.webapi.tests.urls import get_session_url


class ResourceTests(BaseWebAPITestCase):
    """Testing the SessionResource APIs."""

    #
    # HTTP GET tests
    #

    @add_fixtures(['test_users'])
    def test_get_session_with_logged_in_user(self):
        """Testing the GET session/ API with logged in user"""
        rsp = self.apiGet(get_session_url(),
                          expected_mimetype=session_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertTrue(rsp['session']['authenticated'])
        self.assertEqual(rsp['session']['links']['user']['title'],
                         self.user.username)

    def test_get_session_with_anonymous_user(self):
        """Testing the GET session/ API with anonymous user"""
        rsp = self.apiGet(get_session_url(),
                          expected_mimetype=session_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertFalse(rsp['session']['authenticated'])

    @add_fixtures(['test_users', 'test_site'])
    def test_get_session_with_site(self):
        """Testing the GET session/ API with a local site"""
        self._login_user(local_site=True)
        rsp = self.apiGet(get_session_url(self.local_site_name),
                          expected_mimetype=session_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertTrue(rsp['session']['authenticated'])
        self.assertEqual(rsp['session']['links']['user']['title'], 'doc')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_session_with_site_no_access(self):
        """Testing the GET session/ API
        with a local site and Permission Denied error
        """
        self.apiGet(get_session_url(self.local_site_name),
                    expected_status=403)
