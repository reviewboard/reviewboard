"""Views for the Forgejo hosting service.

Version Added:
    7.1
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View
from pydantic import BaseModel, ValidationError

from reviewboard.admin.server import get_server_url
from reviewboard.hostingsvcs.hook_utils import (
    close_all_review_requests,
    get_git_branch_name,
    get_repository_for_hook,
    get_review_request_id,
)

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)


class PushWebHookPayload(BaseModel):
    """Data for the push event WebHook payload.

    Version Added:
        7.1
    """

    class _Commit(BaseModel):
        id: str
        message: str

    commits: list[_Commit]
    ref: str


class WebHookView(View):
    """WebHook handler for Forgejo.

    Version Added:
        7.1
    """

    def post(
        self,
        request: HttpRequest,
        *,
        local_site_name: (str | None) = None,
        repository_id: int,
        hosting_service_id: str,
    ) -> HttpResponse:
        """Handle a POST request to the view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the Forgejo server.

            local_site_name (str):
                The Local Site name, if available.

            repository_id (int):
                The ID of the repository.

            hosting_service_id (str):
                The name of the hosting service.

        Returns:
            django.http.HttpResponse:
            The response to send back to the server.
        """
        hook_event = request.META.get('HTTP_X_FORGEJO_EVENT')

        if hook_event != 'push':
            return HttpResponseBadRequest(
                'Only the "push" event is supported.')

        repository = get_repository_for_hook(
            repository_id=repository_id,
            hosting_service_id=hosting_service_id,
            local_site_name=local_site_name)

        signature = request.META.get('HTTP_X_FORGEJO_SIGNATURE')

        if not signature:
            logger.error('Forgejo WebHook: received POST with a missing '
                         'signature (repository %r).',
                         repository)

            return HttpResponseBadRequest(
                'X-Forgejo-Signature header was missing or blank.')

        m = hmac.new(repository.get_or_create_hooks_uuid().encode(),
                     request.body, hashlib.sha256)

        if m.hexdigest() != signature:
            logger.error('Forgejo WebHook: received incorrect signature '
                         '(repository %r).',
                         repository)

            return HttpResponseBadRequest(
                'Payload signature could not be validated.')

        try:
            payload = PushWebHookPayload.model_validate_json(request.body)
        except ValidationError as e:
            logger.error('Forgejo WebHook: Could not validate payload content '
                         '(repository %r): %s',
                         repository, e)

            return HttpResponseBadRequest(
                'Payload could not be parsed, see Review Board log for '
                'details.')

        server_url = get_server_url(request=request)
        review_request_id_to_commits: defaultdict[int | None, list[str]] = \
            defaultdict(list)
        branch_name = get_git_branch_name(payload.ref)

        for commit in payload.commits:
            review_request_id = get_review_request_id(
                commit_message=commit.message,
                server_url=server_url,
                commit_id=commit.id,
                repository=repository)
            assert review_request_id is not None

            review_request_id_to_commits[review_request_id].append(
                f'{branch_name} ({commit.id[:7]})')

        if review_request_id_to_commits:
            logger.info(
                'Forgejo WebHook: Closing review requests %s',
                ', '.join(str(key) for key in review_request_id_to_commits))

            close_all_review_requests(
                review_request_id_to_commits=review_request_id_to_commits,
                local_site_name=local_site_name,
                repository=repository,
                hosting_service_id=hosting_service_id)

        return HttpResponse()
