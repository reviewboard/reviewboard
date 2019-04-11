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
        with self.siteconfig_settings({'auth_require_sitewide_login': False},
                                      reload_settings=False):
            response = self.client.get('/r/new')
            self.assertEqual(response.status_code, 301)

            response = self.client.get('/r/new/')
            self.assertEqual(response.status_code, 302)

            self.client.login(username='grumpy', password='grumpy')

            response = self.client.get('/r/new/')
            self.assertEqual(response.status_code, 200)

    def test_read_only_mode_for_users(self):
        """Testing NewReviewRequestView when in read-only mode for regular
        users
        """
        self.siteconfig = SiteConfiguration.objects.get_current()
        settings = {
            'site_read_only': True,
        }

        with self.siteconfig_settings(settings):
            # Ensure user is redirected when trying to create new review
			# request.
            self.client.logout()
            self.client.login(username='doc', password='doc')

            resp = self.client.get('/r/new/')

            self.assertEqual(resp.status_code, 302)

    def test_read_only_mode_for_superusers(self):
        """Testing NewReviewRequestView when in read-only mode for superusers
        """
        self.siteconfig = SiteConfiguration.objects.get_current()
        settings = {
            'site_read_only': True,
        }

        with self.siteconfig_settings(settings):
            # Ensure admin can still access new while in read-only mode.
            self.client.logout()
            self.client.login(username='admin', password='admin')

            resp = self.client.get('/r/new/')

            self.assertEqual(resp.status_code, 200)
