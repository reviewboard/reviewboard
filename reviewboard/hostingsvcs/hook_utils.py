from __future__ import unicode_literals

import logging
import re

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import resolve, Resolver404
from django.http import Http404
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.views import _find_review_request_object
from reviewboard.site.urlresolvers import local_site_reverse


def get_server_url(request):
    """Returns the server's URL."""
    site = Site.objects.get_current()
    siteconfig = SiteConfiguration.objects.get_current()

    return '%s://%s%s' % (siteconfig.get('site_domain_method'), site.domain,
                          local_site_reverse('root', request=request))


def get_git_branch_name(ref_name):
    """Returns the branch name corresponding to the specified ref name."""
    branch_ref_prefix = 'refs/heads/'

    if ref_name.startswith(branch_ref_prefix):
        return ref_name[len(branch_ref_prefix):]


def get_review_request_id(commit_message, server_url):
    """Returns the review request ID referenced in the commit message.

    We assume there is at most one review request associated with each commit.
    If a matching review request cannot be found, we return 0.
    """
    regex = settings.HOSTINGSVCS_HOOK_REGEX % {
        'server_url': server_url,
    }

    pattern = re.compile(regex, settings.HOSTINGSVCS_HOOK_REGEX_FLAGS)
    match = pattern.search(commit_message)
    return (match and int(match.group('id'))) or 0


def close_review_request(review_request, review_request_id, description):
    """Closes the specified review request as submitted."""
    if review_request.status == ReviewRequest.SUBMITTED:
        logging.warning('Review request #%s is already submitted.',
                        review_request_id)
        return

    review_request.close(ReviewRequest.SUBMITTED, description=description)
    logging.debug('Review request #%s is set to %s.',
                  review_request_id, review_request.status)


def close_all_review_requests(review_id_to_commits):
    """Closes each review request in the given dictionary as submitted.

    The provided dictionary should map a review request ID (int) to commits
    associated with that review request ID (list of strings). Commits that are not
    associated with any review requests have the review request ID 0.
    """
    for review_request_id in review_id_to_commits:
        if not review_request_id:
            logging.debug('No matching review request ID found for commits: ' +
                          ', '.join(review_id_to_commits[review_request_id]))
            continue

        try:
            match = resolve('/r/%s/' % review_request_id)
        except Resolver404, e:
            logging.error('Could not resolve URL: %s', e)
            continue

        local_site = match.kwargs.get('local_site', None)
        description = ('Pushed to ' +
                       ', '.join(review_id_to_commits[review_request_id]))

        try:
            review_request = \
                _find_review_request_object(review_request_id, local_site)
        except Http404, e:
            logging.error('Review request #%s does not exist.',
                          review_request_id)
            continue

        close_review_request(review_request, review_request_id, description)
