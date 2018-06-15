"""Unit tests for reviewboard.accounts.models.ReviewRequestVisit."""

from __future__ import unicode_literals

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.testing import TestCase


class ReviewRequestVisitTests(TestCase):
    """Unit tests for reviewboard.accounts.models.ReviewRequestVisit."""

    fixtures = ['test_users']

    def test_default_visibility(self):
        """Testing ReviewRequestVisit.visibility default value"""
        review_request = self.create_review_request(publish=True)
        self.client.login(username='admin', password='admin')
        self.client.get(review_request.get_absolute_url())

        visit = ReviewRequestVisit.objects.get(
            user__username='admin', review_request=review_request.id)

        self.assertEqual(visit.visibility, ReviewRequestVisit.VISIBLE)
