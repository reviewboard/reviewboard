"""Tests for the OAuth applications web API,."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.db.query import get_object_or_none
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.oauth.forms import ApplicationChangeForm
from reviewboard.oauth.models import Application
from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (oauth_app_item_mimetype,
                                                oauth_app_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_oauth_app_item_url,
                                           get_oauth_app_list_url)


def _compare_item(self, item_rsp, app):
    self.assertEqual(item_rsp['authorization_grant_type'],
                     app.authorization_grant_type)
    self.assertEqual(item_rsp['client_id'], app.client_id)
    self.assertEqual(item_rsp['client_secret'], app.client_secret)
    self.assertEqual(item_rsp['client_type'], app.client_type)
    self.assertEqual(item_rsp['id'], app.pk)
    self.assertEqual(item_rsp['name'], app.name)

    if app.redirect_uris:
        uris = {uri.strip() for uri in app.redirect_uris.split(',')}
    else:
        uris = set()

    self.assertEqual(set(item_rsp['redirect_uris']), uris)
    self.assertEqual(item_rsp['skip_authorization'], app.skip_authorization)
    self.assertEqual(item_rsp['links']['user']['title'], app.user.username)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ExtraDataListMixin, BaseWebAPITestCase):
    """Testing the OAuthApplicationResource list APIs."""

    resource = resources.oauth_app
    sample_api_url = 'oauth-apps/'

    fixtures = ['test_users']

    compare_item = _compare_item

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            if with_local_site:
                local_site = LocalSite.objects.get(name=local_site_name)
            else:
                local_site = None

            items = [
                Application.objects.create(user=user, local_site=local_site),
            ]
        else:
            items = []

        return (get_oauth_app_list_url(local_site_name=local_site_name),
                oauth_app_list_mimetype,
                items)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_filtered(self):
        """Testing the GET <URL> API only returns filtered applications"""
        admin = User.objects.get(username='admin')
        local_site = LocalSite.objects.get(pk=1)

        applications = set(filter(
            lambda a: a.local_site is None and a.user == self.user,
            self._make_applications([self.user, admin], local_site),
        ))

        rsp = self.api_get(get_oauth_app_list_url(),
                           {},
                           expected_mimetype=oauth_app_list_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(applications,
                         self._applications_from_response(rsp['oauth_apps']))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_filtered_with_localsite(self):
        """Testing the GET <URL> API only returns filtered applications on a
        LocalSite
        """
        admin = User.objects.get(username='admin')
        local_site = LocalSite.objects.get(pk=1)
        local_site.users.add(self.user)

        applications = self._make_applications(
            users=[self.user, admin],
            local_site=local_site,
            predicate=lambda a: (a.local_site == local_site and
                                 a.user == self.user),
        )

        rsp = self.api_get(get_oauth_app_list_url(local_site.name),
                           {},
                           expected_mimetype=oauth_app_list_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(applications,
                         self._applications_from_response(rsp['oauth_apps']))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_superuser_get(self):
        """Testing the GET <URL> API as a superuser"""
        self.user = self._login_user(local_site=False, admin=True)

        local_site = LocalSite.objects.get(pk=1)
        doc = User.objects.get(username='doc')

        applications = self._make_applications(
            users=[self.user, doc],
            local_site=local_site,
            predicate=lambda a: a.local_site is None,
        )

        rsp = self.api_get(get_oauth_app_list_url(),
                           {},
                           expected_mimetype=oauth_app_list_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(applications,
                         self._applications_from_response(rsp['oauth_apps']))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_superuser_get_local_site(self):
        """Testing the GET <URL> API with a LocalSite as a superuser"""
        self.user = self._login_user(local_site=False, admin=True)

        local_site = LocalSite.objects.get(pk=1)
        doc = User.objects.get(username='doc')

        applications = self._make_applications(
            users=[self.user, doc],
            local_site=local_site,
            predicate=lambda a: a.local_site == local_site,
        )

        rsp = self.api_get(get_oauth_app_list_url(local_site.name),
                           {},
                           expected_mimetype=oauth_app_list_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(applications,
                         self._applications_from_response(rsp['oauth_apps']))

    def _applications_from_response(self, item_rsps):
        """Return the Application instances for the given item responses.

        Args:
            item_rsps (list):
                The individual item responses.

        Returns:
            set of reviewboard.oauth.models.Application:
            The matching applications.
        """
        return set(Application.objects.filter(
            pk__in=(item['id'] for item in item_rsps),
        ))

    def _make_applications(self, users, local_site, predicate=None):
        """Create some applications for testing:

        Args:
            users (list of django.contrib.auth.models.User):
                The users to create applications for.

            local_site (reviewboard.site.models.LocalSite):
                A LocalSite.

            predicate (callable, optional):
                An optional callable predicate to filter the results.

        Returns:
            set of reviewboard.oauth.models.Application:
            The created applications.
        """
        applications = set()

        applications.update(
            self.create_oauth_application(u, None, name='%s-app' % u.username)
            for u in users
        )

        applications.update(
            self.create_oauth_application(u, local_site,
                                          name='%s-site-app' % u.username)
            for u in users
        )

        if predicate:
            applications = set(filter(predicate, applications))

        return applications

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        if post_valid_data:
            post_data = {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
            }
        else:
            post_data = {}

        return (get_oauth_app_list_url(local_site_name),
                oauth_app_item_mimetype,
                post_data,
                [])

    def check_post_result(self, user, rsp):
        app = Application.objects.get(pk=rsp['oauth_app']['id'])
        self.compare_item(rsp['oauth_app'], app)

    @webapi_test_template
    def test_post_grant_implicit_no_uris(self):
        """Testing the POST <URL> API with GRANT_IMPLICIT and no URIs"""
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='',
            grant_type=Application.GRANT_IMPLICIT,
            is_valid=False,
        )

    @webapi_test_template
    def test_post_grant_implicit_uris(self):

        """Testing the POST <URL> API with GRANT_IMPLICIT and URIs"""
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='https://example.com/',
            grant_type=Application.GRANT_IMPLICIT,
            is_valid=True,
        )

    @webapi_test_template
    def test_post_grant_authorization_code_no_uris(self):
        """Testing the POST <URL> API with GRANT_AUTHORIZATION_CODE and no URIs
        """
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='',
            grant_type=Application.GRANT_AUTHORIZATION_CODE,
            is_valid=False,
        )

    @webapi_test_template
    def test_post_grant_authorization_code_uris(self):
        """Testing the POST <URL> API with GRANT_AUTHORIZATION_CODE and URIs"""
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='http://example.com',
            grant_type=Application.GRANT_AUTHORIZATION_CODE,
            is_valid=True,
        )

    @webapi_test_template
    def test_post_grant_password_no_uris(self):
        """Testing the POST <URL> API with GRANT_PASSWORD and no URIs"""
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='',
            grant_type=Application.GRANT_PASSWORD,
            is_valid=True,
        )

    @webapi_test_template
    def test_post_grant_password_uris(self):
        """Testing the POST <URL> API with GRANT_PASSWORD and URIs"""
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='http://example.com',
            grant_type=Application.GRANT_PASSWORD,
            is_valid=True,
        )

    @webapi_test_template
    def test_post_grant_client_credentials_no_uris(self):
        """Testing the POST <URL> API with GRANT_CLIENT_CREDENTIALS and no URIs
        """
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='',
            grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            is_valid=True,)

    @webapi_test_template
    def test_post_grant_client_credentials_uris(self):
        """Testing the POST <URL> API with GRANT_CLIENT_CREDENTIALS and URIs"""
        self._test_post_redirect_uri_grant_combination(
            redirect_uris='http://example.com',
            grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            is_valid=True,
        )

    @webapi_test_template
    def test_post_set_user(self):
        """Testing the POST <URL> API with user set"""
        rsp = self.api_post(
            get_oauth_app_list_url(),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'user': 'doc',
            },
            expected_status=400,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

        self.assertIn('fields', rsp)
        self.assertIn('user', rsp['fields'])
        self.assertEqual(rsp['fields']['user'],
                         ['You do not have permission to set this field.'])

    @webapi_test_template
    def test_post_set_user_as_superuser(self):
        """Testing the POST <URL> API as a superuser with user set"""
        self._login_user(admin=True)
        rsp = self.api_post(
            get_oauth_app_list_url(),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'user': 'doc',
            },
            expected_mimetype=oauth_app_item_mimetype,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        app = Application.objects.get(pk=rsp['oauth_app']['id'])
        self.compare_item(rsp['oauth_app'], app)
        self.assertEqual(app.user.username, 'doc')

    @webapi_test_template
    def test_post_set_user_as_superuser_not_exists(self):
        """Testing the POST <URL> API as a superuser with user set as a
        non-existent user
        """
        self._login_user(admin=True)
        rsp = self.api_post(
            get_oauth_app_list_url(),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'user': 'foofoo',
            },
            expected_status=400,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

        self.assertIn('fields', rsp)
        self.assertIn('user', rsp['fields'])
        self.assertEqual(rsp['fields']['user'],
                         ['The user "foofoo" does not exist.'])

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_set_user_as_local_site_admin(self):
        """Testing the POST <URL> API as a LocalSite admin with user set"""
        self._login_user(admin=True, local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)
        local_site.users.add(User.objects.get(username='dopey'))

        rsp = self.api_post(
            get_oauth_app_list_url(self.local_site_name),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'user': 'dopey',
            },
            expected_mimetype=oauth_app_item_mimetype,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        app = Application.objects.get(pk=rsp['oauth_app']['id'])
        self.compare_item(rsp['oauth_app'], app)
        self.assertEqual(app.user.username, 'dopey')

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_set_user_as_local_site_admin_with_non_local_site_user(self):
        """Testing the POST <URL> API as a LocalSite admin with user set to a
        non-LocalSite user
        """
        self._login_user(admin=True, local_site=True)

        rsp = self.api_post(
            get_oauth_app_list_url(self.local_site_name),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'user': 'dopey',
            },
            expected_status=400,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

        self.assertIn('fields', rsp)
        self.assertIn('user', rsp['fields'])
        self.assertEqual(
            rsp['fields']['user'],
            ['The user "dopey" does not exist.'],
        )

    @webapi_test_template
    def test_post_set_skip_authorization(self):
        """Testing the POST <URL> API with skip_authorization set"""
        rsp = self.api_post(
            get_oauth_app_list_url(),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'skip_authorization': '1',
            },
            expected_status=400,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

        self.assertIn('fields', rsp)
        self.assertIn('skip_authorization', rsp['fields'])
        self.assertEqual(rsp['fields']['skip_authorization'],
                         ['You do not have permission to set this field.'])

    @webapi_test_template
    def test_post_set_skip_authorization_as_superuser(self):
        """Testing the POST <URL> API as a superuser with skip_authorization"""
        self._login_user(admin=True)

        rsp = self.api_post(
            get_oauth_app_list_url(),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'skip_authorization': '1',
            },
            expected_mimetype=oauth_app_item_mimetype,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        app = Application.objects.get(pk=rsp['oauth_app']['id'])
        self.compare_item(rsp['oauth_app'], app)
        self.assertEqual(app.skip_authorization, True)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_set_skip_authorization_as_local_site_admin(self):
        """Testing the POST <URL> API as a LocalSite admin with
        skip_authorization set
        """
        self._login_user(admin=True, local_site=True)

        rsp = self.api_post(
            get_oauth_app_list_url(self.local_site_name),
            {
                'authorization_grant_type':
                    Application.GRANT_CLIENT_CREDENTIALS,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test-application',
                'redirect_uris': 'https://example.com/oauth/',
                'skip_authorization': '1',
            },
            expected_mimetype=oauth_app_item_mimetype,
        )

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        app = Application.objects.get(pk=rsp['oauth_app']['id'])
        self.compare_item(rsp['oauth_app'], app)
        self.assertEqual(app.skip_authorization, True)

    def _test_post_redirect_uri_grant_combination(self, redirect_uris,
                                                  grant_type, is_valid):
        """Test the redirect_uris and grant type are valid or invalid.

        Args:
            redirect_uris (unicode):
                A space-separated list of redirect URIs.

            grant_type (unicode):
                The grant type.

            is_valid (bool):
                Whether or not the given combination is valid. This determines
                the testing done on the response.
        """
        post_data = {
            'authorization_grant_type': grant_type,
            'client_type': Application.CLIENT_PUBLIC,
            'name': 'test-app',
            'redirect_uris': redirect_uris,
            'skip_authorization': '0',
        }

        if is_valid:
            rsp = self.api_post(get_oauth_app_list_url(),
                                post_data,
                                expected_mimetype=oauth_app_item_mimetype)
            self.assertIn('stat', rsp)
            self.assertEqual(rsp['stat'], 'ok')
            self.compare_item(rsp['oauth_app'],
                              Application.objects.get(name='test-app'))
        else:
            rsp = self.api_post(get_oauth_app_list_url(),
                                post_data,
                                expected_status=400)
            self.assertIn('stat', rsp)
            self.assertEqual(rsp['stat'], 'fail')
            self.assertIn('err', rsp)
            self.assertIn('fields', rsp)
            self.assertIn('redirect_uris', rsp['fields'])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, BaseWebAPITestCase):
    """Testing the OAuthApplicationResource item APIs."""

    resource = resources.oauth_app
    sample_api_url = 'oauth-apps/<app-id>/'
    fixtures = ['test_users']
    not_owner_status_code = 404
    not_owner_error = DOES_NOT_EXIST

    compare_item = _compare_item

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        app = self.create_oauth_application(user,
                                            with_local_site=with_local_site)

        return (get_oauth_app_item_url(app.pk, local_site_name),
                oauth_app_item_mimetype,
                app)

    @webapi_test_template
    def test_get_without_owner(self):
        """Testing the GET <URL> API without owner"""
        app = self.create_oauth_application(User.objects.get(username='admin'))

        self.api_get(get_oauth_app_item_url(app.pk),
                     expected_status=404)

    @webapi_test_template
    def test_get_without_owner_as_superuser(self):
        """Testing the GET <URL> API without owner as superuser"""
        self.user = self._login_user(admin=True)
        app = self.create_oauth_application(User.objects.get(username='doc'))

        rsp = self.api_get(get_oauth_app_item_url(app.pk),
                           expected_mimetype=oauth_app_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('oauth_app', rsp)
        self.compare_item(rsp['oauth_app'], app)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_without_local_site(self):
        """Testing the GET <URL> API for an app related to a LocalSite"""
        local_site = LocalSite.objects.get(pk=1)
        local_site.users.add(self.user)
        app = self.create_oauth_application(
            self.user,
            local_site=LocalSite.objects.get(pk=1))

        rsp = self.api_get(get_oauth_app_item_url(app.pk),
                           expected_status=404)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_invalid_local_site(self):
        """Testing the GET <URL> API with an app related to a LocalSite not
        using the LocalSite's API
        """
        local_site = LocalSite.objects.get(pk=1)
        local_site.users.add(self.user)
        app = self.create_oauth_application(self.user)

        rsp = self.api_get(get_oauth_app_item_url(app.pk, local_site.name),
                           expected_status=404)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_without_owner_as_local_site_admin(self):
        """Testing the GET <URL> API without owner on a LocalSite as a
        LocalSite admin
        """
        local_site = LocalSite.objects.get(pk=1)
        local_site.users.add(self.user)
        app = self.create_oauth_application(self.user, local_site=local_site)
        self.user = self._login_user(admin=True, local_site=True)

        rsp = self.api_get(get_oauth_app_item_url(app.pk, local_site.name),
                           expected_mimetype=oauth_app_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('oauth_app', rsp)
        self.compare_item(rsp['oauth_app'], app)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        app = self.create_oauth_application(user,
                                            with_local_site=with_local_site)

        if put_valid_data:
            request_data = {
                'extra_data.fake_key': '',
            }
        else:
            request_data = {
                'user': 'admin',
            }

        return (get_oauth_app_item_url(app.pk, local_site_name),
                oauth_app_item_mimetype,
                request_data,
                app,
                [])

    def check_put_result(self, user, item_rsp, app):
        app = Application.objects.get(pk=app.pk)
        self.compare_item(item_rsp, app)

    @add_fixtures(['test_site'])
    def test_put_re_enable_security_disabled(self):
        """Testing the PUT <URL> API with enabled=1 for an application disabled
        due to security
        """
        self.user = self._login_user(admin=True)
        doc = User.objects.get(username='doc')
        local_site = LocalSite.objects.get(pk=1)
        app = self.create_oauth_application(user=doc, local_site=local_site)

        original_secret = app.client_secret

        local_site.users.remove(doc)

        app = Application.objects.get(pk=app.pk)

        self.assertTrue(app.is_disabled_for_security)
        self.assertEqual(app.user, self.user)
        self.assertEqual(app.original_user, doc)

        rsp = self.api_put(get_oauth_app_item_url(app.pk, local_site.name),
                           {'enabled': '1'},
                           expected_status=400)

        app = Application.objects.get(pk=app.pk)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('fields', rsp)
        self.assertIn('__all__', rsp['fields'])
        self.assertEqual(rsp['fields']['__all__'][0],
                         ApplicationChangeForm.DISABLED_FOR_SECURITY_ERROR)
        self.assertEqual(app.original_user, doc)
        self.assertEqual(app.client_secret, original_secret)

    def test_put_regenerate_secret_key(self):
        """Testing the PUT <URL> API with regenerate_client_secret=1"""
        app = self.create_oauth_application(user=self.user)
        original_secret = app.client_secret

        rsp = self.api_put(get_oauth_app_item_url(app.pk),
                           {'regenerate_client_secret': 1},
                           expected_mimetype=oauth_app_item_mimetype)

        app = Application.objects.get(pk=app.pk)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.compare_item(rsp['oauth_app'], app)
        self.assertNotEqual(app.client_secret, original_secret)

    @add_fixtures(['test_site'])
    def test_put_regenerate_secret_key_enable(self):
        """Testing the PUT <URL> API with regenerate_secret_key=1 and enabled=1
        """
        self.user = self._login_user(admin=True)
        doc = User.objects.get(username='doc')
        local_site = LocalSite.objects.get(pk=1)
        app = self.create_oauth_application(user=doc, local_site=local_site)

        original_secret = app.client_secret

        local_site.users.remove(doc)

        app = Application.objects.get(pk=app.pk)

        self.assertTrue(app.is_disabled_for_security)
        self.assertEqual(app.user, self.user)
        self.assertEqual(app.original_user, doc)

        rsp = self.api_put(
            get_oauth_app_item_url(app.pk, local_site.name),
            {
                'enabled': '1',
                'regenerate_client_secret': '1',
            },
            expected_mimetype=oauth_app_item_mimetype)

        app = Application.objects.get(pk=app.pk)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['oauth_app']
        self.compare_item(item_rsp, app)
        self.assertNotEqual(item_rsp['client_secret'], original_secret)

        self.assertFalse(app.is_disabled_for_security)
        self.assertIsNone(app.original_user)
        self.assertTrue(app.enabled)
        self.assertNotEqual(app.client_secret, original_secret)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        app = self.create_oauth_application(user=user,
                                            with_local_site=with_local_site)

        return (get_oauth_app_item_url(app.pk, local_site_name),
                [app.pk])

    def check_delete_result(self, user, app_pk):
        self.assertIsNone(get_object_or_none(Application, pk=app_pk))
