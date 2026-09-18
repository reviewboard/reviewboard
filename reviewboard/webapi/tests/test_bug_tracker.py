"""Unit tests for the BugTrackerResource.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.webapi.errors import DOES_NOT_EXIST
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.hostingsvcs.base import BaseHostingService
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    bug_tracker_item_mimetype,
    bug_tracker_list_mimetype,
)
from reviewboard.webapi.tests.mixins import (
    BasicGetItemListTestSetupState,
    BasicGetItemTestSetupState,
    BasicTestsMetaclass,
)
from reviewboard.webapi.tests.urls import (
    get_bug_tracker_item_url,
    get_bug_tracker_list_url,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from typelets.json import JSONDict


def _get_item_payload(
    self: BaseWebAPITestCase,
    bug_tracker: ConfiguredBugTracker,
) -> JSONDict:
    """Return the expected API payload for a bug tracker.

    Version Added:
        9.0

    Args:
        self (reviewboard.webapi.tests.base.BaseWebAPITestCase):
            The test case.

        bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
            The bug tracker to build the payload for.

    Returns:
        dict:
        The expected payload.
    """
    local_site = bug_tracker.local_site

    if local_site is not None:
        local_site_name = local_site.name
    else:
        local_site_name = None

    item_url = get_bug_tracker_item_url(bug_tracker, local_site_name)
    service = bug_tracker.service
    assert isinstance(service, BaseHostingService)

    return {
        'display_mode': bug_tracker.display_mode,
        'id': bug_tracker.pk,
        'links': {
            'self': {
                'href': f'{self.base_url}{item_url}',
                'method': 'GET',
            },
        },
        'name': bug_tracker.name,
        'service': bug_tracker.service_name,
        'supports_bug_info': service.supports_bug_info,
        'supports_bug_search': service.supports_bug_search,
    }


def _compare_item(
    self: BaseWebAPITestCase,
    item_rsp: JSONDict,
    bug_tracker: ConfiguredBugTracker,
) -> None:
    """Compare an API response to a bug tracker.

    Version Added:
        9.0

    Args:
        self (reviewboard.webapi.tests.base.BaseWebAPITestCase):
            The test case.

        item_rsp (dict):
            The API response.

        bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
            The bug tracker to compare to.
    """
    self.assertEqual(item_rsp, _get_item_payload(self, bug_tracker))


class ResourceListTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the BugTrackerResource list APIs.

    Version Added:
        9.0
    """

    compare_item = _compare_item
    fixtures = ['test_users']
    resource = resources.bug_tracker
    sample_api_url = 'bug-trackers/'

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
        return get_bug_tracker_list_url()

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
        return get_bug_tracker_list_url()

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
        items: list[ConfiguredBugTracker] = []

        if populate_list_items:
            items.append(self.create_bug_tracker(
                local_site=setup_state['local_site']))

        setup_state.update({
            'items': items,
            'mimetype': bug_tracker_list_mimetype,
            'url': get_bug_tracker_list_url(setup_state['local_site_name']),
        })

    @webapi_test_template
    def test_get_excludes_disabled_and_sentinel(self) -> None:
        """Testing the GET <URL> API excludes disabled bug trackers and the
        sentinel bug tracker
        """
        bug_tracker = self.create_bug_tracker()
        self.create_bug_tracker(name='Disabled Tracker', enabled=False)
        ConfiguredBugTracker.objects.get_sentinel()
        url = get_bug_tracker_list_url()

        rsp = self.api_get(url,
                           expected_mimetype=bug_tracker_list_mimetype)

        self.assertEqual(rsp, {
            'bug_trackers': [
                _get_item_payload(self, bug_tracker),
            ],
            'links': {
                'self': {
                    'href': f'{self.base_url}{url}',
                    'method': 'GET',
                },
            },
            'stat': 'ok',
            'total_results': 1,
        })

    @webapi_test_template
    def test_get_with_user_conditions(self) -> None:
        """Testing the GET <URL> API excludes bug trackers whose user
        conditions the user does not pass
        """
        group = self.create_review_group()
        bug_tracker = self.create_bug_tracker(limit_to_groups=[group])
        url = get_bug_tracker_list_url()

        rsp = self.api_get(url,
                           expected_mimetype=bug_tracker_list_mimetype)

        self.assertEqual(rsp, {
            'bug_trackers': [],
            'links': {
                'self': {
                    'href': f'{self.base_url}{url}',
                    'method': 'GET',
                },
            },
            'stat': 'ok',
            'total_results': 0,
        })

        # A user in the group sees the tracker.
        assert self.user is not None
        group.users.add(self.user)

        rsp = self.api_get(url,
                           expected_mimetype=bug_tracker_list_mimetype)

        self.assertEqual(rsp, {
            'bug_trackers': [
                _get_item_payload(self, bug_tracker),
            ],
            'links': {
                'self': {
                    'href': f'{self.base_url}{url}',
                    'method': 'GET',
                },
            },
            'stat': 'ok',
            'total_results': 1,
        })


class ResourceItemTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the BugTrackerResource item APIs.

    Version Added:
        9.0
    """

    compare_item = _compare_item
    fixtures = ['test_users']
    resource = resources.bug_tracker
    sample_api_url = 'bug-trackers/<id>/'

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
        return get_bug_tracker_item_url(self.create_bug_tracker())

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
        return get_bug_tracker_item_url(self.create_bug_tracker())

    #
    # HTTP GET tests
    #

    def populate_get_item_test_objects(
        self,
        *,
        setup_state: BasicGetItemTestSetupState,
        **kwargs,
    ) -> None:
        """Populate objects for a GET item test.

        Args:
            setup_state (reviewboard.webapi.tests.mixins.
                         BasicGetItemTestSetupState):
                The setup state for the test.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        bug_tracker = self.create_bug_tracker(
            local_site=setup_state['local_site'])

        setup_state.update({
            'item': bug_tracker,
            'mimetype': bug_tracker_item_mimetype,
            'url': get_bug_tracker_item_url(bug_tracker,
                                            setup_state['local_site_name']),
        })

    @webapi_test_template
    def test_get_with_user_conditions(self) -> None:
        """Testing the GET <URL> API with a bug tracker whose user
        conditions the user does not pass
        """
        group = self.create_review_group()
        bug_tracker = self.create_bug_tracker(limit_to_groups=[group])

        url = get_bug_tracker_item_url(bug_tracker)

        rsp = self.api_get(url, expected_status=404)

        self.assertEqual(rsp, {
            'err': {
                'code': DOES_NOT_EXIST.code,
                'msg': DOES_NOT_EXIST.msg,
                'type': DOES_NOT_EXIST.error_type,
            },
            'stat': 'fail',
        })

        # A user in the group sees the tracker.
        assert self.user is not None
        group.users.add(self.user)

        rsp = self.api_get(url, expected_mimetype=bug_tracker_item_mimetype)

        self.assertEqual(rsp, {
            'bug_tracker': _get_item_payload(self, bug_tracker),
            'stat': 'ok',
        })
