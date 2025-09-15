"""Unit tests for reviewboard.webapi.resources.session."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.http import SimpleCookie
from djblets.webapi.errors import NOT_LOGGED_IN
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import session_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_session_url

if TYPE_CHECKING:
    from typing import Any

    from django.contrib.auth.models import User
    from typelets.json import JSONDict

    from reviewboard.webapi.tests.mixins import BasicPutTestSetupState


class ResourceTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
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

        self.assertEqual(
            rsp,
            {
                'session': {
                    'authenticated': False,
                    'links': {
                        'self': {
                            'href': 'http://testserver/api/session/',
                            'method': 'GET',
                        },
                    },
                },
                'stat': 'ok',
            })

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

        self.assertEqual(
            rsp,
            {
                'err': {
                    'code': NOT_LOGGED_IN.code,
                    'msg': NOT_LOGGED_IN.msg,
                    'type': NOT_LOGGED_IN.error_type,
                },
                'stat': 'fail',
            })

    #
    # HTTP PUT tests
    #

    # This test does not apply, so remove it.
    test_put_not_owner = None

    def populate_put_test_objects(
        self,
        *,
        setup_state: BasicPutTestSetupState,
        create_valid_request_data: bool,
        **kwargs,
    ) -> None:
        """Populate objects for a PUT test.

        Version Added:
            7.1

        Args:
            setup_state (reviewboard.webapi.tests.mixins.
                         BasicPutTestSetupState):
                The setup state for the test.

            create_valid_request_data (bool):
                Whether ``request_data`` in ``setup_state`` should provide
                valid data for a PUT test, given the populated objects.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        setup_state.update({
            'item': None,
            'mimetype': session_mimetype,
            'request_data': {},
            'url': get_session_url(
                local_site_name=setup_state['local_site_name']),
        })

    def check_put_result(
        self,
        user: User,
        item_rsp: JSONDict,
        item: Any,
        *args,
    ) -> None:
        """Check the results of an HTTP PUT.

        Version Added:
            7.1

        Args:
            user (django.contrib.auth.models.User):
                The user performing the requesdt.

            item_rsp (dict):
                The item payload from the response.

            item (object):
                The item to compare to.

            *args (tuple):
                Positional arguments provided by
                :py:meth:`setup_basic_put_test`.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        self.compare_item(item_rsp, user)

    @webapi_test_template
    def test_put_with_settings_json(self) -> None:
        """Testing the PUT <URL> API with settings:json"""
        user = self._login_user()

        profile = user.get_profile()
        profile.settings['some_setting'] = '123'
        profile.save(update_fields=('settings',))

        rsp = self.api_put(
            get_session_url(),
            {
                'settings:json': json.dumps({
                    'bad_option': '123',
                    'confirm_ship_it': False,
                })
            },
            expected_mimetype=session_mimetype)

        self.assertEqual(
            rsp,
            {
                'session': {
                    'authenticated': True,
                    'links': {
                        'delete': {
                            'href': 'http://testserver/api/session/',
                            'method': 'DELETE',
                        },
                        'self': {
                            'href': 'http://testserver/api/session/',
                            'method': 'GET',
                        },
                        'user': {
                            'href': 'http://testserver/api/users/grumpy/',
                            'method': 'GET',
                            'title': 'grumpy',
                        },
                    },
                },
                'stat': 'ok',
            })

        profile.refresh_from_db()
        self.assertEqual(profile.settings, {
            'some_setting': '123',
            'confirm_ship_it': False,
        })
