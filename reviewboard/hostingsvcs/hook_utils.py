from __future__ import unicode_literals

import logging
import re

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import six

from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite


def get_git_branch_name(ref_name):
    """Returns the branch name corresponding to the specified ref name."""
    branch_ref_prefix = 'refs/heads/'

    if ref_name.startswith(branch_ref_prefix):
        return ref_name[len(branch_ref_prefix):]


def get_repository_for_hook(repository_id, hosting_service_id,
                            local_site_name, hooks_uuid=None):
    """Returns a Repository for the given hook parameters."""
    q = (Q(pk=repository_id) &
         Q(hosting_account__service_name=hosting_service_id))

    if hooks_uuid:
        q &= Q(hooks_uuid=hooks_uuid)

    if local_site_name:
        q &= Q(local_site__name=local_site_name)
    else:
        q &= Q(local_site__isnull=True)

    return get_object_or_404(Repository, q)


def get_review_request_id(commit_message, server_url, commit_id=None,
                          repository=None):
    """Returns the review request ID matching the pushed commit.

    We first use a regex (that can be overriden in settings_local.py) to try to
    find a matching review request ID in the commit message. If no match is
    found with the regex, we then try to find a review request with a matching
    commit ID.

    We assume there is at most one review request associated with each commit.
    If a matching review request cannot be found, we return None.
    """
    regex = settings.HOSTINGSVCS_HOOK_REGEX % {
        'server_url': server_url,
    }

    pattern = re.compile(regex, settings.HOSTINGSVCS_HOOK_REGEX_FLAGS)
    match = pattern.search(commit_message)

    if match:
        try:
            review_request_id = int(match.group('id'))
        except ValueError:
            logging.error('The review request ID must be an integer.')
            review_request_id = None
    elif commit_id:
        assert repository

        try:
            review_request = ReviewRequest.objects.get(
                commit_id=six.text_type(commit_id),
                repository=repository)
            review_request_id = review_request.display_id
        except ReviewRequest.DoesNotExist:
            review_request_id = None

    return review_request_id


def close_review_request(review_request, review_request_id, description):
    """Closes the specified review request as submitted."""
    if review_request.status == ReviewRequest.SUBMITTED:
        logging.warning('Review request #%s is already submitted.',
                        review_request_id)
        return

    # Closing as submitted will fail if the review request was never public. In
    # this case, publish first (which will generate an e-mail, but that's
    # probably desirable anyway).
    if not review_request.public:
        review_request.publish(review_request.submitter)

    review_request.close(ReviewRequest.SUBMITTED, description=description)
    logging.debug('Review request #%s is set to %s.',
                  review_request_id, review_request.status)


def close_all_review_requests(review_request_id_to_commits, local_site_name,
                              repository, hosting_service_id):
    """Closes each review request in the given dictionary as submitted.

    The provided dictionary should map a review request ID (int) to commits
    associated with that review request ID (list of strings). Commits that are
    not associated with any review requests have the key None.
    """
    if local_site_name:
        try:
            local_site = LocalSite.objects.get(name=local_site_name)
        except LocalSite.DoesNotExist:
            logging.error('close_all_review_requests: Local Site %s does '
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
        id_to_review_request = dict(*[
            (review_request.display_id, review_request)
            for review_request in review_requests
        ])

        for review_request_id in review_request_ids:
            if review_request_id not in id_to_review_request:
                logging.error('close_all_review_requests: Review request #%s '
                              'does not exist.',
                              review_request_id)

    # Close any review requests we did find.
    for review_request in review_requests:
        review_request_id = review_request.display_id

        close_review_request(
            review_request,
            review_request_id,
            ('Pushed to ' +
             ', '.join(review_request_id_to_commits[review_request_id])))
