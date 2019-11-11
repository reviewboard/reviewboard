from __future__ import unicode_literals

import logging

from django.contrib.auth.models import Permission, User
from django.utils import six
from djblets.avatars.services.base import AvatarService
from djblets.avatars.services.gravatar import GravatarService
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST
from djblets.webapi.testing.decorators import webapi_test_template
from kgb import SpyAgency

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.backends.registry import get_enabled_auth_backends
from reviewboard.avatars import avatar_services
from reviewboard.avatars.testcase import AvatarServicesTestMixin
from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (user_item_mimetype,
                                                user_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_user_item_url,
                                           get_user_list_url)


class NoProfileAuthBackend(BaseAuthBackend):
    backend_id = 'test-no-profile'
    supports_change_name = False
    supports_change_email = False


class BrokenUpdateProfileAuthBackend(BaseAuthBackend):
    backend_id = 'test-broken-profile'
    supports_change_name = True
    supports_change_email = True

    def update_name(self, user):
        raise Exception('oh no')

    def update_email(self, user):
        raise Exception('oh no')


class NoURLAvatarService(AvatarService):
    """An avatar services that returns no URLs."""

    avatar_service_id = 'no-urls'
    name = 'No URLs For You'

    def get_avatar_urls_uncached(self, user, size):
        """Return no URLs."""
        return {}


