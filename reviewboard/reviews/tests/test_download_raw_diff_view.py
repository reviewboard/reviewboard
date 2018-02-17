"""Unit tests for reviewboard.reviews.views.DownloadRawDiffView."""

from __future__ import unicode_literals

from reviewboard.testing import TestCase


class DownloadRawDiffViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.DownloadRawDiffView."""

    fixtures = ['test_users', 'test_scmtools']

    # Bug #3384
    def test_sends_correct_content_disposition(self):
        """Testing DownloadRawDiffView sends correct Content-Disposition"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        self.create_diffset(review_request=review_request)

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename=diffset')

    # Bug #3704
    def test_normalize_commas_in_filename(self):
        """Testing DownloadRawDiffView removes commas in filename"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        # Create a diffset with a comma in its name.
        self.create_diffset(review_request=review_request, name='test, comma')

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        content_disposition = response['Content-Disposition']
        filename = content_disposition[len('attachment; filename='):]
        self.assertFalse(',' in filename)
