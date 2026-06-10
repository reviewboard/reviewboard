"""Unit tests for the GitHub App webhook handler.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.site.urlresolvers import local_site_reverse


class GitHubAppWebhookViewTests(GitHubTestCase):
    """Unit tests for GitHubAppWebhookView.

    Version Added:
        9.0
    """

    def test_post_acknowledges_delivery(self) -> None:
        """Testing GitHubAppWebhookView POST acknowledges the delivery"""
        url = local_site_reverse('github-app-webhook',
                                 kwargs={'hosting_service_id': 'github'})

        # GitHub is the caller, so the endpoint accepts an unauthenticated,
        # CSRF-free POST.
        response = self.client.post(url,
                                    data='{}',
                                    content_type='application/json',
                                    HTTP_X_GITHUB_EVENT='ping')

        self.assertEqual(response.status_code, 204)

    def test_get_not_allowed(self) -> None:
        """Testing GitHubAppWebhookView rejects GET requests"""
        url = local_site_reverse('github-app-webhook',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
