"""Unit tests for reviewboard.reviews.managers.ReviewRequestManager."""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser, User
from djblets.testing.decorators import add_fixtures

from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.reviews.models import (DefaultReviewer, ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.reviews.testing.queries.review_requests import (
    get_review_requests_accessible_equeries,
    get_review_requests_from_user_equeries,
    get_review_requests_to_group_equeries,
    get_review_requests_to_or_from_user_equeries,
    get_review_requests_to_user_directly_equeries,
    get_review_requests_to_user_equeries,
    get_review_requests_to_user_groups_equeries,
)
from reviewboard.scmtools.errors import ChangeNumberInUseError
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ReviewRequestManagerTests(TestCase):
    """Unit tests for reviewboard.reviews.managers.ReviewRequestManager."""

    fixtures = ['test_users']

    @add_fixtures(['test_scmtools'])
    def test_create_with_site(self):
        """Testing ReviewRequest.objects.create with LocalSite"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        review_request = ReviewRequest.objects.create(
            user, repository, local_site=local_site)
        self.assertEqual(review_request.repository, repository)
        self.assertEqual(review_request.local_site, local_site)
        self.assertEqual(review_request.local_id, 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id(self):
        """Testing ReviewRequest.objects.create with LocalSite and commit ID"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        review_request = ReviewRequest.objects.create(
            user, repository,
            commit_id='123',
            local_site=local_site)
        self.assertEqual(review_request.repository, repository)
        self.assertEqual(review_request.commit_id, '123')
        self.assertEqual(review_request.local_site, local_site)
        self.assertEqual(review_request.local_id, 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id_conflicts_review_request(self):
        """Testing ReviewRequest.objects.create with LocalSite and commit ID
        that conflicts with a review request
        """
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        # This one should be fine.
        ReviewRequest.objects.create(user, repository, commit_id='123',
                                     local_site=local_site)
        self.assertEqual(local_site.review_requests.count(), 1)

        # This one will yell.
        with self.assertRaises(ChangeNumberInUseError):
            ReviewRequest.objects.create(
                user,
                repository,
                commit_id='123',
                local_site=local_site)

        # Make sure that entry doesn't exist in the database.
        self.assertEqual(local_site.review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id_conflicts_draft(self):
        """Testing ReviewRequest.objects.create with LocalSite and
        commit ID that conflicts with a draft
        """
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        # This one should be fine.
        existing_review_request = ReviewRequest.objects.create(
            user, repository, local_site=local_site)
        existing_draft = ReviewRequestDraft.create(existing_review_request)
        existing_draft.commit_id = '123'
        existing_draft.save()

        self.assertEqual(local_site.review_requests.count(), 1)

        # This one will yell.
        with self.assertRaises(ChangeNumberInUseError):
            ReviewRequest.objects.create(
                user,
                repository,
                commit_id='123',
                local_site=local_site)

        # Make sure that entry doesn't exist in the database.
        self.assertEqual(local_site.review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id_and_fetch_problem(self):
        """Testing ReviewRequest.objects.create with LocalSite and
        commit ID with problem fetching commit details
        """
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        self.assertEqual(local_site.review_requests.count(), 0)
        self.assertEqual(DiffSetHistory.objects.count(), 0)
        self.assertEqual(ReviewRequestDraft.objects.count(), 0)

        with self.assertRaises(NotImplementedError):
            ReviewRequest.objects.create(
                user, repository,
                commit_id='123',
                local_site=local_site,
                create_from_commit_id=True)

        # Make sure that entry and related objects don't exist in the database.
        self.assertEqual(local_site.review_requests.count(), 0)
        self.assertEqual(DiffSetHistory.objects.count(), 0)
        self.assertEqual(ReviewRequestDraft.objects.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_create_with_create_from_commit_id(self):
        """Testing ReviewRequest.objects.create with commit ID and
        create_from_commit_id
        """
        user = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Test')

        review_request = ReviewRequest.objects.create(
            user,
            repository,
            commit_id='123',
            create_from_commit_id=True)
        self.assertEqual(review_request.repository, repository)
        self.assertEqual(review_request.diffset_history.diffsets.count(), 0)
        self.assertEqual(review_request.commit_id, '123')
        self.assertEqual(review_request.changenum, 123)

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertIsNotNone(draft.diffset)
        self.assertEqual(draft.commit_id, '123')

    @add_fixtures(['test_scmtools'])
    def test_create_with_create_from_commit_id_and_default_reviewers(self):
        """Testing ReviewRequest.objects.create with commit ID,
        create_from_commit_id, and default reviewers
        """
        user = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Test')

        default_reviewer = DefaultReviewer.objects.create(
            name='Default Reviewer',
            file_regex='.')
        default_reviewer.repository.add(repository)
        default_reviewer.people.add(user)
        default_reviewer.groups.add(self.create_review_group())

        review_request = ReviewRequest.objects.create(
            user,
            repository,
            commit_id='123',
            create_from_commit_id=True)
        self.assertEqual(review_request.target_people.count(), 0)
        self.assertEqual(review_request.target_groups.count(), 0)

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.target_people.count(), 1)
        self.assertEqual(draft.target_groups.count(), 1)

    def test_public(self) -> None:
        """Testing ReviewRequest.objects.public"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        review_request_1 = self.create_review_request(
            summary='Test 1',
            publish=True,
            submitter=user1)

        review_request_2 = self.create_review_request(
            summary='Test 2',
            submitter=user2)

        review_request_3 = self.create_review_request(
            summary='Test 3',
            status='S',
            public=True,
            submitter=user1)

        review_request_4 = self.create_review_request(
            summary='Test 4',
            status='S',
            public=True,
            submitter=user2)

        review_request_5 = self.create_review_request(
            summary='Test 5',
            status='D',
            public=True,
            submitter=user1)

        review_request_6 = self.create_review_request(
            summary='Test 6',
            status='D',
            submitter=user2)

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # Check public() with a viewing user and a default status of 'P'.
        equeries = get_review_requests_accessible_equeries(user=user1)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user1)),
                [
                    review_request_1,
                ])

        # Check public() with anonymous and any status.
        equeries = get_review_requests_accessible_equeries(
            user=AnonymousUser(),
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(status=None)),
                [
                    review_request_5,
                    review_request_4,
                    review_request_3,
                    review_request_1,
                ])

        # Check public() with another viewing user and status=None.
        equeries = get_review_requests_accessible_equeries(
            user=user2,
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user2,
                                                  status=None)),
                [
                    review_request_6,
                    review_request_5,
                    review_request_4,
                    review_request_3,
                    review_request_2,
                    review_request_1,
                ])

        # Check public() with anonymous and status=None and showing all
        # unpublished changes.
        equeries = get_review_requests_accessible_equeries(
            user=AnonymousUser(),
            show_all_unpublished=True,
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(status=None,
                                                  show_all_unpublished=True)),
                [
                    review_request_6,
                    review_request_5,
                    review_request_4,
                    review_request_3,
                    review_request_2,
                    review_request_1,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_repository_on_local_site(self) -> None:
        """Testing ReviewRequest.objects.public with repository on a
        Local Site
        """
        user = User.objects.get(username='grumpy')

        local_site = self.create_local_site(
            name='test',
            users=[user])

        repository = self.create_repository(
            local_site=local_site)

        review_request = self.create_review_request(
            repository=repository,
            local_site=local_site,
            publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()
        user.get_profile()
        user.get_site_profile(local_site=local_site)

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True,
            accessible_repository_ids=[repository.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [
                    review_request,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_without_private_repo_access(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        repositories
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(
            public=False)

        review_request = self.create_review_request(
            repository=repository,
            publish=True)
        self.assertFalse(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(user=user)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [])

    @add_fixtures(['test_scmtools'])
    def test_public_without_private_repo_access_on_local_site(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        repositories on a Local Site
        """
        user = User.objects.get(username='grumpy')

        local_site = self.create_local_site(
            name='test',
            users=[user])

        repository = self.create_repository(
            public=False,
            local_site=local_site)

        review_request = self.create_review_request(
            repository=repository,
            local_site=local_site,
            publish=True)
        self.assertFalse(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()
        user.get_profile()
        user.get_site_profile(local_site=local_site)

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access(self) -> None:
        """Testing ReviewRequest.objects.public with access to private
        repositories
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(
            public=False,
            users=[user])

        review_request = self.create_review_request(
            repository=repository,
            publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(
            user=user,
            accessible_repository_ids=[repository.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [
                    review_request,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access_on_local_site(self) -> None:
        """Testing ReviewRequest.objects.public with access to private
        repositories on a Local Site
        """
        user = User.objects.get(username='grumpy')

        local_site = self.create_local_site(
            name='test',
            users=[user])

        repository = self.create_repository(
            public=False,
            local_site=local_site,
            users=[user])

        review_request = self.create_review_request(
            repository=repository,
            publish=True,
            local_site=local_site)
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()
        user.get_profile()
        user.get_site_profile(local_site=local_site)

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True,
            accessible_repository_ids=[repository.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [
                    review_request,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access_through_group(self) -> None:
        """Testing ReviewRequest.objects.public with access to private
        repositories
        """
        user = User.objects.get(username='grumpy')

        group = self.create_review_group(
            invite_only=True,
            users=[user])

        repository = self.create_repository(
            public=False,
            review_groups=[group])

        review_request = self.create_review_request(
            repository=repository,
            publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(
            user=user,
            accessible_repository_ids=[repository.pk],
            accessible_review_group_ids=[group.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [
                    review_request,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access_through_group_on_local_site(
        self,
    ) -> None:
        """Testing ReviewRequest.objects.public with access to private
        repositories on a Local Site
        """
        user = User.objects.get(username='grumpy')

        local_site = self.create_local_site(
            name='test',
            users=[user])

        group = self.create_review_group(
            invite_only=True,
            users=[user])

        repository = self.create_repository(
            public=False,
            local_site=local_site,
            review_groups=[group])

        review_request = self.create_review_request(
            repository=repository,
            local_site=local_site,
            publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()
        user.get_profile()
        user.get_site_profile(local_site=local_site)

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True,
            accessible_repository_ids=[repository.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [
                    review_request,
                ])

    def test_public_without_private_group_access(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(
            publish=True,
            target_groups=[group])
        self.assertFalse(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(user=user)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [])

    def test_public_with_private_group_access(self) -> None:
        """Testing ReviewRequest.objects.public with access to private
        group
        """
        user = User.objects.get(username='grumpy')

        group = self.create_review_group(
            invite_only=True,
            users=[user])

        review_request = self.create_review_request(
            publish=True,
            target_groups=[group])
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(
            user=user,
            accessible_review_group_ids=[group.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [
                    review_request,
                ])

    def test_public_with_private_group_access_on_local_site(self) -> None:
        """Testing ReviewRequest.objects.public with access to private
        group on a Local Site
        """
        user = User.objects.get(username='grumpy')

        local_site = self.create_local_site(
            name='test',
            users=[user])

        group = self.create_review_group(
            invite_only=True,
            local_site=local_site,
            users=[user])

        review_request = self.create_review_request(
            publish=True,
            local_site=local_site,
            target_groups=[group])
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()
        user.get_profile()
        user.get_site_profile(local_site=local_site)

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True,
            accessible_review_group_ids=[group.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [
                    review_request,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_public_group(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        repositories and with access to private group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group()

        repository = self.create_repository(public=False)

        review_request = self.create_review_request(
            repository=repository,
            publish=True,
            target_groups=[group])
        self.assertFalse(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(
            user=user,
            accessible_review_group_ids=[group.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_group_and_public_repo(self) -> None:
        """Testing ReviewRequest.objects.public with access to private
        group and without access to private group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        repository = self.create_repository(
            public=False,
            users=[user])

        review_request = self.create_review_request(
            repository=repository,
            publish=True,
            target_groups=[group])
        self.assertFalse(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(
            user=user,
            accessible_repository_ids=[repository.pk])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_owner(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        repository and as the submitter
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    submitter=user,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(user=user)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [
                    review_request,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_owner_on_local_site(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        repository and as the submitter on a Local Site
        """
        user = User.objects.get(username='grumpy')

        local_site = self.create_local_site(
            name='test',
            users=[user])

        repository = self.create_repository(
            public=False,
            local_site=local_site)

        review_request = self.create_review_request(
            repository=repository,
            submitter=user,
            local_site=local_site,
            publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [
                    review_request,
                ])

    def test_public_with_private_group_and_owner(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        group and as the submitter
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(
            submitter=user,
            publish=True,
            target_groups=[group])
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(user=user)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [
                    review_request,
                ])

    def test_public_with_private_group_and_owner_on_local_site(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        group and as the submitter on a Local Site
        """
        user = User.objects.get(username='grumpy')

        local_site = self.create_local_site(
            name='test',
            users=[user])

        group = self.create_review_group(
            invite_only=True,
            local_site=local_site)

        review_request = self.create_review_request(
            submitter=user,
            local_site=local_site,
            publish=True,
            target_groups=[group])
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [
                    review_request,
                ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_target_people(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        repository and user in target_people
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)

        review_request = self.create_review_request(
            repository=repository,
            publish=True,
            target_people=[user])
        self.assertFalse(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(user=user)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [])

    def test_public_with_private_group_and_target_people(self) -> None:
        """Testing ReviewRequest.objects.public without access to private
        group and user in target_people
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(
            publish=True,
            target_groups=[group],
            target_people=[user])
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        equeries = get_review_requests_accessible_equeries(user=user)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user)),
                [
                    review_request,
                ])

    def test_public_with_private_group_and_target_people_on_local_site(
        self,
    ) -> None:
        """Testing ReviewRequest.objects.public without access to private
        group and user in target_people on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        group = self.create_review_group(
            invite_only=True,
            local_site=local_site)

        review_request = self.create_review_request(
            publish=True,
            local_site=local_site,
            target_groups=[group],
            target_people=[user])
        self.assertTrue(review_request.is_accessible_by(user))

        # Prime the caches.
        LocalSite.objects.has_local_sites()
        user.get_site_profile(local_site=local_site)

        equeries = get_review_requests_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=True)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.public(user=user,
                                                  local_site=local_site)),
                [
                    review_request,
                ])

    def test_to_group(self) -> None:
        """Testing ReviewRequest.objects.to_group"""
        user1 = User.objects.get(username='doc')

        group1 = self.create_review_group(
            name='privgroup',
            users=[user1])

        review_request_1 = self.create_review_request(
            summary='Test 1',
            public=True,
            submitter=user1,
            target_groups=[group1])

        self.create_review_request(
            summary='Test 2',
            public=False,
            submitter=user1,
            target_groups=[group1])

        review_request_3 = self.create_review_request(
            summary='Test 3',
            public=True,
            status='S',
            submitter=user1,
            target_groups=[group1])

        # Check to_group() with a default status of 'P'.
        equeries = get_review_requests_to_group_equeries(
            user=AnonymousUser(),
            to_group_name='privgroup')

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_group('privgroup',
                                                    local_site=None)),
                [
                    review_request_1,
                ])

        # Check to_group() with any status.
        equeries = get_review_requests_to_group_equeries(
            user=AnonymousUser(),
            to_group_name='privgroup',
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_group('privgroup',
                                                    local_site=None,
                                                    status=None)),
                [
                    review_request_3,
                    review_request_1,
                ])

    def test_to_user_group(self) -> None:
        """Testing ReviewRequest.objects.to_user_groups"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        profile1 = user1.get_profile()
        profile2 = user2.get_profile()

        group1 = self.create_review_group(
            name='group1',
            users=[user1])

        group2 = self.create_review_group(
            name='group2',
            users=[user2])

        review_request_1 = self.create_review_request(
            summary='Test 1',
            public=True,
            submitter=user1,
            target_groups=[group1])

        review_request_2 = self.create_review_request(
            summary='Test 2',
            submitter=user2,
            public=True,
            status='S',
            target_groups=[group1])

        review_request_3 = self.create_review_request(
            summary='Test 3',
            public=True,
            submitter=user2,
            target_groups=[group1, group2])

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # Check to_user_groups() with a default status of 'P'.
        equeries = get_review_requests_to_user_groups_equeries(
            user=AnonymousUser(),
            to_user='doc',
            to_user_profile=profile1,
            target_groups=[group1])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user_groups('doc',
                                                          local_site=None)),
                [
                    review_request_3,
                    review_request_1,
                ])

        # Check to_user_groups() with any status.
        equeries = get_review_requests_to_user_groups_equeries(
            user=AnonymousUser(),
            to_user='doc',
            to_user_profile=profile1,
            target_groups=[group1],
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user_groups('doc',
                                                          status=None,
                                                          local_site=None)),
                [
                    review_request_3,
                    review_request_2,
                    review_request_1,
                ])

        # Check to_user_groups() with a viewing user.
        equeries = get_review_requests_to_user_groups_equeries(
            user=user2,
            to_user='grumpy',
            to_user_profile=profile2,
            target_groups=[group2])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user_groups('grumpy',
                                                          user=user2,
                                                          local_site=None)),
                [
                    review_request_3,
                ])

    def test_to_or_from_user(self) -> None:
        """Testing ReviewRequest.objects.to_or_from_user"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        profile1 = user1.get_profile()
        profile2 = user2.get_profile()

        group1 = self.create_review_group(
            name='group1',
            users=[user1])

        group2 = self.create_review_group(
            name='group2',
            users=[user2])

        review_request_1 = self.create_review_request(
            summary='Test 1',
            public=True,
            submitter=user1)

        review_request_2 = self.create_review_request(
            summary='Test 2',
            public=False,
            submitter=user1)

        review_request_3 = self.create_review_request(
            summary='Test 3',
            public=True,
            status='S',
            submitter=user1)

        review_request_4 = self.create_review_request(
            summary='Test 4',
            public=True,
            submitter=user1,
            target_groups=[group1],
            target_people=[user2])

        review_request_5 = self.create_review_request(
            summary='Test 5',
            submitter=user2,
            status='S',
            target_groups=[group1],
            target_people=[user2, user1])

        review_request_6 = self.create_review_request(
            summary='Test 6',
            public=True,
            submitter=user2,
            target_groups=[group1, group2],
            target_people=[user1])

        review_request_7 = self.create_review_request(
            summary='Test 7',
            public=True,
            status='S',
            submitter=user2,
            target_people=[user1])

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # Check to_or_from_user() with a default status of 'P'.
        equeries = get_review_requests_to_or_from_user_equeries(
            user=AnonymousUser(),
            to_or_from_user='doc',
            to_or_from_user_profile=profile1,
            target_groups=[group1])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_or_from_user('doc',
                                                           local_site=None)),
                [
                    review_request_6,
                    review_request_4,
                    review_request_1,
                ])

        # Check to_or_from_user() with a different user.
        equeries = get_review_requests_to_or_from_user_equeries(
            user=AnonymousUser(),
            to_or_from_user='grumpy',
            to_or_from_user_profile=profile2,
            target_groups=[group2])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_or_from_user('grumpy',
                                                           local_site=None)),
                [
                    review_request_6,
                    review_request_4,
                ])

        # Check to_or_from_user() with any status.
        equeries = get_review_requests_to_or_from_user_equeries(
            user=AnonymousUser(),
            to_or_from_user='doc',
            to_or_from_user_profile=profile1,
            target_groups=[group1],
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_or_from_user('doc',
                                                           status=None,
                                                           local_site=None)),
                [
                    review_request_7,
                    review_request_6,
                    review_request_4,
                    review_request_3,
                    review_request_1,
                ])

        # Check to_or_from_user() with a viewing user and any status.
        equeries = get_review_requests_to_or_from_user_equeries(
            user=user2,
            to_or_from_user='doc',
            to_or_from_user_profile=profile1,
            target_groups=[group1],
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_or_from_user('doc',
                                                           user=user2,
                                                           status=None,
                                                           local_site=None)),
                [
                    review_request_7,
                    review_request_6,
                    review_request_5,
                    review_request_4,
                    review_request_3,
                    review_request_1,
                ])

        # Check to_or_from_user() with a viewing user as to/from user and
        # any status.
        equeries = get_review_requests_to_or_from_user_equeries(
            user=user1,
            to_or_from_user='doc',
            to_or_from_user_profile=profile1,
            target_groups=[group1],
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_or_from_user('doc',
                                                           user=user1,
                                                           status=None,
                                                           local_site=None)),
                [
                    review_request_7,
                    review_request_6,
                    review_request_4,
                    review_request_3,
                    review_request_2,
                    review_request_1,
                ])

    def test_to_user_directly(self) -> None:
        """Testing ReviewRequest.objects.to_user_directly"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        profile1 = user1.get_profile()

        group1 = self.create_review_group(
            name='group1',
            users=[user1])

        group2 = self.create_review_group(
            name='group2',
            users=[user2])

        self.create_review_request(
            summary='Test 1',
            public=True,
            submitter=user1,
            target_groups=[group1],
            target_people=[user2])

        review_request_2 = self.create_review_request(
            summary='Test 2',
            submitter=user2,
            status='S',
            target_groups=[group1],
            target_people=[user2, user1])

        review_request_3 = self.create_review_request(
            summary='Test 3',
            public=True,
            submitter=user2,
            target_groups=[group1, group2],
            target_people=[user1])

        review_request_4 = self.create_review_request(
            summary='Test 4',
            public=True,
            status='S',
            submitter=user2,
            target_people=[user1])

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # Check to_user_directly() with a default status of 'P'.
        equeries = get_review_requests_to_user_directly_equeries(
            user=AnonymousUser(),
            to_user='doc',
            to_user_profile=profile1)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user_directly('doc',
                                                            local_site=None)),
                [
                    review_request_3,
                ])

        # Check to_user_directly() with any status.
        equeries = get_review_requests_to_user_directly_equeries(
            user=AnonymousUser(),
            to_user='doc',
            to_user_profile=profile1,
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user_directly('doc',
                                                            status=None)),
                [
                    review_request_4,
                    review_request_3,
                ])

        # Check to_user_directly() with a viewing user and any status.
        equeries = get_review_requests_to_user_directly_equeries(
            user=user2,
            to_user='doc',
            to_user_profile=profile1,
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user_directly('doc',
                                                            user=user2,
                                                            status=None,
                                                            local_site=None)),
                [
                    review_request_4,
                    review_request_3,
                    review_request_2,
                ])

    def test_from_user(self) -> None:
        """Testing ReviewRequest.objects.from_user"""
        user1 = User.objects.get(username='doc')

        review_request_1 = self.create_review_request(
            summary='Test 1',
            public=True,
            submitter=user1)

        review_request_2 = self.create_review_request(
            summary='Test 2',
            public=False,
            submitter=user1)

        review_request_3 = self.create_review_request(
            summary='Test 3',
            public=True,
            status='S',
            submitter=user1)

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # Check from_user() with a default status of 'P'.
        equeries = get_review_requests_from_user_equeries(
            user=AnonymousUser(),
            from_user='doc')

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.from_user('doc', local_site=None)),
                [
                    review_request_1,
                ])

        # Check from_user() with any status.
        equeries = get_review_requests_from_user_equeries(
            user=AnonymousUser(),
            status=None,
            from_user='doc')

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.from_user('doc',
                                                     status=None,
                                                     local_site=None)),
                [
                    review_request_3,
                    review_request_1,
                ])

        # Check from_user() with a viewing user and any status.
        equeries = get_review_requests_from_user_equeries(
            user=user1,
            status=None,
            from_user='doc')

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.from_user('doc',
                                                     user=user1,
                                                     status=None,
                                                     local_site=None)),
                [
                    review_request_3,
                    review_request_2,
                    review_request_1,
                ])

    def test_to_user(self) -> None:
        """Testing ReviewRequest.objects.to_user"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        profile1 = user1.get_profile()

        group1 = self.create_review_group(
            name='group1',
            users=[user1])

        group2 = self.create_review_group(
            name='group2',
            users=[user2])

        review_request_1 = self.create_review_request(
            summary='Test 1',
            publish=True,
            submitter=user1,
            target_groups=[group1])

        review_request_2 = self.create_review_request(
            summary='Test 2',
            submitter=user2,
            status='S',
            target_groups=[group1],
            target_people=[user1, user2])

        review_request_3 = self.create_review_request(
            summary='Test 3',
            publish=True,
            submitter=user2,
            target_groups=[group1, group2],
            target_people=[user1])

        review_request_4 = self.create_review_request(
            summary='Test 4',
            publish=True,
            status='S',
            submitter=user2,
            target_groups=[group1, group2],
            target_people=[user1])

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # Check to_user() with a default status of 'P'.
        equeries = get_review_requests_to_user_equeries(
            user=AnonymousUser(),
            to_user='doc',
            to_user_profile=profile1,
            target_groups=[group1])

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user('doc', local_site=None)),
                [
                    review_request_3,
                    review_request_1,
                ])

        # Check to_user() with any status.
        equeries = get_review_requests_to_user_equeries(
            user=AnonymousUser(),
            to_user='doc',
            to_user_profile=profile1,
            target_groups=[group1],
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user('doc',
                                                   status=None,
                                                   local_site=None)),
                [
                    review_request_4,
                    review_request_3,
                    review_request_1,
                ])

        # Check to_user() with a viewing user and any status.
        equeries = get_review_requests_to_user_equeries(
            user=user2,
            to_user='doc',
            to_user_profile=profile1,
            target_groups=[group1],
            status=None)

        with self.assertQueries(equeries):
            self.assertEqual(
                list(ReviewRequest.objects.to_user('doc',
                                                   user=user2,
                                                   status=None,
                                                   local_site=None)),
                [
                    review_request_4,
                    review_request_3,
                    review_request_2,
                    review_request_1,
                ])

    def assertValidSummaries(self, review_requests, summaries):
        r_summaries = [r.summary for r in review_requests]

        for summary in r_summaries:
            self.assertIn(summary, summaries,
                          'summary "%s" not found in summary list'
                          % summary)

        for summary in summaries:
            self.assertIn(summary, r_summaries,
                          'summary "%s" not found in review request list'
                          % summary)
