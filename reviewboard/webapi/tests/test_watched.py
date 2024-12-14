"""Unit tests for WatchedResource.

Version Added:
    7.0.3
"""

from __future__ import annotations

import json
from typing import Any

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import watched_mimetype
from reviewboard.webapi.tests.mixins import (
    BasicTestsMetaclass,
    BasicGetItemTestSetupState,
)
from reviewboard.webapi.tests.urls import get_watched_url


class ResourceTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the WatchedResource.

    Version Added:
        7.0.3
    """

    basic_get_returns_json = False
    fixtures = ['test_users']
    sample_api_url = 'users/<username>/watched/'
    resource = resources.watched
    test_http_methods = ('GET',)

    def populate_get_item_test_objects(
        self,
        *,
        setup_state: BasicGetItemTestSetupState,
        **kwargs,
    ) -> None:
        """Populate objects for a GET item test.

        Args:
            setup_state (rbtools.webapi.tests.mixins.
                         BasicGetItemTestSetupState):
                The setup state for the test.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        setup_state['url'] = get_watched_url(
            'doc', local_site_name=setup_state['local_site_name'])
        setup_state['mimetype'] = watched_mimetype
        setup_state['item'] = None

    def compare_item(
        self,
        item_rsp: bytes,
        obj: Any,
    ) -> None:
        """Compare an item's response payload to an object.

        Args:
            item_rsp (dict):
                The item payload from the response.

            obj (object):
                The object to compare to.
        """
        rsp = json.loads(item_rsp.decode())

        self.assertIn('links', rsp)
        self.assertIn('watched_review_groups', rsp['links'])
        self.assertIn('watched_review_requests', rsp['links'])
