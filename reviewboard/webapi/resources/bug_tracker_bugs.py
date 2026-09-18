"""API resource for searching bugs on a bug tracker.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from djblets.webapi.decorators import (
    webapi_docs,
    webapi_login_required,
    webapi_request_fields,
    webapi_response_errors,
)
from djblets.webapi.errors import (
    DOES_NOT_EXIST,
    NOT_LOGGED_IN,
    PERMISSION_DENIED,
)
from djblets.webapi.fields import IntFieldType, StringFieldType

from reviewboard.hostingsvcs.base import BaseHostingService
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.reviews.models import ReviewRequest
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site

if TYPE_CHECKING:
    from django.http import HttpRequest
    from djblets.webapi.resources.base import WebAPIResourceHandlerResult


logger = logging.getLogger(__name__)


#: The default number of results to return when searching the tracker.
#:
#: Version Added:
#:     9.0
BUG_SEARCH_DEFAULT_RESULTS = 25


#: The maximum number of results to return when searching the tracker.
#:
#: Version Added:
#:     9.0
BUG_SEARCH_MAX_RESULTS = 100


class BugTrackerBugsResource(WebAPIResource):
    """Provides bug search on a configured bug tracker.

    This proxies typeahead search queries to the bug tracker. It requires
    a review request, and only serves users who may use the bug tracker
    on that review request.

    Version Added:
        9.0
    """

    added_in = '9.0'

    name = 'bug'
    name_plural = 'bugs'
    policy_id = 'bug_tracker_bugs'
    allowed_methods = ('GET',)

    @webapi_docs(
        """
        Searches for bugs on the bug tracker.

        This requires a review request that the bug tracker applies to.
        The requesting user must have access to the review request and
        pass the bug tracker's user conditions.
        """
    )
    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required={
            'q': {
                'type': StringFieldType,
                'description': 'The search query.',
            },
            'review-request': {
                'type': IntFieldType,
                'description': 'The ID of the review request the bugs '
                               'would be linked to.',
            },
        },
        optional={
            'max-results': {
                'type': IntFieldType,
                'description': f'The maximum number of results to return. '
                               f'Defaults to {BUG_SEARCH_DEFAULT_RESULTS}.',
            },
        },
    )
    def get_list(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> WebAPIResourceHandlerResult:
        """Handle HTTP GET requests for the list resource.

        This looks up the bug tracker and review request, checks that the
        tracker applies to the review request and that the user passes its
        conditions, and then runs the search on the tracker's service.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments parsed from the URL.

            **kwargs (dict):
                Keyword arguments parsed from the URL.

        Returns:
            djblets.webapi.resources.base.WebAPIResourceHandlerResult:
            The result of the request.
        """
        try:
            bug_tracker = ConfiguredBugTracker.objects.get(
                pk=kwargs['bug_tracker_id'],
                enabled=True)
        except ConfiguredBugTracker.DoesNotExist:
            return DOES_NOT_EXIST

        local_site = request.local_site

        if local_site:
            local_site_id = local_site.pk
        else:
            local_site_id = None

        if bug_tracker.local_site_id != local_site_id:
            return DOES_NOT_EXIST

        try:
            review_request = ReviewRequest.objects.for_id(
                request.GET['review-request'],
                local_site=local_site)
        except (KeyError, ReviewRequest.DoesNotExist, ValueError):
            return DOES_NOT_EXIST

        if not review_request.is_accessible_by(request.user):
            return self.get_no_access_error(request)

        available = ConfiguredBugTracker.objects.for_review_request(
            review_request,
            user=request.user,
            request=request)

        available_tracker_ids = {
            available_tracker.pk
            for available_tracker in available
        }

        if bug_tracker.pk not in available_tracker_ids:
            return self.get_no_access_error(request)

        service = bug_tracker.service
        assert isinstance(service, BaseHostingService)

        if not service.supports_bug_search:
            return DOES_NOT_EXIST

        limit = min(
            int(request.GET.get('max-results', BUG_SEARCH_DEFAULT_RESULTS)),
            BUG_SEARCH_MAX_RESULTS)

        try:
            results = bug_tracker.search_bugs(request.GET['q'],
                                              limit=limit)
        except Exception as e:
            logger.exception('Error searching bugs on bug tracker '
                             'ID=%s: %s',
                             bug_tracker.pk, e)
            results = []

        return 200, {
            self.list_result_key: list(results),
            'total_results': len(results),
        }


bug_tracker_bugs_resource = BugTrackerBugsResource()
