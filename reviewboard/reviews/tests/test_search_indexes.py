"""Unit tests for reviewboard.reviews.search_indexes.

Version Added:
    8.0
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Q
from django_assert_queries.testing import assert_queries

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.search_indexes import ReviewRequestIndex
from reviewboard.scmtools.models import Repository
from reviewboard.search.testing import search_enabled
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from django_assert_queries import ExpectedQueries


class ReviewRequestIndexTests(TestCase):
    """Unit tests for ReviewRequestIndex.

    Version Added:
        8.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def test_update(self) -> None:
        """Testing ReviewRequestIndex.update"""
        # Set up a bunch of default objects.
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2',
                                          invite_only=True)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')
        user3 = self.create_user(username='user3')

        Profile.objects.create(user=user1)
        Profile.objects.create(user=user2,
                               is_private=True)

        repository1 = self.create_repository(name='repo1')
        repository2 = self.create_repository(name='repo2',
                                             public=False)
        repository3 = self.create_repository(name='repo3',
                                             public=False)
        repository3.users.add(user1, user3)

        target_people = [user1, user2, user3]

        diffset_histories: list[DiffSetHistory] = []
        review_requests: list[ReviewRequest] = []
        diffsets: list[DiffSet] = []

        for (user, repository, target_groups) in itertools.product(
            (user1, user2, user3),
            (repository1, repository2, None),
            ([group1], [group2]),
        ):
            review_request = self.create_review_request(
                publish=True,
                repository=repository,
                submitter=user,
                target_groups=target_groups,
                target_people=target_people,
            )
            review_requests.append(review_request)

            assert review_request.diffset_history is not None
            diffset_histories.append(review_request.diffset_history)

            if repository is not None:
                diffsets += [
                    self.create_diffset(review_request),
                    self.create_diffset(review_request),
                ]

        # Pre-populate caches.
        self.assertFalse(LocalSite.objects.has_local_sites())

        equeries: ExpectedQueries = [
            {
                'model': ReviewRequest,
                'only_fields': {
                    # ReviewRequest fields.
                    'bugs_closed',
                    'changenum',
                    'commit_id',
                    'description',
                    'last_updated',
                    'local_id',
                    'local_site_id',
                    'public',
                    'repository_id',
                    'submitter_id',
                    'summary',
                    'testing_done',

                    # DiffSetHistory fields.
                    'diffset_history__id',
                },
                'select_related': {
                    'diffset_history',
                },
                'where': Q(public=True)
            },
            {
                'model': Repository,
                'only_fields': {
                    'local_site',
                    'public',
                },
                'where': Q(id__in={
                    repository1.pk,
                    repository2.pk,
                    None,
                }),
            },
            {
                'model': User,
                'only_fields': {
                    # User fields.
                    'first_name',
                    'last_name',
                    'username',

                    # Profile fields.
                    'profile__extra_data',
                    'profile__is_private',
                },
                'select_related': {
                    'profile',
                },
                'where': Q(id__in={
                    user1.pk,
                    user2.pk,
                    user3.pk,
                }),
            },
            {
                'model': DiffSet,
                'only_fields': {
                    'history_id',
                },
                'where': Q(history__in=diffset_histories[::-1]),
            },
            {
                'model': FileDiff,
                'only_fields': {
                    'dest_file',
                    'source_file',
                },
                'where': Q(diffset__in=diffsets),
            },
            {
                'extra': {
                    '_prefetch_related_val_reviewrequest_id': (
                        '"reviews_reviewrequest_target_groups".'
                        '"reviewrequest_id"',
                        [],
                    ),
                },
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    # Group fields.
                    'invite_only',
                    'local_site',
                },
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__in=review_requests[::-1]),
            },
            {
                'extra': {
                    '_prefetch_related_val_reviewrequest_id': (
                        '"reviews_reviewrequest_target_people".'
                        '"reviewrequest_id"',
                        [],
                    ),
                },
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'only_fields': {'id'},
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where':
                    Q(directed_review_requests__in=review_requests[::-1]),
            },
        ]

        with (search_enabled(),
              assert_queries(equeries)):
            ReviewRequestIndex().update()

    def test_update_with_local_sites(self) -> None:
        """Testing ReviewRequestIndex.update with LocalSites"""
        # Set up a bunch of default objects.
        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')
        user3 = self.create_user(username='user3')

        Profile.objects.create(user=user1)
        Profile.objects.create(
            user=user2,
            is_private=True,
        )

        local_site1 = self.create_local_site(
            name='local-site-1',
            users=[user1],
        )

        local_site2 = self.create_local_site(
            name='local-site-2',
            users=[user2],
        )

        diffset_histories: list[DiffSetHistory] = []
        diffsets: list[DiffSet] = []
        repository_ids: set[int | None] = {None}
        review_requests: list[ReviewRequest] = []

        for local_site in (local_site1, local_site2, None):
            group1 = self.create_review_group(
                name='group1',
                local_site=local_site,
                users=[user1],
            )
            group2 = self.create_review_group(
                name='group2',
                local_site=local_site,
                invite_only=True,
                users=[user2],
            )

            repository1 = self.create_repository(
                name='repo1',
                local_site=local_site,
            )

            repository2 = self.create_repository(
                name='repo2',
                local_site=local_site,
                public=False,
            )
            repository2.review_groups.add(group2)

            repository3 = self.create_repository(
                name='repo3',
                local_site=local_site,
                public=False,
            )
            repository3.users.add(user3)

            target_people = [user1, user2, user3]

            local_id = 1

            for (user, repository, target_groups) in itertools.product(
                (user1, user2, user3),
                (repository1, repository2, None),
                ([group1], [group2]),
            ):
                review_request = self.create_review_request(
                    public=True,
                    local_id=local_id,
                    local_site=local_site,
                    repository=repository,
                    submitter=user,
                    target_groups=target_groups,
                    target_people=target_people,
                )
                review_requests.append(review_request)
                local_id += 1

                assert review_request.diffset_history is not None
                diffset_histories.append(review_request.diffset_history)

                if repository is not None:
                    repository_ids.add(repository.pk)
                    diffsets += [
                        self.create_diffset(review_request),
                        self.create_diffset(review_request),
                    ]

        # Pre-populate caches.
        self.assertTrue(LocalSite.objects.has_local_sites())

        equeries: ExpectedQueries = [
            {
                'model': ReviewRequest,
                'only_fields': {
                    # ReviewRequest fields.
                    'bugs_closed',
                    'changenum',
                    'commit_id',
                    'description',
                    'last_updated',
                    'local_id',
                    'local_site_id',
                    'public',
                    'repository_id',
                    'submitter_id',
                    'summary',
                    'testing_done',

                    # DiffSetHistory fields.
                    'diffset_history__id',
                },
                'select_related': {
                    'diffset_history',
                },
                'where': Q(public=True)
            },
            {
                'model': Repository,
                'only_fields': {
                    # Repository fields.
                    'local_site',
                    'public',

                    # LocalSite fields.
                    'local_site__public',
                },
                'select_related': {
                    'local_site',
                },
                'where': Q(id__in=repository_ids),
            },
            {
                'model': User,
                'only_fields': {
                    # User fields.
                    'first_name',
                    'last_name',
                    'username',

                    # Profile fields.
                    'profile__extra_data',
                    'profile__is_private',
                },
                'select_related': {'profile'},
                'where': Q(id__in={
                    user1.pk,
                    user2.pk,
                    user3.pk,
                }),
            },
            {
                'model': DiffSet,
                'only_fields': {
                    'history_id',
                },
                'where': Q(history__in=diffset_histories[::-1]),
            },
            {
                'model': FileDiff,
                'only_fields': {
                    'dest_file',
                    'source_file',
                },
                'where': Q(diffset__in=diffsets),
            },
            {
                'extra': {
                    '_prefetch_related_val_reviewrequest_id': (
                        '"reviews_reviewrequest_target_groups".'
                        '"reviewrequest_id"',
                        [],
                    ),
                },
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    # Group fields.
                    'invite_only',
                    'local_site',

                    # LocalSite fields.
                    'local_site__public',
                },
                'select_related': {
                    'local_site',
                },
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__in=review_requests[::-1]),
            },
            {
                'extra': {
                    '_prefetch_related_val_reviewrequest_id': (
                        '"reviews_reviewrequest_target_people".'
                        '"reviewrequest_id"',
                        [],
                    ),
                },
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'only_fields': {'id'},
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where':
                    Q(directed_review_requests__in=review_requests[::-1]),
            },
            {
                'model': LocalSite,
                'only_fields': {
                    'name',
                },
                'where': Q(id__in={
                    local_site1.pk,
                    local_site2.pk,
                    None,
                }),
            },
        ]

        with (search_enabled(),
              assert_queries(equeries, with_tracebacks=True)):
            ReviewRequestIndex().update()
