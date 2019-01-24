"""Unit tests for BaseReviewRequestDetails."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from reviewboard.reviews.models import DefaultReviewer
from reviewboard.testing import TestCase


class BaseReviewRequestDetailsTests(TestCase):
    """Unit tests for BaseReviewRequestDetails."""

    fixtures = ['test_scmtools']

    def test_add_default_reviewers_with_users(self):
        """Testing BaseReviewRequestDetails.add_default_reviewers with users"""
        user1 = User.objects.create_user(username='user1',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2',
                                    email='user2@example.com')
        user3 = User.objects.create(username='user3',
                                    email='user3@example.com',
                                    is_active=False)

        # Create the default reviewers.
        default_reviewer1 = DefaultReviewer.objects.create(name='Test 1',
                                                           file_regex='.*')
        default_reviewer1.people.add(user1, user2, user3)

        # Create the review request and accompanying diff.
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=user1)
        diffset = self.create_diffset(review_request)
        self.create_filediff(diffset)

        # The following queries will be executed:
        #
        # 1. Diffset
        # 2. The file list
        # 3. The default reviewer list
        # 4. User list for all matched default reviewers
        # 5. Group list for all matched default reviewers
        # 6. Existing user ID list (m2m.add())
        # 7. Setting new users (m2m.add())
        with self.assertNumQueries(7):
            review_request.add_default_reviewers()

        self.assertEqual(list(review_request.target_people.all()),
                         [user1, user2])
        self.assertEqual(list(review_request.target_groups.all()),
                         [])

    def test_add_default_reviewers_with_groups(self):
        """Testing BaseReviewRequestDetails.add_default_reviewers with groups
        """
        user1 = User.objects.create_user(username='user1',
                                         email='user1@example.com')

        group1 = self.create_review_group(name='Group 1')
        group2 = self.create_review_group(name='Group 2')

        # Create the default reviewers.
        default_reviewer1 = DefaultReviewer.objects.create(name='Test 1',
                                                           file_regex='.*')
        default_reviewer1.groups.add(group1, group2)

        # Create the review request and accompanying diff.
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=user1)
        diffset = self.create_diffset(review_request)
        self.create_filediff(diffset)

        # The following queries will be executed:
        #
        # 1. Diffset
        # 2. The file list
        # 3. The default reviewer list
        # 4. User list for all matched default reviewers
        # 5. Group list for all matched default reviewers
        # 8. Existing group ID list (m2m.add())
        # 9. Setting new groups (m2m.add())
        with self.assertNumQueries(7):
            review_request.add_default_reviewers()

        self.assertEqual(list(review_request.target_groups.all()),
                         [group1, group2])
        self.assertEqual(list(review_request.target_people.all()),
                         [])

    def test_add_default_reviewers_with_users_and_groups(self):
        """Testing BaseReviewRequestDetails.add_default_reviewers with both
        users and groups
        """
        user1 = User.objects.create_user(username='user1',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2',
                                    email='user2@example.com')

        group1 = self.create_review_group(name='Group 1')
        group2 = self.create_review_group(name='Group 2')

        # Create the default reviewers.
        default_reviewer1 = DefaultReviewer.objects.create(name='Test 1',
                                                           file_regex='.*')
        default_reviewer1.people.add(user1, user2)

        default_reviewer2 = DefaultReviewer.objects.create(name='Test 2',
                                                           file_regex='.*')
        default_reviewer2.groups.add(group1, group2)

        # Create the review request and accompanying diff.
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=user1)
        diffset = self.create_diffset(review_request)
        self.create_filediff(diffset)

        # The following queries will be executed:
        #
        # 1. Diffset
        # 2. The file list
        # 3. The default reviewer list
        # 4. User list for all matched default reviewers
        # 5. Group list for all matched default reviewers
        # 6. Existing user ID list (m2m.add())
        # 7. Setting new users (m2m.add())
        # 8. Existing group ID list (m2m.add())
        # 9. Setting new groups (m2m.add())
        with self.assertNumQueries(9):
            review_request.add_default_reviewers()

        self.assertEqual(list(review_request.target_people.all()),
                         [user1, user2])
        self.assertEqual(list(review_request.target_groups.all()),
                         [group1, group2])

    def test_add_default_reviewers_with_no_matches(self):
        """Testing BaseReviewRequestDetails.add_default_reviewers with no
        matches
        """
        user1 = User.objects.create_user(username='user1',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2',
                                    email='user2@example.com')

        group1 = self.create_review_group(name='Group 1')
        group2 = self.create_review_group(name='Group 2')

        # Create the default reviewers.
        default_reviewer1 = DefaultReviewer.objects.create(name='Test 1',
                                                           file_regex='/foo')
        default_reviewer1.people.add(user1, user2)

        default_reviewer2 = DefaultReviewer.objects.create(name='Test 2',
                                                           file_regex='/bar')
        default_reviewer2.groups.add(group1, group2)

        # Create the review request and accompanying diff.
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=user1)
        diffset = self.create_diffset(review_request)
        self.create_filediff(diffset)

        # The following queries will be executed:
        #
        # 1. Diffset
        # 2. The file list
        # 3. The default reviewer list
        with self.assertNumQueries(3):
            review_request.add_default_reviewers()

        self.assertEqual(list(review_request.target_people.all()), [])
        self.assertEqual(list(review_request.target_groups.all()), [])

    def test_add_default_reviewers_with_no_repository(self):
        """Testing BaseReviewRequestDetails.add_default_reviewers with no
        repository
        """
        user1 = User.objects.create_user(username='user1',
                                         email='user1@example.com')

        # Create the review request and accompanying diff.
        review_request = self.create_review_request(submitter=user1)

        with self.assertNumQueries(0):
            review_request.add_default_reviewers()
