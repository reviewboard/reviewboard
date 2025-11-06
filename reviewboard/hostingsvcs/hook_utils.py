"""Utilities for WebHook handlers."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


logger = logging.getLogger(__name__)


def get_git_branch_name(
    ref_name: str,
) -> str:
    """Return the branch name corresponding to the specified ref name.

    Args:
        ref_name (str):
            The name of the Git reference.

    Returns:
        str:
        The isolated branch name.
    """
    if ref_name.startswith('refs/heads/'):
        return ref_name[len('refs/heads/'):]
    else:
        return ref_name


@deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
def get_repository_for_hook(
    *,
    repository_id: int,
    hosting_service_id: str,
    local_site_name: str | None,
    hooks_uuid: (str | None) = None,
) -> Repository:
    """Return a Repository for the given hook parameters.

    Version Changed:
        7.1:
        Made arguments keyword-only.

    Args:
        repository_id (int):
            The ID of the repository.

        hosting_service_id (str):
            The name of the hosting service.

        local_site_name (str):
            The Local Site name, if available.

        hooks_uuid (str, optional):
            The UUID to use for WebHooks for this repository.

    Returns:
        reviewboard.scmtools.models.Repository:
        The repository object.

    Raises:
        django.http.Http404:
            A repository with the given parameters was not found.
    """
    q = (Q(pk=repository_id) &
         Q(hosting_account__service_name=hosting_service_id))

    if hooks_uuid:
        q &= Q(hooks_uuid=hooks_uuid)

    if local_site_name:
        q &= Q(local_site__name=local_site_name)
    else:
        q &= Q(local_site__isnull=True)

    return get_object_or_404(Repository, q)


@deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
def get_review_request_id(
    *,
    commit_message: str,
    server_url: str,
    commit_id: (str | None) = None,
    repository: (Repository | None) = None,
) -> int | None:
    """Return the review request ID matching the pushed commit.

    We first use a regex (that can be overridden in settings_local.py) to try
    to find a matching review request ID in the commit message. If no match is
    found with the regex, we then try to find a review request with a matching
    commit ID.

    We assume there is at most one review request associated with each commit.
    If a matching review request cannot be found, we return None.

    Version Changed:
        7.1:
        Made arguments keyword-only.

    Args:
        commit_message (str):
            The commit message from the hosting service.

        server_url (str):
            The URL to the Review Board server.

        commit_id (str):
            The ID of the commit.

        repository (reviewboard.scmtools.models.Repository):
            The repository for the commit.

    Returns:
        int:
        The ID of the review request that corresponds to the pushed commit. If
        no review request could be found, this will be ``None``.
    """
    regex = settings.HOSTINGSVCS_HOOK_REGEX % {
        'server_url': re.escape(server_url),
    }

    pattern = re.compile(regex, settings.HOSTINGSVCS_HOOK_REGEX_FLAGS)
    match = pattern.search(commit_message)

    if match:
        try:
            review_request_id = int(match.group('id'))
        except ValueError:
            logger.error('The review request ID must be an integer.')
            review_request_id = None
    elif commit_id:
        assert repository

        try:
            review_request = ReviewRequest.objects.get(
                commit_id=str(commit_id),
                repository=repository)
            review_request_id = review_request.display_id
        except ReviewRequest.DoesNotExist:
            review_request_id = None
    else:
        review_request_id = None

    return review_request_id


@deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
def close_review_request(
    *,
    review_request: ReviewRequest,
    review_request_id: int,
    description: str,
) -> None:
    """Close the specified review request as submitted.

    Version Changed:
        7.1:
        Made arguments keyword-only.

    Args:
        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request to close.

        review_request_id (int):
            The ID of the review request.

        description (str):
            The close description to use.
    """
    if review_request.status == ReviewRequest.SUBMITTED:
        logger.warning('Review request #%s is already submitted.',
                       review_request_id)
        return

    # Closing as submitted will fail if the review request was never public. In
    # this case, publish first.
    if not review_request.public:
        review_request.publish(review_request.submitter, trivial=True,
                               validate_fields=False)

    review_request.close(ReviewRequest.SUBMITTED, description=description)
    logger.debug('Review request #%s is set to %s.',
                 review_request_id, review_request.status)


@deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
def close_all_review_requests(
    *,
    review_request_id_to_commits: Mapping[int | None, Sequence[str]],
    local_site_name: str | None,
    repository: Repository,
    hosting_service_id: str,
) -> None:
    """Close each review request in the given dictionary as submitted.

    The provided dictionary should map a review request ID (int) to commits
    associated with that review request ID (list of strings). Commits that are
    not associated with any review requests have the key None.

    Version Changed:
        7.1:
        Made arguments keyword-only.

    Args:
        review_request_id_to_commits (dict):
            A mapping from review request ID to a list of

        local_site_name (str):
            The Local Site name, if available.

        repository (reviewboard.scmtools.models.Repository):
            The repository for all review requests.

        hosting_service_id (str):
            The name of the hosting service.
    """
    if local_site_name:
        try:
            local_site = LocalSite.objects.get(name=local_site_name)
        except LocalSite.DoesNotExist:
            logger.error('close_all_review_requests: Local Site %s does '
                         'not exist.',
                         local_site_name)
            return
    else:
        local_site = None

    # Some of the entries we get may have 'None' keys, so filter them out.
    review_request_ids = [
        review_request_id
        for review_request_id in review_request_id_to_commits
        if review_request_id is not None
    ]

    if not review_request_ids:
        return

    # Look up all review requests that match the given repository, hosting
    # service ID, and Local Site.
    q = (Q(repository=repository) &
         Q(repository__hosting_account__service_name=hosting_service_id))

    if local_site:
        q &= Q(local_id__in=review_request_ids) & Q(local_site=local_site)
    else:
        q &= Q(pk__in=review_request_ids)

    review_requests = list(ReviewRequest.objects.filter(q))

    # Check if there are any listed that we couldn't find, and log them.
    if len(review_request_ids) != len(review_requests):
        id_to_review_request = {
            review_request.display_id: review_request
            for review_request in review_requests
        }

        for review_request_id in review_request_ids:
            if review_request_id not in id_to_review_request:
                logger.error('close_all_review_requests: Review request #%s '
                             'does not exist.',
                             review_request_id)

    # Close any review requests we did find.
    for review_request in review_requests:
        review_request_id = review_request.display_id

        commits_info = ', '.join(
            review_request_id_to_commits[review_request_id])

        close_review_request(
            review_request=review_request,
            review_request_id=review_request_id,
            description=f'Pushed to {commits_info}',
        )
