from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (user_item_mimetype,
                                                user_list_mimetype)
from reviewboard.webapi.tests.urls import (get_user_item_url,
                                           get_user_list_url)


class UserResourceTests(BaseWebAPITestCase):
    """Testing the UserResource API tests."""
    fixtures = ['test_users']

    #
    # List tests
    #

    def test_get_users(self):
        """Testing the GET users/ API"""
        rsp = self.apiGet(get_user_list_url(),
                          expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), User.objects.count())

    def test_get_users_with_q(self):
        """Testing the GET users/?q= API"""
        rsp = self.apiGet(get_user_list_url(), {'q': 'gru'},
                          expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 1)  # grumpy

    @add_fixtures(['test_site'])
    def test_get_users_with_site(self):
        """Testing the GET users/ API with a local site"""
        self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)
        rsp = self.apiGet(get_user_list_url(self.local_site_name),
                          expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), local_site.users.count())

    @add_fixtures(['test_site'])
    def test_get_users_with_site_no_access(self):
        """Testing the GET users/ API
        with a local site and Permission Denied error
        """
        self.apiGet(get_user_list_url(self.local_site_name),
                    expected_status=403)

    #
    # Item tests
    #

    def test_get_user(self):
        """Testing the GET users/<username>/ API"""
        username = 'doc'
        user = User.objects.get(username=username)
        profile = Profile.objects.get(user=user)
        self.assertFalse(profile.is_private)

        rsp = self.apiGet(get_user_item_url(username),
                          expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertEqual(rsp['user']['first_name'], user.first_name)
        self.assertEqual(rsp['user']['last_name'], user.last_name)
        self.assertEqual(rsp['user']['id'], user.id)
        self.assertEqual(rsp['user']['email'], user.email)

    def test_get_user_not_modified(self):
        """Testing the GET users/<username>/ API with Not Modified response"""
        self._testHttpCaching(get_user_item_url('doc'),
                              check_etags=True)

    @add_fixtures(['test_site'])
    def test_get_user_with_site(self):
        """Testing the GET users/<username>/ API with a local site"""
        self._login_user(local_site=True)

        username = 'doc'
        user = User.objects.get(username=username)
        profile = Profile.objects.get(user=user)
        self.assertFalse(profile.is_private)

        rsp = self.apiGet(get_user_item_url(username, self.local_site_name),
                          expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertEqual(rsp['user']['first_name'], user.first_name)
        self.assertEqual(rsp['user']['last_name'], user.last_name)
        self.assertEqual(rsp['user']['id'], user.id)
        self.assertEqual(rsp['user']['email'], user.email)

    @add_fixtures(['test_site'])
    def test_get_user_with_site_and_profile_private(self):
        """Testing the GET users/<username>/ API
        with a local site and private profile
        """
        self._login_user(local_site=True)

        username = 'admin'
        user = User.objects.get(username=username)

        profile, is_new = Profile.objects.get_or_create(user=user)
        profile.is_private = True
        profile.save()

        rsp = self.apiGet(get_user_item_url(username, self.local_site_name),
                          expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertFalse('first_name' in rsp['user'])
        self.assertFalse('last_name' in rsp['user'])
        self.assertFalse('email' in rsp['user'])

    @add_fixtures(['test_site'])
    def test_get_missing_user_with_site(self):
        """Testing the GET users/<username>/ API with a local site"""
        self._login_user(local_site=True)
        self.apiGet(get_user_item_url('dopey', self.local_site_name),
                    expected_status=404)

    @add_fixtures(['test_site'])
    def test_get_user_with_site_no_access(self):
        """Testing the GET users/<username>/ API
        with a local site and Permission Denied error
        """
        print self.fixtures
        self.apiGet(get_user_item_url('doc', self.local_site_name),
                    expected_status=403)
