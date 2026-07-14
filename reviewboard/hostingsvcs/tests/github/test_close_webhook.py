"""Unit tests for the repo-specific GitHub close webhook handler.

Version Added:
    9.0:
    Split out from reviewboard.hostingsvcs.tests.test_github
"""

from __future__ import annotations

import hashlib
import hmac
from typing import TYPE_CHECKING

from djblets.testing.decorators import add_fixtures

from reviewboard.hostingsvcs.hook_utils import logger
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.test.client import _MonkeyPatchedWSGIResponse


class CloseSubmittedHookTests(GitHubTestCase):
    """Unit tests for the GitHub close-submitted webhook."""

    fixtures: Sequence[str] = ['test_users', 'test_scmtools']

    def test_close_submitted_hook(self) -> None:
        """Testing GitHub close_submitted hook with event=push"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_with_local_site(self) -> None:
        """Testing GitHub close_submitted hook with event=push and using a
        Local Site
        """
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_with_unpublished_review_request(
        self,
    ) -> None:
        """Testing GitHub close_submitted hook with event=push and an
        un-published review request
        """
        self._test_post_commit_hook(publish=False)

    def test_close_submitted_hook_ping(self) -> None:
        """Testing GitHub close_submitted hook with event=ping"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid(),
            event='ping')
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_repo(self) -> None:
        """Testing GitHub close_submitted hook with event=push and invalid
        repository
        """
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_site(self) -> None:
        """Testing GitHub close_submitted hook with event=push and invalid
        Local Site
        """
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            local_site_name='badsite',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_service_id(self) -> None:
        """Testing GitHub close_submitted hook with event=push and invalid
        hosting service ID
        """
        # We'll test against Bitbucket for this test.
        account = self.create_hosting_account()
        account.service_name = 'bitbucket'
        account.save()

        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_event(self) -> None:
        """Testing GitHub close_submitted hook with invalid event"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid(),
            event='foo')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_signature(self) -> None:
        """Testing GitHub close_submitted hook with invalid signature"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret='bad-secret')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_review_requests(self) -> None:
        """Testing GitHub close_submitted hook with event=push and invalid
        review requests
        """
        self.spy_on(logger.error)

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url='/r/9999/',
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

        self.assertSpyCalledWith(
            logger.error,
            'close_all_review_requests: Review request #%s does not exist.',
            9999)

    def _test_post_commit_hook(
        self,
        local_site: (LocalSite | None) = None,
        publish: bool = True,
    ) -> None:
        """Testing posting to a commit hook.

        This will simulate pushing a commit and posting the resulting webhook
        payload from GitHub to the handler for the hook.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning the review request.

            publish (bool, optional):
                Whether to test with a published review request.
        """
        account = self.create_hosting_account(local_site=local_site)
        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=publish)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (1c44b46)')

    def _post_commit_hook_payload(
        self,
        post_url: str,
        review_request_url: str,
        secret: str,
        event: str = 'push',
    ) -> _MonkeyPatchedWSGIResponse:
        """Post a payload for a hook for testing.

        Args:
            post_url (str):
                The URL to post to.

            review_request_url (str):
                The URL of the review request being represented in the
                payload.

            secret (str):
                The HMAC secret for the message.

            event (str, optional):
                The webhook event.

        Results:
            django.core.handlers.request.wsgi.WSGIRequest:
            The post request.
        """
        payload = self.dump_json({
            # NOTE: This payload only contains the content we make
            #       use of in the hook.
            'ref': 'refs/heads/master',
            'commits': [
                {
                    'id': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                    'message': (
                        f'This is my fancy commit\n'
                        f'\n'
                        f'Reviewed at http://example.com'
                        f'{review_request_url}'
                    ),
                },
            ]
        })

        m = hmac.new(secret.encode('utf-8'), payload, hashlib.sha1)

        return self.client.post(
            post_url,
            payload,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT=event,
            HTTP_X_HUB_SIGNATURE=f'sha1={m.hexdigest()}')
