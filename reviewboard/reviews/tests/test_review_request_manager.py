from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.reviews.models import (DefaultReviewer, ReviewRequest,
                                        ReviewRequestDraft)
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

    def test_public(self):
        """Testing ReviewRequest.objects.public"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        self.create_review_request(summary='Test 1',
                                   publish=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 2',
                                   submitter=user2)
        self.create_review_request(summary='Test 3',
                                   status='S',
                                   public=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 4',
                                   status='S',
                                   public=True,
                                   submitter=user2)
        self.create_review_request(summary='Test 5',
                                   status='D',
                                   public=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 6',
                                   status='D',
                                   submitter=user2)

        self.assertValidSummaries(
            ReviewRequest.objects.public(user=user1),
            [
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.public(status=None),
            [
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.public(user=user2, status=None),
            [
                'Test 6',
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
            ])
        self.assertValidSummaries(
            ReviewRequest.objects.public(status=None,
                                         show_all_unpublished=True),
            [
                'Test 6',
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
            ])

    @add_fixtures(['test_scmtools'])
    def test_public_with_repository_on_local_site(self):
        """Testing ReviewRequest.objects.public with repository on a
        Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        repository = self.create_repository(local_site=local_site)
        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_without_private_repo_access(self):
        """Testing ReviewRequest.objects.public without access to private
        repositories
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_public_without_private_repo_access_on_local_site(self):
        """Testing ReviewRequest.objects.public without access to private
        repositories on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        repository = self.create_repository(public=False,
                                            local_site=local_site)
        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=True)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access(self):
        """Testing ReviewRequest.objects.public with access to private
        repositories
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        repository.users.add(user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access_on_local_site(self):
        """Testing ReviewRequest.objects.public with access to private
        repositories on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        repository = self.create_repository(public=False,
                                            local_site=local_site)
        repository.users.add(user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True,
                                                    local_site=local_site)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access_through_group(self):
        """Testing ReviewRequest.objects.public with access to private
        repositories
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False)
        repository.review_groups.add(group)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access_through_group_on_local_site(self):
        """Testing ReviewRequest.objects.public with access to private
        repositories on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False,
                                            local_site=local_site)
        repository.review_groups.add(group)
        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 1)

    def test_public_without_private_group_access(self):
        """Testing ReviewRequest.objects.public without access to private
        group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    def test_public_with_private_group_access(self):
        """Testing ReviewRequest.objects.public with access to private
        group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    def test_public_with_private_group_access_on_local_site(self):
        """Testing ReviewRequest.objects.public with access to private
        group on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        group = self.create_review_group(invite_only=True,
                                         local_site=local_site)
        group.users.add(user)

        review_request = self.create_review_request(publish=True,
                                                    local_site=local_site)
        review_request.target_groups.add(group)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_public_group(self):
        """Testing ReviewRequest.objects.public without access to private
        repositories and with access to private group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group()

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_groups.add(group)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_group_and_public_repo(self):
        """Testing ReviewRequest.objects.public with access to private
        group and without access to private group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        repository = self.create_repository(public=False)
        repository.users.add(user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_groups.add(group)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_owner(self):
        """Testing ReviewRequest.objects.public without access to private
        repository and as the submitter
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    submitter=user,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_owner_on_local_site(self):
        """Testing ReviewRequest.objects.public without access to private
        repository and as the submitter on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        repository = self.create_repository(public=False,
                                            local_site=local_site)
        review_request = self.create_review_request(repository=repository,
                                                    submitter=user,
                                                    local_site=local_site,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 1)

    def test_public_with_private_group_and_owner(self):
        """Testing ReviewRequest.objects.public without access to private
        group and as the submitter
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(submitter=user,
                                                    publish=True)
        review_request.target_groups.add(group)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    def test_public_with_private_group_and_owner_on_local_site(self):
        """Testing ReviewRequest.objects.public without access to private
        group and as the submitter on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        group = self.create_review_group(invite_only=True,
                                         local_site=local_site)

        review_request = self.create_review_request(submitter=user,
                                                    local_site=local_site,
                                                    publish=True)
        review_request.target_groups.add(group)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_target_people(self):
        """Testing ReviewRequest.objects.public without access to private
        repository and user in target_people
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_people.add(user)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    def test_public_with_private_group_and_target_people(self):
        """Testing ReviewRequest.objects.public without access to private
        group and user in target_people
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        review_request.target_people.add(user)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    def test_public_with_private_group_and_target_people_on_local_site(self):
        """Testing ReviewRequest.objects.public without access to private
        group and user in target_people on a Local Site
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(username='grumpy')
        local_site.users.add(user)

        group = self.create_review_group(invite_only=True,
                                         local_site=local_site)

        review_request = self.create_review_request(publish=True,
                                                    local_site=local_site)
        review_request.target_groups.add(group)
        review_request.target_people.add(user)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user,
                                                       local_site=local_site)
        self.assertEqual(review_requests.count(), 1)

    def test_to_group(self):
        """Testing ReviewRequest.objects.to_group"""
        user1 = User.objects.get(username='doc')

        group1 = self.create_review_group(name='privgroup')
        group1.users.add(user1)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    public=False,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    status='S',
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        self.assertValidSummaries(
            ReviewRequest.objects.to_group('privgroup', None),
            [
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_group('privgroup', None, status=None),
            [
                'Test 3',
                'Test 1',
            ])

    def test_to_user_group(self):
        """Testing ReviewRequest.objects.to_user_groups"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    public=True,
                                                    status='S')
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups('doc', local_site=None),
            [
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups(
                'doc', status=None, local_site=None),
            [
                'Test 3',
                'Test 2',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups(
                'grumpy', user=user2, local_site=None),
            [
                'Test 3',
            ])

    def test_to_or_from_user(self):
        """Testing ReviewRequest.objects.to_or_from_user"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        self.create_review_request(summary='Test 1',
                                   public=True,
                                   submitter=user1)

        self.create_review_request(summary='Test 2',
                                   public=False,
                                   submitter=user1)

        self.create_review_request(summary='Test 3',
                                   public=True,
                                   status='S',
                                   submitter=user1)

        review_request = self.create_review_request(summary='Test 4',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)

        review_request = self.create_review_request(summary='Test 5',
                                                    submitter=user2,
                                                    status='S')
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 6',
                                                    public=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 7',
                                                    public=True,
                                                    status='S',
                                                    submitter=user2)
        review_request.target_people.add(user1)

        self.assertValidSummaries(
            ReviewRequest.objects.to_or_from_user('doc', local_site=None),
            [
                'Test 6',
                'Test 4',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_or_from_user('grumpy', local_site=None),
            [
                'Test 6',
                'Test 4',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_or_from_user('doc', status=None,
                                                  local_site=None),
            [
                'Test 7',
                'Test 6',
                'Test 4',
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_or_from_user('doc', user=user2,
                                                  status=None,
                                                  local_site=None),
            [
                'Test 7',
                'Test 6',
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_or_from_user('doc', user=user1,
                                                  status=None,
                                                  local_site=None),
            [
                'Test 7',
                'Test 6',
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
            ])

    def test_to_user_directly(self):
        """Testing ReviewRequest.objects.to_user_directly"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    status='S')
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 4',
                                                    public=True,
                                                    status='S',
                                                    submitter=user2)
        review_request.target_people.add(user1)

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly('doc', local_site=None),
            [
                'Test 3',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly('doc', status=None),
            [
                'Test 4',
                'Test 3',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly(
                'doc', user2, status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 2',
            ])

    def test_from_user(self):
        """Testing ReviewRequest.objects.from_user"""
        user1 = User.objects.get(username='doc')

        self.create_review_request(summary='Test 1',
                                   public=True,
                                   submitter=user1)

        self.create_review_request(summary='Test 2',
                                   public=False,
                                   submitter=user1)

        self.create_review_request(summary='Test 3',
                                   public=True,
                                   status='S',
                                   submitter=user1)

        self.assertValidSummaries(
            ReviewRequest.objects.from_user('doc', local_site=None),
            [
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user('doc', status=None,
                                            local_site=None),
            [
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user(
                'doc', user=user1, status=None, local_site=None),
            [
                'Test 3',
                'Test 2',
                'Test 1',
            ])

    def test_to_user(self):
        """Testing ReviewRequest.objects.to_user"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    status='S')
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 3',
                                                    publish=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 4',
                                                    publish=True,
                                                    status='S',
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        self.assertValidSummaries(
            ReviewRequest.objects.to_user('doc', local_site=None),
            [
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user('doc', status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user(
                'doc', user=user2, status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
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
