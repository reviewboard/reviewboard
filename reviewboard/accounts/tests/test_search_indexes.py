"""Unit tests for reviewboard.accounts.search_indexes.

Version Added:
    8.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Q
from django_assert_queries.testing import assert_queries

from reviewboard.accounts.models import Profile
from reviewboard.reviews.models import Group
from reviewboard.accounts.search_indexes import UserIndex
from reviewboard.search.testing import search_enabled
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django_assert_queries import ExpectedQueries


class UserIndexTests(TestCase):
    """Unit tests for UserIndex.

    Version Added:
        8.0
    """

    def test_update(self) -> None:
        """Testing UserIndex.update"""
        users = self._create_users()

        group1 = self.create_review_group(name='group1')
        group1.users.add(*users[:5])

        group2 = self.create_review_group(name='group2')
        group2.users.add(*users[:-5])

        # Pre-populate caches.
        self.assertFalse(LocalSite.objects.has_local_sites())

        equeries: ExpectedQueries = [
            {
                'model': User,
                'only_fields': {
                    'email',
                    'first_name',
                    'last_name',
                    'username',
                    'profile__extra_data',
                    'profile__is_private',
                },
                'select_related': {
                    'profile',
                },
                'where': Q(is_active=True),
            },
            {
                'extra': {
                    '_prefetch_related_val_user_id': (
                        '"reviews_group_users"."user_id"',
                        [],
                    ),
                },
                'join_types': {
                    'reviews_group_users': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'invite_only',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': Q(users__in=users),
            },
        ]

        with (search_enabled(),
              assert_queries(equeries)):
            UserIndex().update()

    def test_update_with_local_sites(self) -> None:
        """Testing UserIndex.update with Local Sites in the database
        """
        users = self._create_users()

        local_site = self.create_local_site(name='test-site')
        local_site.users.add(*users[:5],
                             *users[:-5])

        group1 = self.create_review_group(name='group1')
        group1.users.add(*users[5:10])

        group2 = self.create_review_group(name='group2',
                                          local_site=local_site)
        group2.users.add(*users[:-5])

        # Pre-populate caches.
        self.assertTrue(LocalSite.objects.has_local_sites())

        equeries: ExpectedQueries = [
            {
                'model': User,
                'only_fields': {
                    'email',
                    'first_name',
                    'last_name',
                    'username',
                    'profile__extra_data',
                    'profile__is_private',
                },
                'select_related': {'profile'},
                'where': Q(is_active=True),
            },
            {
                'extra': {
                    '_prefetch_related_val_user_id': (
                        '"reviews_group_users"."user_id"',
                        [],
                    ),
                },
                'join_types': {
                    'reviews_group_users': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'invite_only',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': Q(users__in=users),
            },
            {
                'extra': {
                    '_prefetch_related_val_user_id': (
                        '"site_localsite_users"."user_id"',
                        [],
                    ),
                },
                'join_types': {
                    'site_localsite_users': 'INNER JOIN',
                },
                'model': LocalSite,
                'num_joins': 1,
                'only_fields': {
                    'name',
                },
                'tables': {
                    'site_localsite',
                    'site_localsite_users',
                },
                'where': Q(users__in=users),
            },
        ]

        with (search_enabled(),
              assert_queries(equeries, with_tracebacks=True)):
            UserIndex().update()

    def _create_users(self) -> Sequence[User]:
        """Create and return users to use for the tests.

        Returns:
            list of django.contrib.auth.models.User:
            The list of created users.
        """
        users: list[User] = []

        for i in range(20):
            user = self.create_user(username=f'user-{i:02}')
            users.append(user)

            if i > 10:
                # Create a profile.
                Profile.objects.create(
                    user=user,
                    is_private=(i % 2 == 0),
                )

        return users
