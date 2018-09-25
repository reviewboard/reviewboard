from __future__ import unicode_literals

from django.http import SimpleCookie
from django.utils import six
from djblets.webapi.errors import NOT_LOGGED_IN
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import session_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_session_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the SessionResource APIs."""
    fixtures = ['test_users']
    sample_api_url = 'session/'
    resource = resources.session

    def setup_http_not_allowed_list_test(self, user):
        return get_session_url()

    def setup_http_not_allowed_item_test(self, user):
        return get_session_url()

    def compare_item(self, item_rsp, user):
        self.assertTrue(item_rsp['authenticated'])
        self.assertEqual(item_rsp['links']['user']['title'], user.username)
        self.assertEqual(item_rsp['links']['delete']['href'],
                         item_rsp['links']['self']['href'])
        self.assertEqual(item_rsp['links']['delete']['method'], 'DELETE')

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        return (get_session_url(local_site_name),
                session_mimetype,
                user)

    def test_get_with_anonymous_user(self):
        """Testing the GET session/ API with anonymous user"""
        self.client.logout()
        rsp = self.api_get(get_session_url(),
                           expected_mimetype=session_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('session', rsp)
        self.assertFalse(rsp['session']['authenticated'])

    #
    # HTTP DELETE test
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        return (get_session_url(local_site_name),
                session_mimetype)

    def check_delete_result(self, user, *args):
        pass

    @webapi_test_template
    def test_delete_not_owner(self):
        """Testing the DELETE <URL> API when not logged in"""
        self.load_fixtures(self.basic_delete_fixtures)

        url, cb_args = self.setup_basic_delete_test(self.user, False, None)

        self.client.logout()
        self.client.cookies = SimpleCookie()

        rsp = self.api_delete(url, expected_status=401)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], NOT_LOGGED_IN.code)
