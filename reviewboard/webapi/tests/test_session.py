from __future__ import unicode_literals

from djblets.util.compat import six

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
        rsp = self.apiGet(get_session_url(),
                          expected_mimetype=session_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertFalse(rsp['session']['authenticated'])
