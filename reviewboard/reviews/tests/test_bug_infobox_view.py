"""Unit tests for the bug infobox."""

from django.http import HttpResponseNotFound
from django.urls import reverse

from reviewboard.testing import TestCase


class BugInfoboxViewTests(TestCase):
    """Unit tests for the bug infobox."""

    fixtures = ['test_users']

    def test_with_attachment_only_review_request(self):
        """Testing the BugInfoboxView with a review request that does not have
        a repository
        """
        review_request = self.create_review_request(publish=True)
        url = reverse('bug_infobox', args=(review_request.pk, '1'))
        response = self.client.get(url)

        self.assertIsInstance(response, HttpResponseNotFound)
