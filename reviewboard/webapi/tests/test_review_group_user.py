from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import Group
from reviewboard.site.models import LocalSite
from reviewboard.webapi.errors import INVALID_USER
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (user_item_mimetype,
                                                user_list_mimetype)
from reviewboard.webapi.tests.urls import (get_review_group_user_item_url,
                                           get_review_group_user_list_url)


class ReviewGroupUserResourceTests(BaseWebAPITestCase):
    """Testing the ReviewGroupUserResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    def test_create_user(self, local_site=None):
        """Testing the POST groups/<name>/users/ API"""
        self._login_user(admin=True, local_site=local_site)

        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.users = []
        group.save()

        user = User.objects.get(pk=1)

        rsp = self.apiPost(
            get_review_group_user_list_url(group.name, local_site),
            {'username': user.username},
            expected_mimetype=user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(group.users.count(), 1)
        self.assertEqual(group.users.get().username, user.username)

    @add_fixtures(['test_site'])
    def test_create_user_with_site(self):
        """Testing the POST groups/<name>/users/ API with local site"""
        self.test_create_user(LocalSite.objects.get(name=self.local_site_name))

    def test_create_user_with_no_access(self, local_site=None):
        """Testing the POST groups/<name>/users/ API with Permission Denied"""
        group = Group.objects.get(pk=1)
        user = User.objects.get(pk=1)

        rsp = self.apiPost(
            get_review_group_user_list_url(group.name, local_site),
            {'username': user.username},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_create_user_with_site_no_access(self):
        """Testing the POST groups/<name>/users/ API with local site and Permission Denied"""
        self.test_create_user_with_no_access(
            LocalSite.objects.get(name=self.local_site_name))

    def test_create_user_with_invalid_user(self):
        """Testing the POST groups/<name>/users/ API with invalid user"""
        self._login_user(admin=True)

        group = Group.objects.get(pk=1)
        group.users = []
        group.save()

        rsp = self.apiPost(
            get_review_group_user_list_url(group.name),
            {'username': 'grabl'},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_USER.code)

        self.assertEqual(group.users.count(), 0)

    def test_delete_user(self, local_site=None):
        """Testing the DELETE groups/<name>/users/<username>/ API"""
        self._login_user(admin=True, local_site=local_site)

        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.save()

        old_count = group.users.count()
        user = group.users.all()[0]

        self.apiDelete(
            get_review_group_user_item_url(group.name, user.username,
                                           local_site),
            expected_status=204)

        self.assertEqual(group.users.count(), old_count - 1)

    @add_fixtures(['test_site'])
    def test_delete_user_with_site(self):
        """Testing the DELETE groups/<name>/users/<username>/ API with local site"""
        self.test_delete_user(LocalSite.objects.get(name=self.local_site_name))

    def test_delete_user_with_no_access(self, local_site=None):
        """Testing the DELETE groups/<name>/users/<username>/ API with Permission Denied"""
        group = Group.objects.get(pk=1)
        user = group.users.all()[0]

        self.apiDelete(
            get_review_group_user_item_url(group.name, user.username,
                                           local_site),
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_user_with_site_no_access(self):
        """Testing the DELETE groups/<name>/users/<username>/ API with local site and Permission Denied"""
        self.test_delete_user_with_no_access(
            LocalSite.objects.get(name=self.local_site_name))

    def test_get_users(self, local_site=None):
        """Testing the GET groups/<name>/users/ API"""
        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.save()

        rsp = self.apiGet(
            get_review_group_user_list_url(group.name, local_site),
            expected_mimetype=user_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), group.users.count())

    @add_fixtures(['test_site'])
    def test_get_users_with_site(self):
        """Testing the GET groups/<name>/users/ API with local site"""
        self._login_user(local_site=True)
        self.test_get_users(LocalSite.objects.get(name=self.local_site_name))
