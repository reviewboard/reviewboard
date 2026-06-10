"""Views for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic.base import View

from reviewboard.admin.server import get_server_url
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_git_branch_name,
                                                get_repository_for_hook,
                                                get_review_request_id)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from django.http import HttpRequest
    from typelets.json import JSONDict

    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class GitHubHookViews:
    """Container class for hook views."""

    @staticmethod
    @require_POST
    def post_receive_hook_close_submitted(
        request: HttpRequest,
        local_site_name: (str | None) = None,
        repository_id: (int | None) = None,
        hosting_service_id: (str | None) = None,
    ) -> HttpResponse:
        """Close review requests as submitted automatically after a push.

        Args:
            request (django.http.HttpRequest):
                The request from the Bitbucket webhook.

            local_site_name (str, optional):
                The local site name, if available.

            repository_id (int, optional):
                The pk of the repository, if available.

            hosting_service_id (str, optional):
                The name of the hosting service.

        Returns:
            django.http.HttpResponse:
            A response for the request.
        """
        hook_event = request.META.get('HTTP_X_GITHUB_EVENT')

        if hook_event == 'ping':
            # GitHub is checking that this hook is valid, so accept the request
            # and return.
            return HttpResponse()
        elif hook_event != 'push':
            return HttpResponseBadRequest(
                'Only "ping" and "push" events are supported.')

        assert repository_id is not None
        assert hosting_service_id is not None

        repository = get_repository_for_hook(
            repository_id=repository_id,
            hosting_service_id=hosting_service_id,
            local_site_name=local_site_name)

        # Validate the hook against the stored UUID.
        m = hmac.new(repository.get_or_create_hooks_uuid().encode('utf-8'),
                     request.body, hashlib.sha1)

        sig_parts = request.META.get('HTTP_X_HUB_SIGNATURE', '').split('=')

        if sig_parts[0] != 'sha1' or len(sig_parts) != 2:
            # We don't know what this is.
            return HttpResponseBadRequest('Unsupported HTTP_X_HUB_SIGNATURE')

        if m.hexdigest() != sig_parts[1]:
            return HttpResponseBadRequest('Bad signature.')

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except ValueError as e:
            logger.error('The payload is not in JSON format: %s', e)
            return HttpResponseBadRequest('Invalid payload format')

        server_url = get_server_url(request=request)
        review_request_id_to_commits = \
            GitHubHookViews._get_review_request_id_to_commits_map(
                payload, server_url, repository)

        if review_request_id_to_commits:
            close_all_review_requests(
                review_request_id_to_commits=review_request_id_to_commits,
                local_site_name=local_site_name,
                repository=repository,
                hosting_service_id=hosting_service_id)

        return HttpResponse()

    @staticmethod
    def _get_review_request_id_to_commits_map(
        payload: JSONDict,
        server_url: str,
        repository: Repository,
    ) -> Mapping[int | None, Sequence[str]] | None:
        """Return a mapping of review request ID to a list of commits.

        If a commit's commit message does not contain a review request ID,
        we append the commit to the key None.

        Args:
            payload (dict):
                The decoded webhook payload.

            server_url (str):
                The URL of the Review Board server.

            repository (reviewboard.scmtools.models.Repository):
                The repository object.

        Returns:
            dict:
            A mapping from review request ID to a list of matching commits from
            the payload.
        """
        review_request_id_to_commits_map = defaultdict(list)

        ref_name = payload.get('ref')

        if not ref_name:
            return None

        assert isinstance(ref_name, str)

        branch_name = get_git_branch_name(ref_name)
        if not branch_name:
            return None

        commits = payload.get('commits', [])
        assert isinstance(commits, list)

        for commit in commits:
            assert isinstance(commit, dict)

            commit_hash = commit.get('id')
            assert isinstance(commit_hash, str)

            commit_message = commit.get('message')
            assert isinstance(commit_message, str)

            review_request_id = get_review_request_id(
                commit_message=commit_message,
                server_url=server_url,
                commit_id=commit_hash,
                repository=repository)

            review_request_id_to_commits_map[review_request_id].append(
                f'{branch_name} ({commit_hash[:7]})')

        return review_request_id_to_commits_map


@method_decorator(csrf_exempt, name='dispatch')
class GitHubAppWebhookView(View):
    """Receive webhook events from a GitHub App.

    A GitHub App has a single, app-wide webhook URL that receives events from
    every account the app is installed on.

    This is currently a stub. It acknowledges deliveries so GitHub considers
    the webhook healthy, but does not yet act on any events.

    Version Added:
        9.0
    """

    def post(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP POST requests.

        Args:
            request (django.http.HttpRequest):
                The webhook request from GitHub.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            An empty response acknowledging the delivery.
        """
        event = request.META.get('HTTP_X_GITHUB_EVENT', '')

        # TODO: Verify the X-Hub-Signature-256 header against the app's stored
        # webhook secret and dispatch events once handlers exist.
        logger.debug('Received GitHub App webhook event: %s', event)

        return HttpResponse(status=204)
