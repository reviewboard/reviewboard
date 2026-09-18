"""Unit tests for the BugTrackerBugsResource.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

import kgb
from djblets.webapi.errors import (
    DOES_NOT_EXIST,
    INVALID_FORM_DATA,
    PERMISSION_DENIED,
)
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.hostingsvcs.splat import Splat
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import bug_tracker_bugs_list_mimetype
from reviewboard.webapi.tests.mixins import (
    BasicGetItemListTestSetupState,
    BasicTestsMetaclass,
)
from reviewboard.webapi.tests.urls import get_bug_tracker_bugs_list_url

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.contrib.auth.models import User
    from typelets.json import JSONDict

    from reviewboard.hostingsvcs.base.bug_tracker import BugSearchResult
    from reviewboard.reviews.models import ReviewRequest
    from reviewboard.site.models import LocalSite


class ResourceListTests(kgb.SpyAgency,
                        BaseWebAPITestCase,
                        metaclass=BasicTestsMetaclass):
    """Unit tests for the BugTrackerBugsResource list APIs."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'bug-trackers/<id>/bugs/'
    resource = resources.bug_tracker_bugs

    def compare_item(
        self,
        item_rsp: JSONDict,
        result: BugSearchResult,
    ) -> None:
        """Compare an API response to a bug search result.

        Args:
            item_rsp (dict):
                The API response.

            result (reviewboard.hostingsvcs.base.bug_tracker.
                    BugSearchResult):
                The search result to compare to.
        """
        self.assertEqual(item_rsp, result)

    def setup_http_not_allowed_item_test(
        self,
        user: User,
    ) -> str:
        """Set up the HTTP not allowed test for item access.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to use for accessing the resource.
        """
        review_request, bug_tracker = self._create_search_objects()

        return self._build_search_url(review_request, bug_tracker)

    def setup_http_not_allowed_list_test(
        self,
        user: User,
    ) -> str:
        """Set up the HTTP not allowed test for list access.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to use for accessing the resource.
        """
        review_request, bug_tracker = self._create_search_objects()

        return self._build_search_url(review_request, bug_tracker)

    #
    # HTTP GET tests
    #

    def populate_get_list_test_objects(
        self,
        *,
        setup_state: BasicGetItemListTestSetupState,
        populate_list_items: bool,
        **kwargs,
    ) -> None:
        """Populate objects for a GET list test.

        Args:
            setup_state (reviewboard.webapi.tests.mixins.
                         BasicGetItemListTestSetupState):
                The setup state for the test.

            populate_list_items (bool):
                Whether to populate items for the results.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        review_request, bug_tracker = self._create_search_objects(
            local_site=setup_state['local_site'])

        results: list[BugSearchResult] = []

        if populate_list_items:
            results.append({
                'bug_id': '123',
                'summary': 'Crash on startup',
            })

        self._enable_bug_search(results)

        setup_state.update({
            'items': results,
            'mimetype': bug_tracker_bugs_list_mimetype,
            'url': self._build_search_url(
                review_request,
                bug_tracker,
                local_site_name=setup_state['local_site_name']),
        })

    @webapi_test_template
    def test_get_without_search_support(self) -> None:
        """Testing the GET <URL> API with a bug tracker that does not
        support searching
        """
        review_request, bug_tracker = self._create_search_objects()

        rsp = self.api_get(self._build_search_url(review_request,
                                                  bug_tracker),
                           expected_status=404)
        assert rsp is not None

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': DOES_NOT_EXIST.code,
                'msg': DOES_NOT_EXIST.msg,
                'type': DOES_NOT_EXIST.error_type,
            },
        })

    @webapi_test_template
    def test_get_without_review_request(self) -> None:
        """Testing the GET <URL> API without a review request"""
        bug_tracker = self.create_bug_tracker(service_name='splat')
        self._enable_bug_search([])

        rsp = self.api_get(
            get_bug_tracker_bugs_list_url(bug_tracker),
            {
                'q': 'crash',
            },
            expected_status=400)
        assert rsp is not None

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
                'type': INVALID_FORM_DATA.error_type,
            },
            'fields': {
                'review-request': ['This field is required'],
            },
        })

    @webapi_test_template
    def test_get_with_out_of_scope_tracker(self) -> None:
        """Testing the GET <URL> API with a bug tracker not applying to the
        review request
        """
        review_request, bug_tracker = self._create_search_objects(
            apply_to=ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS)
        self._enable_bug_search([])

        rsp = self.api_get(self._build_search_url(review_request,
                                                  bug_tracker),
                           expected_status=403)
        assert rsp is not None

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': PERMISSION_DENIED.code,
                'msg': PERMISSION_DENIED.msg,
                'type': PERMISSION_DENIED.error_type,
            },
        })

    @webapi_test_template
    def test_get_with_failing_user_conditions(self) -> None:
        """Testing the GET <URL> API with a user failing the bug tracker's
        conditions
        """
        review_request, bug_tracker = self._create_search_objects(
            limit_to_groups=[self.create_review_group()])
        self._enable_bug_search([])

        rsp = self.api_get(self._build_search_url(review_request,
                                                  bug_tracker),
                           expected_status=403)
        assert rsp is not None

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': PERMISSION_DENIED.code,
                'msg': PERMISSION_DENIED.msg,
                'type': PERMISSION_DENIED.error_type,
            },
        })

    def _create_search_objects(
        self,
        *,
        local_site: (LocalSite | None) = None,
        **tracker_kwargs,
    ) -> tuple[ReviewRequest, ConfiguredBugTracker]:
        """Create a review request and a bug tracker to search.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site to create the objects on.

            **tracker_kwargs (dict):
                Additional arguments for the bug tracker.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (reviewboard.reviews.models.ReviewRequest):
                    The review request.

                1 (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                    The bug tracker.
        """
        repository = self.create_repository(local_site=local_site)
        review_request = self.create_review_request(
            repository=repository,
            local_site=local_site,
            publish=True)
        bug_tracker = self.create_bug_tracker(service_name='splat',
                                              local_site=local_site,
                                              **tracker_kwargs)

        return review_request, bug_tracker

    def _build_search_url(
        self,
        review_request: ReviewRequest,
        bug_tracker: ConfiguredBugTracker,
        *,
        query: str = 'crash',
        local_site_name: (str | None) = None,
    ) -> str:
        """Return a search URL with its query string.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request the bugs would be linked to.

            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker to search.

            query (str, optional):
                The search query.

            local_site_name (str, optional):
                The name of the Local Site, if any.

        Returns:
            str:
            The URL.
        """
        url = get_bug_tracker_bugs_list_url(bug_tracker, local_site_name)
        params = urlencode({
            'q': query,
            'review-request': review_request.display_id,
        })

        return f'{url}?{params}'

    def _enable_bug_search(
        self,
        results: Sequence[BugSearchResult],
    ) -> None:
        """Enable bug search on the Splat service for this test.

        Args:
            results (list of reviewboard.hostingsvcs.base.bug_tracker.
                     BugSearchResult):
                The results the search should return.
        """
        Splat.supports_bug_search = True
        self.addCleanup(lambda: delattr(Splat, 'supports_bug_search'))

        self.spy_on(Splat.search_bugs,
                    owner=Splat,
                    op=kgb.SpyOpReturn(results))
