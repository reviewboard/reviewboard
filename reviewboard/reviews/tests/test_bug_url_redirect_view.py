"""Unit tests for reviewboard.reviews.views.BugURLRedirectView."""

from __future__ import unicode_literals

from django.core.urlresolvers import reverse

from reviewboard.testing import TestCase


class BugURLRedirectViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.BugURLRedirectView."""

    fixtures = ['test_users', 'test_scmtools']

    # Bug #4080
    def test_with_custom_scheme(self):
        """Testing BugURLRedirectView with non-HTTP scheme loads correctly"""
        # Create a repository with a bug tracker that uses a non-standard
        # url scheme.
        repository = self.create_repository(public=True,
                                            bug_tracker='scheme://bugid=%s')
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        url = reverse('bug_url', args=(review_request.pk, '1'))
        response = self.client.get(url)

        # Test if we redirected to the correct url with correct bugID.
        self.assertEqual(response['Location'], 'scheme://bugid=1')
