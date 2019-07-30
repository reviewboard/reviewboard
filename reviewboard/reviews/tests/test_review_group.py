"""Unit tests for reviewboard.reviews.models.Group"""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from djblets.testing.decorators import add_fixtures

from reviewboard.testing import TestCase


class ReviewGroupTests(TestCase):
    """Unit tests for reviewboard.reviews.models.Group."""

    def test_is_accessible_by_with_public(self):
        """Testing Group.is_accessible_by with public group"""
        user = self.create_user()
        group = self.create_review_group()

        self.assertTrue(group.is_accessible_by(user))
        self.assertTrue(group.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_public_and_hidden(self):
        """Testing Group.is_accessible_by with public hidden group"""
        user = self.create_user()
        group = self.create_review_group(visible=False)

        self.assertTrue(group.is_accessible_by(user))
        self.assertTrue(group.is_accessible_by(user))

    def test_is_accessible_by_with_invite_only_and_not_member(self):
        """Testing Group.is_accessible_by with invite-only group and user
        not a member
        """
        user = self.create_user()
        group = self.create_review_group(invite_only=True)

        self.assertFalse(group.is_accessible_by(user))
        self.assertFalse(group.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_invite_only_and_member(self):
        """Testing Group.is_accessible_by with invite-only group and user is
        a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        self.assertTrue(group.is_accessible_by(user))

    def test_is_accessible_by_with_invite_only_and_superuser(self):
        """Testing Group.is_accessible_by with invite-only group and user is
        a superuser
        """
        user = self.create_user(is_superuser=True)
        group = self.create_review_group(invite_only=True)

        self.assertTrue(group.is_accessible_by(user))

    def test_is_accessible_by_with_invite_only_hidden_not_member(self):
        """Testing Group.is_accessible_by with invite-only hidden group and
        user not a member
        """
        user = self.create_user()
        group = self.create_review_group(invite_only=True,
                                         visible=False)

        self.assertFalse(group.is_accessible_by(user))
        self.assertFalse(group.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_invite_only_hidden_and_member(self):
        """Testing Group.is_accessible_by with invite-only hidden group and
        user is a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True,
                                         visible=False)
        group.users.add(user)

        self.assertTrue(group.is_accessible_by(user))

    @add_fixtures(['test_users', 'test_site'])
    def test_is_accessible_by_with_local_site_accessible(self):
        """Testing Group.is_accessible_by with Local Site accessible by user"""
        user = self.create_user()

        group = self.create_review_group(with_local_site=True)
        group.local_site.users.add(user)

        self.assertTrue(group.is_accessible_by(user))

    @add_fixtures(['test_users', 'test_site'])
    def test_is_accessible_by_with_local_site_not_accessible(self):
        """Testing Group.is_accessible_by with Local Site not accessible by
        user
        """
        user = self.create_user()
        group = self.create_review_group(with_local_site=True)

        self.assertFalse(group.is_accessible_by(user))
        self.assertFalse(group.is_accessible_by(AnonymousUser()))

    def test_is_mutable_by_with_non_admins(self):
        """Testing Group.is_mutable_by with non-administrative users"""
        user = self.create_user()
        group = self.create_review_group()

        self.assertFalse(group.is_mutable_by(user))
        self.assertFalse(group.is_mutable_by(AnonymousUser()))

    def test_is_mutable_by_with_superuser(self):
        """Testing Group.is_mutable_by with superuser"""
        user = self.create_user(is_superuser=True)
        group = self.create_review_group()

        self.assertTrue(group.is_mutable_by(user))

    def test_is_mutable_by_with_change_group_perm(self):
        """Testing Group.is_mutable_by with user with reviews.change_group
        permission
        """
        user = self.create_user(perms=[
            ('reviews', 'change_group'),
        ])
        group = self.create_review_group()

        self.assertTrue(group.is_mutable_by(user))

    @add_fixtures(['test_users', 'test_site'])
    def test_is_mutable_by_with_local_site_admin(self):
        """Testing Group.is_mutable_by with user with Local Site admin"""
        user = self.create_user()

        group = self.create_review_group(with_local_site=True)
        group.local_site.admins.add(user)

        self.assertTrue(group.is_mutable_by(user))
