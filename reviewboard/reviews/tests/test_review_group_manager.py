"""Unit tests for reviewboard.reviews.manager.ReviewGroupManager."""

from django.contrib.auth.models import AnonymousUser
from djblets.testing.decorators import add_fixtures

from reviewboard.deprecation import RemovedInReviewBoard60Warning
from reviewboard.reviews.models import Group
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ReviewGroupManagerTests(TestCase):
    """Unit tests for reviewboard.reviews.manager.ReviewGroupManager."""

    def test_accessible_with_public(self):
        """Testing Group.objects.accessible with public group"""
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group()

        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=False))
        self.assertIn(
            group,
            Group.objects.accessible(anonymous, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(anonymous, visible_only=False))

    def test_accessible_with_public_and_hidden(self):
        """Testing Group.objects.accessible with public hidden group"""
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group(visible=False)

        self.assertNotIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=False))
        self.assertNotIn(
            group,
            Group.objects.accessible(anonymous, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(anonymous, visible_only=False))

    def test_accessible_with_invite_only_and_not_member(self):
        """Testing Group.objects.accessible with invite-only group and user
        not a member
        """
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group(invite_only=True)

        self.assertNotIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertNotIn(
            group,
            Group.objects.accessible(user, visible_only=False))
        self.assertNotIn(
            group,
            Group.objects.accessible(anonymous, visible_only=True))
        self.assertNotIn(
            group,
            Group.objects.accessible(anonymous, visible_only=False))

    def test_accessible_with_invite_only_and_member(self):
        """Testing Group.objects.accessible with invite-only group and user is
        a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=False))

    def test_accessible_with_invite_only_and_superuser(self):
        """Testing Group.objects.accessible with invite-only group and user is
        a superuser
        """
        user = self.create_user(is_superuser=True)
        group = self.create_review_group(invite_only=True)

        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=False))

    def test_accessible_with_invite_only_and_perm(self):
        """Testing Group.objects.accessible with invite-only group and user
        has reviews.view_invite_only_groups permission
        """
        user = self.create_user(perms=[
            ('reviews', 'can_view_invite_only_groups'),
        ])
        group = self.create_review_group(invite_only=True)

        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=True))

    def test_accessible_with_invite_only_hidden_not_member(self):
        """Testing Group.objects.accessible with invite-only hidden group and
        user not a member
        """
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group(invite_only=True,
                                         visible=False)

        self.assertNotIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertNotIn(
            group,
            Group.objects.accessible(user, visible_only=False))
        self.assertNotIn(
            group,
            Group.objects.accessible(anonymous, visible_only=True))
        self.assertNotIn(
            group,
            Group.objects.accessible(anonymous, visible_only=False))

    def test_accessible_with_invite_only_hidden_and_member(self):
        """Testing Group.objects.accessible with invite-only hidden group and
        user is a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True,
                                         visible=False)
        group.users.add(user)

        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=False))

    def test_accessible_with_invite_only_hidden_and_superuser(self):
        """Testing Group.objects.accessible with invite-only hidden group and
        superuser
        """
        user = self.create_user(is_superuser=True)
        group = self.create_review_group(invite_only=True,
                                         visible=False)

        self.assertNotIn(
            group,
            Group.objects.accessible(user, visible_only=True))
        self.assertIn(
            group,
            Group.objects.accessible(user, visible_only=False))

    @add_fixtures(['test_users', 'test_site'])
    def test_accessible_with_local_site_accessible(self):
        """Testing Group.objects.accessible with Local Site accessible by user
        """
        user = self.create_user()

        group = self.create_review_group(with_local_site=True)
        group.local_site.users.add(user)

        self.assertIn(
            group,
            Group.objects.accessible(user, local_site=group.local_site))
        self.assertIn(
            group,
            Group.objects.accessible(user, local_site=LocalSite.ALL))

        message = (
            'show_all_local_sites is deprecated. Please pass '
            'local_site=LocalSite.ALL instead. This will be required '
            'in Review Board 6.'
        )

        with self.assertWarns(RemovedInReviewBoard60Warning, message):
            self.assertIn(
                group,
                Group.objects.accessible(user, show_all_local_sites=True))

    def test_accessible_ids_with_public(self):
        """Testing Group.objects.accessible_ids with public group"""
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group()

        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=False))

    def test_accessible_ids_with_public_and_hidden(self):
        """Testing Group.objects.accessible_ids with public hidden group"""
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group(visible=False)

        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))
        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=False))

    def test_accessible_ids_with_invite_only_and_not_member(self):
        """Testing Group.objects.accessible_ids with invite-only group and
        user not a member
        """
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group(invite_only=True)

        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))
        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=True))
        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=False))

    def test_accessible_ids_with_invite_only_and_member(self):
        """Testing Group.objects.accessible_ids with invite-only group and
        user is a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))

    def test_accessible_ids_with_invite_only_and_superuser(self):
        """Testing Group.objects.accessible_ids with invite-only group and
        user is a superuser
        """
        user = self.create_user(is_superuser=True)
        group = self.create_review_group(invite_only=True)

        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))

    def test_accessible_ids_with_invite_only_and_perm(self):
        """Testing Group.objects.accessible_ids with invite-only group and
        user has reviews.view_invite_only_groups permission
        """
        user = self.create_user(perms=[
            ('reviews', 'can_view_invite_only_groups'),
        ])
        group = self.create_review_group(invite_only=True)

        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))

    def test_accessible_ids_with_invite_only_hidden_not_member(self):
        """Testing Group.objects.accessible_ids with invite-only hidden group
        and user not a member
        """
        anonymous = AnonymousUser()
        user = self.create_user()
        group = self.create_review_group(invite_only=True,
                                         visible=False)

        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))
        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=True))
        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(anonymous, visible_only=False))

    def test_accessible_ids_with_invite_only_hidden_and_member(self):
        """Testing Group.objects.accessible_ids with invite-only hidden group
        and user is a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True,
                                         visible=False)
        group.users.add(user)

        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))

    def test_accessible_ids_with_invite_only_hidden_and_superuser(self):
        """Testing Group.objects.accessible_ids with invite-only hidden group
        and superuser
        """
        user = self.create_user(is_superuser=True)
        group = self.create_review_group(invite_only=True,
                                         visible=False)

        self.assertNotIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=True))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, visible_only=False))

    @add_fixtures(['test_users', 'test_site'])
    def test_accessible_ids_with_local_site_accessible_ids(self):
        """Testing Group.objects.accessible_ids with Local Site accessible by
        user
        """
        user = self.create_user()

        group = self.create_review_group(with_local_site=True)
        group.local_site.users.add(user)

        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, local_site=group.local_site))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, local_site=LocalSite.ALL))

        message = (
            'show_all_local_sites is deprecated. Please pass '
            'local_site=LocalSite.ALL instead. This will be required '
            'in Review Board 6.'
        )

        with self.assertWarns(RemovedInReviewBoard60Warning, message):
            self.assertIn(
                group.pk,
                Group.objects.accessible_ids(user, show_all_local_sites=True))
