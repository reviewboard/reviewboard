"""Unit tests for reviewboard.accounts.models.Trophy."""

from django.contrib.auth.models import User
from django.test.client import RequestFactory

from reviewboard.accounts.models import Trophy
from reviewboard.accounts.trophies import TrophyType
from reviewboard.deprecation import RemovedInReviewBoard40Warning
from reviewboard.testing import TestCase


class TrophyTests(TestCase):
    """Unit tests for reviewboard.accounts.models.Trophy."""

    fixtures = ['test_users']

    def test_is_fish_trophy_awarded_for_new_review_request(self):
        """Testing if a fish trophy is awarded for a new review request"""
        user1 = User.objects.get(username='doc')
        category = 'fish'
        review_request = self.create_review_request(publish=True, id=3223,
                                                    submitter=user1)
        trophies = Trophy.objects.get_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_fish_trophy_awarded_for_older_review_request(self):
        """Testing if a fish trophy is awarded for an older review request"""
        user1 = User.objects.get(username='doc')
        category = 'fish'
        review_request = self.create_review_request(publish=True, id=1001,
                                                    submitter=user1)
        del review_request.extra_data['calculated_trophies']
        trophies = Trophy.objects.get_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_milestone_trophy_awarded_for_new_review_request(self):
        """Testing if a milestone trophy is awarded for a new review request
        """
        user1 = User.objects.get(username='doc')
        category = 'milestone'
        review_request = self.create_review_request(publish=True, id=1000,
                                                    submitter=user1)
        trophies = Trophy.objects.compute_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_milestone_trophy_awarded_for_older_review_request(self):
        """Testing if a milestone trophy is awarded for an older review
        request
        """
        user1 = User.objects.get(username='doc')
        category = 'milestone'
        review_request = self.create_review_request(publish=True, id=10000,
                                                    submitter=user1)
        del review_request.extra_data['calculated_trophies']
        trophies = Trophy.objects.compute_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_no_trophy_awarded(self):
        """Testing if no trophy is awarded"""
        user1 = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True, id=999,
                                                    submitter=user1)
        trophies = Trophy.objects.compute_trophies(review_request)
        self.assertFalse(trophies)
