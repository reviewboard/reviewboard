from __future__ import unicode_literals

from django.contrib.auth.models import Permission, User
from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.webapi.testing.decorators import webapi_test_template
from kgb import SpyAgency

from reviewboard.accounts.backends import (AuthBackend,
                                           get_enabled_auth_backends)
from reviewboard.accounts.models import Profile
from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (user_item_mimetype,
                                                user_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_user_item_url,
                                           get_user_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(SpyAgency, BaseWebAPITestCase):
    """Testing the UserResource list API tests."""
    fixtures = ['test_users']
    sample_api_url = 'users/'
    resource = resources.user

    test_http_methods = ('GET',)

    def setup_http_not_allowed_list_test(self, user):
        return get_user_list_url()

    def compare_item(self, item_rsp, obj):
        self.assertEqual(item_rsp['id'], obj.pk)
        self.assertEqual(item_rsp['username'], obj.username)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if not populate_items:
            items = []
        elif with_local_site:
            local_site = self.get_local_site(name=local_site_name)
            items = list(local_site.users.all())
        else:
            items = list(User.objects.all())

        return (get_user_list_url(local_site_name),
                user_list_mimetype,
                items)

    def test_get_with_q(self):
        """Testing the GET users/?q= API"""
        rsp = self.api_get(get_user_list_url(), {'q': 'gru'},
                           expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 1)  # grumpy

    def test_query_users_auth_backend(self):
        """Testing the GET users/?q= API
        with AuthBackend.query_users failure
        """
        class SandboxAuthBackend(AuthBackend):
            backend_id = 'test-id'
            name = 'test'

            def query_users(self, query, request):
                raise Exception

        backend = SandboxAuthBackend()

        self.spy_on(get_enabled_auth_backends, call_fake=lambda: [backend])
        self.spy_on(backend.query_users)

        rsp = self.api_get(get_user_list_url(), {'q': 'gru'},
                           expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue(backend.query_users.called)

    def test_search_users_auth_backend(self):
        """Testing the GET users/?q= API
        with AuthBackend.search_users failure
        """
        class SandboxAuthBackend(AuthBackend):
            backend_id = 'test-id'
            name = 'test'

            def search_users(self, query, request):
                raise Exception

        backend = SandboxAuthBackend()

        self.spy_on(get_enabled_auth_backends, call_fake=lambda: [backend])
        self.spy_on(backend.search_users)

        rsp = self.api_get(get_user_list_url(), {'q': 'gru'},
                           expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue(backend.search_users.called)

    #
    # HTTP POST tests
    #
    @webapi_test_template
    def test_post_anonymous(self):
        """Testing the POST <URL> API as an anonymous user"""
        self.client.logout()
        rsp = self.api_post(
            get_user_list_url(),
            {
                'username': 'username',
                'password': 'password',
                'email': 'email@example.com',
            },
            expected_status=401)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('err', rsp)
        self.assertIn('code', rsp['err'])
        self.assertEqual(rsp['err']['code'], 103)

    @webapi_test_template
    def test_post(self):
        """Testing the POST <URL> API as a regular user"""
        rsp = self.api_post(
            get_user_list_url(),
            {
                'username': 'username',
                'password': 'password',
                'email': 'email@example.com'
            },
            expected_status=403)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('err', rsp)
        self.assertIn('code', rsp['err'])
        self.assertEqual(rsp['err']['code'], 101)

    @webapi_test_template
    def test_post_superuser(self):
        """Testing the POST <URL> API as a superuser"""
        self.client.login(username='admin', password='admin')

        rsp = self.api_post(
            get_user_list_url(),
            {
                'username': 'username',
                'password': 'password',
                'email': 'email@example.com',
            },
            expected_mimetype=user_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.compare_item(rsp['user'], User.objects.get(username='username'))

    @webapi_test_template
    def test_post_auth_add_user_perm(self):
        """Testing the POST <URL> API as a user with the auth.add_user
        permission
        """
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label='auth',
                                   codename='add_user'))

        rsp = self.api_post(
            get_user_list_url(),
            {
                'username': 'username',
                'password': 'password',
                'email': 'email@example.com',
            },
            expected_mimetype=user_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.compare_item(rsp['user'], User.objects.get(username='username'))

    @webapi_test_template
    def test_post_local_site(self):
        """Testing the POST <URL> API with a local site"""
        local_site = LocalSite.objects.create(name='test', public=True)

        self.client.login(username='admin', password='admin')
        rsp = self.api_post(
            get_user_list_url(local_site.name),
            {
                'username': 'username',
                'password': 'password',
                'email': 'email@example.com'
            },
            expected_status=403)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('err', rsp)
        self.assertIn('code', rsp['err'])
        self.assertEqual(rsp['err']['code'], 101)

    @webapi_test_template
    def test_post_duplicate_username(self):
        """Testing the POST <URL> API for a username that already exists"""
        self.client.login(username='admin', password='admin')
        rsp = self.api_post(
            get_user_list_url(),
            {
                'username': 'doc',
                'password': 'password',
                'email': 'doc@example.com'
            },
            expected_status=400)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('fields', rsp)
        self.assertIn('username', rsp['fields'])

    @webapi_test_template
    def test_post_invalid_email(self):
        """Testing the POST <URL> API for an invalid e-mail address"""
        self.client.login(username='admin', password='admin')
        rsp = self.api_post(
            get_user_list_url(),
            {
                'username': 'username',
                'password': 'password',
                'email': 'invalid e-mail',
            },
            expected_status=400)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('fields', rsp)
        self.assertIn('email', rsp['fields'])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the UserResource item API tests."""
    fixtures = ['test_users']
    sample_api_url = 'users/<username>/'
    resource = resources.user

    def setup_http_not_allowed_item_test(self, user):
        return get_user_item_url(user.username)

    def compare_item(self, item_rsp, user):
        self.assertEqual(item_rsp['id'], user.pk)
        self.assertEqual(item_rsp['username'], user.username)
        self.assertEqual(item_rsp['first_name'], user.first_name)
        self.assertEqual(item_rsp['last_name'], user.last_name)
        self.assertEqual(item_rsp['email'], user.email)

        # There's no simple way to test the specific URLs that are returned,
        # but we can at least make sure everything we expect to be present is
        # present.
        self.assertIn('avatar_url', item_rsp)
        self.assertIn('1x', item_rsp['avatar_urls'])
        self.assertIn('2x', item_rsp['avatar_urls'])

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        return (get_user_item_url(user.username, local_site_name),
                user_item_mimetype,
                user)

    def test_get_not_modified(self):
        """Testing the GET users/<username>/ API with Not Modified response"""
        self._testHttpCaching(get_user_item_url('doc'),
                              check_etags=True)

    @add_fixtures(['test_site'])
    def test_get_with_site_and_profile_private(self):
        """Testing the GET users/<username>/ API
        with a local site and private profile
        """
        self._login_user(local_site=True)

        username = 'admin'
        user = User.objects.get(username=username)

        profile, is_new = Profile.objects.get_or_create(user=user)
        profile.is_private = True
        profile.save()

        rsp = self.api_get(get_user_item_url(username, self.local_site_name),
                           expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertNotIn('first_name', rsp['user'])
        self.assertNotIn('last_name', rsp['user'])
        self.assertNotIn('email', rsp['user'])

    @add_fixtures(['test_site'])
    def test_get_missing_user_with_site(self):
        """Testing the GET users/<username>/ API with a local site"""
        self._login_user(local_site=True)
        self.api_get(get_user_item_url('dopey', self.local_site_name),
                     expected_status=404)
