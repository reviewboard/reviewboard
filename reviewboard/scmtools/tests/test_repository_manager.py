"""Unit tests for reviewboard.scmtools.manager.RepositoryManager."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from django.utils import six
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

    def test_get_best_match_with_pk(self):
        """Testing Repository.objects.get_best_match with repository ID"""
        repository1 = self.create_repository()
        self.create_repository(name=six.text_type(repository1.pk))

        self.assertEqual(
            Repository.objects.get_best_match(repository1.pk),
            repository1)

    @add_fixtures(['test_site'])
    def test_get_best_match_with_pk_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository ID and
        local_site=...
        """
        repository1 = self.create_repository(with_local_site=True)
        repository2 = self.create_repository()
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.pk,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.pk)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.pk,
                                              local_site=local_site)

    def test_get_best_match_with_name(self):
        """Testing Repository.objects.get_best_match with repository name"""
        repository1 = self.create_repository(name='repo 1')
        self.create_repository(name='repo 2')

        self.assertEqual(
            Repository.objects.get_best_match('repo 1'),
            repository1)

    @add_fixtures(['test_site'])
    def test_get_best_match_with_name_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository name
        and local_site=...
        """
        repository1 = self.create_repository(name='repo 1',
                                             with_local_site=True)
        repository2 = self.create_repository(name='repo 2')
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.name,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.name)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.name,
                                              local_site=local_site)

    def test_get_best_match_with_path(self):
        """Testing Repository.objects.get_best_match with repository path"""
        repository1 = self.create_repository(path='/test-path-1')
        self.create_repository(path='/test-path-2')

        self.assertEqual(
            Repository.objects.get_best_match('/test-path-1'),
            repository1)

    @add_fixtures(['test_site'])
    def test_get_best_match_with_path_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository path
        and local_site=...
        """
        repository1 = self.create_repository(path='/test-path-1',
                                             with_local_site=True)
        repository2 = self.create_repository(path='/test-path-2')
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.path,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.path)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.path,
                                              local_site=local_site)

    def test_get_best_match_with_mirror_path(self):
        """Testing Repository.objects.get_best_match with repository
        mirror_path
        """
        repository1 = self.create_repository(mirror_path='/test-path-1')
        self.create_repository(mirror_path='/test-path-2')

        self.assertEqual(
            Repository.objects.get_best_match('/test-path-1'),
            repository1)

    @add_fixtures(['test_site'])
    def test_get_best_match_with_mirror_path_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository
        mirror_path and local_site=...
        """
        repository1 = self.create_repository(mirror_path='/test-path-1',
                                             with_local_site=True)
        repository2 = self.create_repository(mirror_path='/test-path-2')
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.mirror_path,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.mirror_path)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.mirror_path,
                                              local_site=local_site)

    def test_get_best_match_with_no_match(self):
        """Testing Repository.objects.get_best_match with no match"""
        self.create_repository(name='repo 1')
        self.create_repository(name='repo 2')

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match('bad-id')

    def test_get_best_match_with_multiple_prefer_visible(self):
        """Testing Repository.objects.get_best_match with multiple results
        prefers visible over name/path/mirror_path
        """
        repository1 = self.create_repository(
            name='repo1',
            path='/path1',
            mirror_path='mirror')
        repository2 = self.create_repository(
            name='repo2',
            path='/path2',
            mirror_path='mirror')
        repository3 = self.create_repository(
            name='repo3',
            path='/path3',
            mirror_path='mirror')

        # This should fail, since all are visible and they conflict.
        with self.assertRaises(Repository.MultipleObjectsReturned):
            Repository.objects.get_best_match('mirror')

        # It should then work if only one is visible.
        repository2.visible = False
        repository2.save(update_fields=('visible',))

        repository3.visible = False
        repository3.save(update_fields=('visible',))

        self.assertEqual(
            Repository.objects.get_best_match('mirror'),
            repository1)

    def test_get_best_match_with_multiple_prefer_name(self):
        """Testing Repository.objects.get_best_match with multiple results
        prefers name over path/mirror_path
        """
        repository1 = self.create_repository(
            name='repo1',
            path='/path1',
            mirror_path='mirror')
        self.create_repository(
            name='repo2',
            path='/path2',
            mirror_path='mirror')
        self.create_repository(
            name='repo3',
            path='/path3',
            mirror_path='mirror')

        # This should fail, since all are visible and they conflict.
        with self.assertRaises(Repository.MultipleObjectsReturned):
            Repository.objects.get_best_match('mirror')

        # It should then work if only one is visible.
        repository1.name = 'mirror'
        repository1.save(update_fields=('name',))

        self.assertEqual(
            Repository.objects.get_best_match('mirror'),
            repository1)

    def test_get_best_match_with_multiple_prefer_path(self):
        """Testing Repository.objects.get_best_match with multiple results
        prefers path over mirror_path
        """
        repository1 = self.create_repository(
            name='repo1',
            path='/path1',
            mirror_path='mirror')
        self.create_repository(
            name='repo2',
            path='/path2',
            mirror_path='mirror')
        self.create_repository(
            name='repo3',
            path='/path3',
            mirror_path='mirror')

        # This should fail, since all are visible and they conflict.
        with self.assertRaises(Repository.MultipleObjectsReturned):
            Repository.objects.get_best_match('mirror')

        # It should then work if only one is visible.
        repository1.path = 'mirror'
        repository1.save(update_fields=('path',))

        self.assertEqual(
            Repository.objects.get_best_match('mirror'),
            repository1)
