"""Unit tests for reviewboard.scmtools.manager.RepositoryManager."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from djblets.testing.decorators import add_fixtures

from reviewboard.scmtools.models import Repository
from reviewboard.testing import TestCase


class RepositoryManagerTests(TestCase):
    """Unit tests for reviewboard.scmtools.manager.RepositoryManager."""

    fixtures = ['test_scmtools']

    def test_accessible_with_public(self):
        """Testing Repository.objects.accessible with public repository"""
        user = self.create_user()
        repository = self.create_repository()

        self.assertIn(repository,
                      Repository.objects.accessible(user))
        self.assertIn(repository,
                      Repository.objects.accessible(AnonymousUser()))

    def test_accessible_with_public_and_hidden(self):
        """Testing Repository.objects.accessible with public hidden
        repository
        """
        anonymous = AnonymousUser()
        user = self.create_user()
        repository = self.create_repository(visible=False)

        self.assertNotIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))
        self.assertNotIn(
            repository,
            Repository.objects.accessible(anonymous, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(anonymous, visible_only=False))

    def test_accessible_with_private_and_not_member(self):
        """Testing Repository.objects.accessible with private repository and
        user not a member
        """
        anonymous = AnonymousUser()
        user = self.create_user()
        repository = self.create_repository(public=False)

        self.assertNotIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertNotIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))
        self.assertNotIn(
            repository,
            Repository.objects.accessible(anonymous, visible_only=True))
        self.assertNotIn(
            repository,
            Repository.objects.accessible(anonymous, visible_only=False))

    def test_accessible_with_private_and_member(self):
        """Testing Repository.objects.accessible with private repository and
        user is a member
        """
        user = self.create_user()

        repository = self.create_repository(public=False)
        repository.users.add(user)

        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))

    def test_accessible_with_private_and_member_by_group(self):
        """Testing Repository.objects.accessible with private repository and
        user is a member by group
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False)
        repository.review_groups.add(group)

        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))

    def test_accessible_with_private_and_superuser(self):
        """Testing Repository.objects.accessible with private repository and
        user is a superuser
        """
        user = self.create_user(is_superuser=True)
        repository = self.create_repository(public=False)

        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))

    def test_accessible_with_private_hidden_not_member(self):
        """Testing Repository.objects.accessible with private hidden
        repository and user not a member
        """
        anonymous = AnonymousUser()
        user = self.create_user()
        repository = self.create_repository(public=False,
                                            visible=False)

        self.assertNotIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertNotIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))
        self.assertNotIn(
            repository,
            Repository.objects.accessible(anonymous, visible_only=True))
        self.assertNotIn(
            repository,
            Repository.objects.accessible(anonymous, visible_only=False))

    def test_accessible_with_private_hidden_and_member(self):
        """Testing Repository.objects.accessible with private hidden
        repository and user is a member
        """
        user = self.create_user()

        repository = self.create_repository(public=False,
                                            visible=False)
        repository.users.add(user)

        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))

    def test_accessible_with_private_hidden_and_member_by_group(self):
        """Testing Repository.objects.accessible with private hidden
        repository and user is a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False,
                                            visible=False)
        repository.review_groups.add(group)

        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))

    def test_accessible_with_private_hidden_and_superuser(self):
        """Testing Repository.objects.accessible with private hidden
        repository and superuser
        """
        user = self.create_user(is_superuser=True)
        repository = self.create_repository(public=False,
                                            visible=False)

        self.assertNotIn(
            repository,
            Repository.objects.accessible(user, visible_only=True))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, visible_only=False))

    @add_fixtures(['test_users', 'test_site'])
    def test_accessible_with_local_site_accessible(self):
        """Testing Repository.objects.accessible with Local Site accessible by
        user
        """
        user = self.create_user(is_superuser=True)

        repository = self.create_repository(with_local_site=True)
        repository.local_site.users.add(user)

        self.assertIn(
            repository,
            Repository.objects.accessible(user,
                                          local_site=repository.local_site))
        self.assertIn(
            repository,
            Repository.objects.accessible(user, show_all_local_sites=True))
