"""Unit tests for reviewboard.reviews.models.base_comment.StatusUpdate."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, Permission, User
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.testing import TestCase


class StatusUpdateTests(TestCase):
    """Unit tests for reviewboard.reviews.models.base_comment.StatusUpdate."""

    fixtures = ['test_users']

    def test_is_mutable_by_with_anonymous(self):
        """Testing StatusUpdate.is_mutable_by with anonymous user"""
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertFalse(status_update.is_mutable_by(AnonymousUser()))

    def test_is_mutable_by_with_owner(self):
        """Testing StatusUpdate.is_mutable_by with owner"""
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertTrue(status_update.is_mutable_by(status_update.user))

    def test_is_mutable_by_with_other_user(self):
        """Testing StatusUpdate.is_mutable_by with other user"""
        other_user = User.objects.create(username='other-user')
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertFalse(status_update.is_mutable_by(other_user))

    def test_is_mutable_by_with_other_user_and_can_change_status_perm(self):
        """Testing StatusUpdate.is_mutable_by with other user with
        change_statusupdate permission
        """
        other_user = User.objects.create(username='other-user')
        other_user.user_permissions.add(
            Permission.objects.get(codename='change_statusupdate'))

        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertTrue(status_update.is_mutable_by(other_user))

    @add_fixtures(['test_site'])
    def test_is_mutable_by_with_other_user_with_perm_same_local_site(self):
        """Testing StatusUpdate.is_mutable_by with other user on same
        LocalSite with change_statusupdate permission
        """
        review_request = self.create_review_request(with_local_site=True)
        status_update = self.create_status_update(review_request)

        other_user = User.objects.create(username='other-user')

        site = review_request.local_site
        site.users.add(other_user)

        site_profile = other_user.get_site_profile(site)
        site_profile.permissions = {
            'reviews.change_statusupdate': True,
        }
        site_profile.save(update_fields=('permissions',))

        self.assertTrue(status_update.is_mutable_by(other_user))