class SimpleRenderAvatarService(NoURLAvatarService):
    """An avatar services that has simple, testable rendered output."""

    avatar_service_id = 'simple-renders'
    name = 'Simple Renders'

    def render(self, request, user, size, **kwargs):
        return '<div class="avatar" data-size="%s">%s</div>' % (size,
                                                                user.username)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(AvatarServicesTestMixin, SpyAgency,
                        BaseWebAPITestCase):
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

    @webapi_test_template
    def test_get_filter_inactive(self):
        """Testing the GET <URL> API filters out inactive users by default"""
        dopey = User.objects.get(username='dopey')
        dopey.is_active = False
        dopey.save()

        rsp = self.api_get(get_user_list_url(),
                           expected_mimetype=user_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        user_pks = [user['id'] for user in rsp['users']]
        returned_users = set(User.objects.filter(pk__in=user_pks))
        expected_users = set(User.objects.filter(is_active=True))
        self.assertEqual(returned_users, expected_users)

    @webapi_test_template
    def test_get_include_inactive(self):
        """Testing the GET <URL>/?include-inactive=1 API includes inactive
        users
        """
        dopey = User.objects.get(username='dopey')
        dopey.is_active = False
        dopey.save()

        rsp = self.api_get(get_user_list_url(), {'include-inactive': '1'},
                           expected_mimetype=user_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        user_pks = [user['id'] for user in rsp['users']]
        self.assertEqual(set(User.objects.filter(pk__in=user_pks)),
                         set(User.objects.all()))

    @webapi_test_template
    def test_get_include_inactive_true(self):
        """Testing the GET <URL>/?include-inactive=true API includes inactive
        users
        """
        dopey = User.objects.get(username='dopey')
        dopey.is_active = False
        dopey.save()

        rsp = self.api_get(get_user_list_url(), {'include-inactive': 'true'},
                           expected_mimetype=user_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        user_pks = [user['id'] for user in rsp['users']]
        self.assertEqual(set(User.objects.filter(pk__in=user_pks)),
                         set(User.objects.all()))

    def test_get_with_q(self):
        """Testing the GET users/?q= API"""
        rsp = self.api_get(get_user_list_url(), {'q': 'gru'},
                           expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 1)  # grumpy

    @webapi_test_template
    def test_get_with_render_avatars_at(self):
        """Testing the GET <URL> API with ?render-avatars-at=..."""
        avatar_services.register(SimpleRenderAvatarService)
        avatar_services.enable_service(SimpleRenderAvatarService, save=False)
        avatar_services.set_default_service(SimpleRenderAvatarService)

        rsp = self.api_get(
            get_user_list_url(),
            {
                'render-avatars-at': '24,abc,48,,128',
            },
            expected_mimetype=user_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 4)
        self.assertEqual(
            rsp['users'][0]['avatar_html'],
            {
                '24': '<div class="avatar" data-size="24">admin</div>',
                '48': '<div class="avatar" data-size="48">admin</div>',
                '128': '<div class="avatar" data-size="128">admin</div>',
            })

        self.assertEqual(
            rsp['users'][1]['avatar_html'],
            {
                '24': '<div class="avatar" data-size="24">doc</div>',
                '48': '<div class="avatar" data-size="48">doc</div>',
                '128': '<div class="avatar" data-size="128">doc</div>',
            })

        self.assertEqual(
            rsp['users'][2]['avatar_html'],
            {
                '24': '<div class="avatar" data-size="24">dopey</div>',
                '48': '<div class="avatar" data-size="48">dopey</div>',
                '128': '<div class="avatar" data-size="128">dopey</div>',
            })

        self.assertEqual(
            rsp['users'][3]['avatar_html'],
            {
                '24': '<div class="avatar" data-size="24">grumpy</div>',
                '48': '<div class="avatar" data-size="48">grumpy</div>',
                '128': '<div class="avatar" data-size="128">grumpy</div>',
            })

    def test_populate_users_auth_backend(self):
        """Testing the GET users/?q= API with BaseAuthBackend.populate_users
        failure
        """
        class SandboxAuthBackend(BaseAuthBackend):
            backend_id = 'test-id'
            name = 'test'

            def populate_users(self, query, request, **kwargs):
                raise Exception

        backend = SandboxAuthBackend()

        self.spy_on(get_enabled_auth_backends, call_fake=lambda: [backend])
        self.spy_on(backend.populate_users)

        rsp = self.api_get(get_user_list_url(), {'q': 'gru'},
                           expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue(backend.populate_users.called)

    def test_build_search_users_query_auth_backend(self):
        """Testing the GET users/?q= API with
        BaseAuthBackend.build_search_users_query failure
        """
        class SandboxAuthBackend(BaseAuthBackend):
            backend_id = 'test-id'
            name = 'test'

            def build_search_users_query(self, query, request, **kwargs):
                raise Exception

        backend = SandboxAuthBackend()

        self.spy_on(get_enabled_auth_backends, call_fake=lambda: [backend])
        self.spy_on(backend.build_search_users_query)

        rsp = self.api_get(get_user_list_url(), {'q': 'gru'},
                           expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue(backend.build_search_users_query.called)

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
        self.assertEqual(rsp['fields'], {
            'email': ['Enter a valid email address.'],
        })

    @webapi_test_template
    def test_post_with_render_avatars_at(self):
        """Testing the POST <URL> API with render_avatars_at=..."""
        self.client.login(username='admin', password='admin')

        avatar_services.register(SimpleRenderAvatarService)
        avatar_services.enable_service(SimpleRenderAvatarService, save=False)
        avatar_services.set_default_service(SimpleRenderAvatarService)

        rsp = self.api_post(
            get_user_list_url(),
            {
                'username': 'myuser',
                'password': 'mypass',
                'email': 'myuser@example.com',
                'render_avatars_at': '24,abc,48,,128',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['user']['avatar_html'],
            {
                '24': '<div class="avatar" data-size="24">myuser</div>',
                '48': '<div class="avatar" data-size="48">myuser</div>',
                '128': '<div class="avatar" data-size="128">myuser</div>',
            })


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(AvatarServicesTestMixin, SpyAgency,
                        BaseWebAPITestCase):
    """Testing the UserResource item API tests."""
    fixtures = ['test_users']
    sample_api_url = 'users/<username>/'
    resource = resources.user
    test_http_methods = ('GET',)

    def setUp(self):
        super(ResourceItemTests, self).setUp()

        avatar_services.enable_service(GravatarService, save=False)

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

        # By default, avatars are not rendered.
        self.assertIsNone(item_rsp['avatar_html'])

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

    def test_get_with_site_and_profile_private(self):
        """Testing the GET users/<username>/ API with a local site and private
        profile
        """
        username = 'admin'
        user = User.objects.get(username=username)

        site = LocalSite.objects.create(name=self.local_site_name)
        site.users = [user, self.user]

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        rsp = self.api_get(get_user_item_url(username, self.local_site_name),
                           expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertNotIn('first_name', rsp['user'])
        self.assertNotIn('last_name', rsp['user'])
        self.assertNotIn('email', rsp['user'])

    @add_fixtures(['test_site'])
    def test_get_with_site_and_profile_private_as_site_admin(self):
        """Testing the GET users/<username>/ API with a local site and private
        profile as a LocalSite admin
        """
        self._login_user(local_site=True)

        username = 'admin'
        user = User.objects.get(username=username)

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        rsp = self.api_get(get_user_item_url(username, self.local_site_name),
                           expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['user']
        self.assertEqual(item_rsp['username'], user.username)
        self.assertEqual(item_rsp['first_name'], user.first_name)
        self.assertEqual(item_rsp['last_name'], user.last_name)
        self.assertEqual(item_rsp['email'], user.email)

    @add_fixtures(['test_site'])
    def test_get_missing_user_with_site(self):
        """Testing the GET users/<username>/ API with a local site"""
        self._login_user(local_site=True)
        self.api_get(get_user_item_url('dopey', self.local_site_name),
                     expected_status=404)

    @webapi_test_template
    def test_get_with_profile_private_and_only_fields(self):
        """Testing the GET <URL> API with a private profile and ?only-fields=
        """
        username = 'dopey'
        user = User.objects.get(username=username)

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        rsp = self.api_get(
            '%s?only-fields=username' % get_user_item_url(username),
            expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertNotIn('first_name', rsp['user'])
        self.assertNotIn('last_name', rsp['user'])
        self.assertNotIn('email', rsp['user'])

    @webapi_test_template
    def test_get_inactive_user(self):
        """Testing the GET <URL> API for an inactive user"""
        dopey = User.objects.get(username='dopey')
        dopey.is_active = False
        dopey.save()

        rsp = self.api_get(get_user_item_url('dopey'),
                           expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['is_active'], False)

    @webapi_test_template
    def test_get_avatar_service_no_urls(self):
        """Testing the GET <URL> API when the avatar service returns no URLs
        """
        avatar_services.register(NoURLAvatarService)
        avatar_services.enable_service(NoURLAvatarService, save=False)

        dopey = User.objects.get(username='dopey')
        settings_mgr = avatar_services.settings_manager_class(dopey)
        settings_mgr.avatar_service_id = NoURLAvatarService.avatar_service_id
        settings_mgr.save()

        rsp = self.api_get(get_user_item_url('dopey'),
                           expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        user_rsp = rsp['user']
        self.assertIn('avatar_url', user_rsp)
        self.assertIsNone(user_rsp['avatar_url'])
        self.assertIn('avatar_urls', user_rsp)
        self.assertEqual(user_rsp['avatar_urls'], {})

    @webapi_test_template
    def test_get_with_render_avatars_at(self):
        """Testing the GET <URL> API with ?render-avatars-at=..."""
        avatar_services.register(SimpleRenderAvatarService)
        avatar_services.enable_service(SimpleRenderAvatarService, save=False)
        avatar_services.set_default_service(SimpleRenderAvatarService)

        rsp = self.api_get(
            get_user_item_url('dopey'),
            {
                'render-avatars-at': '24,abc,48,,128',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['user']['avatar_html'],
            {
                '24': '<div class="avatar" data-size="24">dopey</div>',
                '48': '<div class="avatar" data-size="48">dopey</div>',
                '128': '<div class="avatar" data-size="128">dopey</div>',
            })

    #
    # HTTP PUT tests
    #

    @webapi_test_template
    def test_put_with_user_not_found(self):
        """Testing the PUT <URL> API with username not found"""
        self._login_user(admin=True)

        rsp = self.api_put(
            get_user_item_url('bad-username'),
            {
                'first_name': 'new-first-name',
            },
            expected_status=404)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @webapi_test_template
    def test_put_profile_fields_as_same_user(self):
        """Testing the PUT <URL> API with profile fields as user being
        modified
        """
        auth_backend = get_enabled_auth_backends()[0]
        self.spy_on(auth_backend.update_name)
        self.spy_on(auth_backend.update_email)

        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'first_name': 'new-first-name',
                'last_name': 'new-last-name',
                'email': 'new-email@example.com',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        user_rsp = rsp['user']
        self.assertEqual(user_rsp['first_name'], 'new-first-name')
        self.assertEqual(user_rsp['last_name'], 'new-last-name')
        self.assertEqual(user_rsp['email'], 'new-email@example.com')

        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.first_name, 'new-first-name')
        self.assertEqual(user.last_name, 'new-last-name')
        self.assertEqual(user.email, 'new-email@example.com')

        self.assertTrue(auth_backend.update_name.called_with(user))
        self.assertTrue(auth_backend.update_email.called_with(user))

    @webapi_test_template
    def test_put_profile_fields_as_other_user(self):
        """Testing the PUT <URL> API with profile fields as other user"""
        user = self.create_user(username='test-user',
                                password='test-user')

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'first_name': 'new-first-name',
                'last_name': 'new-last-name',
                'email': 'new-email@example.com',
            },
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

    @webapi_test_template
    def test_put_profile_fields_as_superuser(self):
        """Testing the PUT <URL> API with profile fields as superuser"""
        auth_backend = get_enabled_auth_backends()[0]
        self.spy_on(auth_backend.update_name)
        self.spy_on(auth_backend.update_email)

        user = self.create_user(username='test-user',
                                password='test-user')
        self._login_user(admin=True)

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'first_name': 'new-first-name',
                'last_name': 'new-last-name',
                'email': 'new-email@example.com',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        user_rsp = rsp['user']
        self.assertEqual(user_rsp['first_name'], 'new-first-name')
        self.assertEqual(user_rsp['last_name'], 'new-last-name')
        self.assertEqual(user_rsp['email'], 'new-email@example.com')

        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.first_name, 'new-first-name')
        self.assertEqual(user.last_name, 'new-last-name')
        self.assertEqual(user.email, 'new-email@example.com')

        self.assertTrue(auth_backend.update_name.called_with(user))
        self.assertTrue(auth_backend.update_email.called_with(user))

    @webapi_test_template
    def test_put_profile_fields_as_user_with_perm(self):
        """Testing the PUT <URL> API with profile fields as user with
        auth.change_user permission
        """
        auth_backend = get_enabled_auth_backends()[0]
        self.spy_on(auth_backend.update_name)
        self.spy_on(auth_backend.update_email)

        user = self.create_user(username='test-user',
                                password='test-user')

        self.create_user(username='login-user',
                         password='login-user',
                         perms=[('auth', 'change_user')])
        self.assertTrue(self.client.login(username='login-user',
                                          password='login-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'first_name': 'new-first-name',
                'last_name': 'new-last-name',
                'email': 'new-email@example.com',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        user_rsp = rsp['user']
        self.assertEqual(user_rsp['first_name'], 'new-first-name')
        self.assertEqual(user_rsp['last_name'], 'new-last-name')
        self.assertEqual(user_rsp['email'], 'new-email@example.com')

        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.first_name, 'new-first-name')
        self.assertEqual(user.last_name, 'new-last-name')
        self.assertEqual(user.email, 'new-email@example.com')

        self.assertTrue(auth_backend.update_name.called_with(user))
        self.assertTrue(auth_backend.update_email.called_with(user))

    @webapi_test_template
    def test_put_with_invalid_email_field(self):
        """Testing the PUT <URL> API with invalid e-mail field"""
        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'email': 'bad-email',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('fields', rsp)
        self.assertEqual(rsp['fields'], {
            'email': ['Enter a valid email address.'],
        })

    @webapi_test_template
    def test_put_with_full_name_and_no_backend_support(self):
        """Testing the PUT <URL> API with setting first_name or last_name
        with auth_backend.supports_change_name == False
        """
        self.spy_on(get_enabled_auth_backends,
                    call_fake=lambda: [NoProfileAuthBackend()])

        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'first_name': 'new_first_name',
                'last_name': 'new_last_name',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('fields', rsp)
        self.assertEqual(rsp['fields'], {
            'first_name': ['The configured auth backend does not allow names '
                           'to be changed.'],
            'last_name': ['The configured auth backend does not allow names '
                          'to be changed.'],
        })

    @webapi_test_template
    def test_put_with_email_and_no_backend_support(self):
        """Testing the PUT <URL> API with setting email with
        auth_backend.supports_change_email == False
        """
        self.spy_on(get_enabled_auth_backends,
                    call_fake=lambda: [NoProfileAuthBackend()])

        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'email': 'new@example.com',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('fields', rsp)
        self.assertEqual(rsp['fields'], {
            'email': ['The configured auth backend does not allow e-mail '
                      'addresses to be changed.'],
        })

    @webapi_test_template
    def test_put_with_update_namel_failure(self):
        """Testing the PUT <URL> API with auth_backend.update_name() failure"""
        auth_backend = BrokenUpdateProfileAuthBackend()
        logger = logging.getLogger('reviewboard.webapi.resources.user')

        self.spy_on(get_enabled_auth_backends,
                    call_fake=lambda: [auth_backend])
        self.spy_on(logger.exception)

        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'first_name': 'new-first-name',
                'last_name': 'new-last-name',
            },
            expected_mimetype=user_item_mimetype)

        user_rsp = rsp['user']
        self.assertEqual(user_rsp['first_name'], 'new-first-name')
        self.assertEqual(user_rsp['last_name'], 'new-last-name')

        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.first_name, 'new-first-name')
        self.assertEqual(user.last_name, 'new-last-name')

        self.assertTrue(logger.exception.called_with(
            'Error when calling update_name for auth backend %r for user '
            'ID %s: %s',
            auth_backend, user.pk))

    @webapi_test_template
    def test_put_with_update_email_failure(self):
        """Testing the PUT <URL> API with auth_backend.update_email() failure
        """
        auth_backend = BrokenUpdateProfileAuthBackend()
        logger = logging.getLogger('reviewboard.webapi.resources.user')

        self.spy_on(get_enabled_auth_backends,
                    call_fake=lambda: [auth_backend])
        self.spy_on(logger.exception)

        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'email': 'new@example.com',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['user']['email'], 'new@example.com')

        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.email, 'new@example.com')

        self.assertTrue(logger.exception.called_with(
            'Error when calling update_email for auth backend %r for user '
            'ID %s: %s',
            auth_backend, user.pk))

    @webapi_test_template
    def test_put_is_active_as_same_user(self):
        """Testing the PUT <URL> API with is_active field as user being
        modified
        """
        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'is_active': 'false',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('fields', rsp)
        self.assertEqual(rsp['fields'], {
            'is_active': [
                'This field can only be set by administrators and users '
                'with the auth.change_user permission.'
            ],
        })

        user = User.objects.get(pk=user.pk)
        self.assertTrue(user.is_active)

    @webapi_test_template
    def test_put_is_active_as_superuser(self):
        """Testing the PUT <URL> API with is_active field as superuser"""
        user = self.create_user(username='test-user',
                                password='test-user')
        self._login_user(admin=True)

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'is_active': 'false',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        user_rsp = rsp['user']
        self.assertFalse(user_rsp['is_active'])

        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.is_active)

    @webapi_test_template
    def test_put_is_active_as_user_with_perm(self):
        """Testing the PUT <URL> API with profile fields as user with
        auth.change_user permission
        """
        user = self.create_user(username='test-user',
                                password='test-user')

        self.create_user(username='login-user',
                         password='login-user',
                         perms=[('auth', 'change_user')])
        self.assertTrue(self.client.login(username='login-user',
                                          password='login-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'is_active': 'false',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        user_rsp = rsp['user']
        self.assertFalse(user_rsp['is_active'])

        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.is_active)

    @webapi_test_template
    def test_put_with_render_avatars_at(self):
        """Testing the PUT <URL> API with render_avatars_at=..."""
        avatar_services.register(SimpleRenderAvatarService)
        avatar_services.enable_service(SimpleRenderAvatarService, save=False)
        avatar_services.set_default_service(SimpleRenderAvatarService)

        user = self.create_user(username='test-user',
                                password='test-user')
        self.assertTrue(self.client.login(username='test-user',
                                          password='test-user'))

        rsp = self.api_put(
            get_user_item_url(user.username),
            {
                'first_name': 'new-name',
                'render_avatars_at': '24,abc,48,,128',
            },
            expected_mimetype=user_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['user']['avatar_html'],
            {
                '24': '<div class="avatar" data-size="24">test-user</div>',
                '48': '<div class="avatar" data-size="48">test-user</div>',
                '128': '<div class="avatar" data-size="128">test-user</div>',
            })
