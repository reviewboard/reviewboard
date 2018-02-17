"""Unit tests for reviewboard.reviews.views.NewReviewRequestView."""

from __future__ import unicode_literals

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.testing import TestCase


class NewReviewRequestViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.NewReviewRequestView."""

    fixtures = ['test_users']

    # TODO: Split this up into multiple unit tests, and do a better job of
    #       checking for expected results.
    def test_get(self):
        """Testing NewReviewRequestView.get"""
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('auth_require_sitewide_login', False)
        siteconfig.save()

        response = self.client.get('/r/new')
        self.assertEqual(response.status_code, 301)

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 302)

        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 200)
