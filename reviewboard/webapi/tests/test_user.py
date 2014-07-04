from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.testing.decorators import add_fixtures

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
class ResourceListTests(BaseWebAPITestCase):
    """Testing the UserResource list API tests."""
    fixtures = ['test_users']
    sample_api_url = 'users/'
    resource = resources.user

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
            local_site = LocalSite.objects.get(name=local_site_name)
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
