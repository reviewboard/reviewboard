"""Unit tests for reviewboard.accounts.managers.ReviewRequestVisitManager."""

from django.contrib.auth.models import User
from django.db.models import Q

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.testing import TestCase


class ReviewRequestVisitTests(TestCase):
    """Unit tests for reviewboard.accounts.managers.ReviewRequestVisitManager.
    """

    fixtures = ['test_users']

    def test_update_visibility_create(self):
        """Testing ReviewRequestVisitManager.update_visibility
        creates a new visit
        """
        review_request = self.create_review_request(publish=True)
        user = User.objects.get(username='admin')

        visit = ReviewRequestVisit.objects.update_visibility(
            review_request, user, ReviewRequestVisit.ARCHIVED)

        self.assertEqual(visit.visibility, ReviewRequestVisit.ARCHIVED)

    def test_update_visibility_update_visible(self):
        """Testing ReviewRequestVisitManager.update_visibility
        updates existing visit with visible
        """
        review_request = self.create_review_request(publish=True)
        user = User.objects.get(username='admin')

        visit = ReviewRequestVisit.objects.create(
            review_request=review_request, user=user,
            visibility=ReviewRequestVisit.VISIBLE)

        queries = [
            {
                'model': ReviewRequestVisit,
                'select_for_update': True,
                'where': Q(review_request=review_request, user=user),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'UPDATE',
                'where': Q(pk=visit.pk),
            },
        ]

        with self.assertQueries(queries, num_statements=4):
            visit = ReviewRequestVisit.objects.update_visibility(
                review_request, user, ReviewRequestVisit.VISIBLE)

        self.assertEqual(visit.visibility, ReviewRequestVisit.VISIBLE)

    def test_update_visibility_update_archive(self):
        """Testing ReviewRequestVisitManager.update_visibility
        updates existing visit with archive
        """
        review_request = self.create_review_request(publish=True)
        user = User.objects.get(username='admin')

        ReviewRequestVisit.objects.create(
            review_request=review_request, user=user,
            visibility=ReviewRequestVisit.VISIBLE)
        visit = ReviewRequestVisit.objects.update_visibility(
            review_request, user, ReviewRequestVisit.ARCHIVED)

        self.assertEqual(visit.visibility, ReviewRequestVisit.ARCHIVED)
