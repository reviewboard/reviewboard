"""API resource for configured bug trackers.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_docs
from djblets.webapi.fields import (
    BooleanFieldType,
    IntFieldType,
    StringFieldType,
)

from reviewboard.hostingsvcs.base import BaseHostingService
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_login_required

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest
    from djblets.webapi.resources.base import WebAPIResourceHandlerResult


class BugTrackerResource(WebAPIResource):
    """Provides information on configured bug trackers.

    This lists the bug trackers usable by the requesting user. Bug
    trackers are configured through the administration UI.

    Version Added:
        9.0
    """

    added_in = '9.0'

    name = 'bug_tracker'
    model = ConfiguredBugTracker
    uri_object_key = 'bug_tracker_id'
    allowed_methods = ('GET',)

    fields = {
        'display_mode': {
            'type': StringFieldType,
            'description': 'How bugs on this tracker are shown on review '
                           'requests. This is either ``compact`` or '
                           '``detailed``.',
        },
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the bug tracker.',
        },
        'name': {
            'type': StringFieldType,
            'description': 'The display name of the bug tracker. This is '
                           'used as the field label on review requests.',
        },
        'service': {
            'type': StringFieldType,
            'description': 'The ID of the service providing this bug '
                           'tracker.',
        },
        'supports_bug_info': {
            'type': BooleanFieldType,
            'description': 'Whether the bug tracker can provide metadata '
                           'about bugs.',
        },
        'supports_bug_search': {
            'type': BooleanFieldType,
            'description': 'Whether the bug tracker supports searching '
                           'for bugs.',
        },
    }

    @webapi_check_login_required
    def get_queryset(
        self,
        request: HttpRequest,
        local_site_name: (str | None) = None,
        *args,
        **kwargs,
    ) -> QuerySet[ConfiguredBugTracker]:
        """Return a queryset for the resource.

        This only includes enabled bug trackers whose user conditions the
        requesting user passes.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            local_site_name (str, optional):
                The name of the current Local Site, if present.

            *args (tuple):
                Positional arguments parsed from the URL.

            **kwargs (dict):
                Keyword arguments parsed from the URL.

        Returns:
            django.db.models.query.QuerySet:
            The queryset for the bug trackers.
        """
        local_site = self._get_local_site(local_site_name)

        queryset = (
            ConfiguredBugTracker.objects
            .accessible(local_site=local_site)
            .filter(enabled=True)
        )

        usable_pks = [
            bug_tracker.pk
            for bug_tracker in queryset
            if bug_tracker.is_usable_by(request.user, request=request)
        ]

        return ConfiguredBugTracker.objects.filter(pk__in=usable_pks)

    def has_access_permissions(
        self,
        request: HttpRequest,
        bug_tracker: ConfiguredBugTracker,
        *args,
        **kwargs,
    ) -> bool:
        """Return whether the bug tracker is accessible by a user.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker to check.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            bool:
            Whether the bug tracker can be accessed by the user.
        """
        return (bug_tracker.is_accessible_by(request.user) and
                bug_tracker.is_usable_by(request.user, request=request))

    @webapi_docs(
        """
        Retrieves the list of bug trackers usable by the user.

        Disabled bug trackers, and bug trackers whose user conditions the
        requesting user does not pass, are excluded.
        """
    )
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs) -> WebAPIResourceHandlerResult:
        """Handle HTTP GET requests for the list resource.

        Args:
            *args (tuple):
                Positional arguments passed to the parent method.

            **kwargs (dict):
                Keyword arguments passed to the parent method.

        Returns:
            djblets.webapi.resources.base.WebAPIResourceHandlerResult:
            The result of the request.
        """
        ...

    @webapi_docs('Retrieves information on a particular bug tracker.')
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs) -> WebAPIResourceHandlerResult:
        """Handle HTTP GET requests for the item resource.

        Args:
            *args (tuple):
                Positional arguments passed to the parent method.

            **kwargs (dict):
                Keyword arguments passed to the parent method.

        Returns:
            djblets.webapi.resources.base.WebAPIResourceHandlerResult:
            The result of the request.
        """
        ...

    def serialize_service_field(
        self,
        obj: ConfiguredBugTracker,
        **kwargs,
    ) -> str:
        """Serialize the ``service`` field.

        Args:
            obj (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            str:
            The serialized content for the service field.
        """
        return obj.service_name

    def serialize_supports_bug_info_field(
        self,
        obj: ConfiguredBugTracker,
        **kwargs,
    ) -> bool:
        """Serialize the ``supports_bug_info`` field.

        Args:
            obj (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            bool:
            Whether the bug tracker supports bug metadata.
        """
        service = obj.service
        assert isinstance(service, BaseHostingService)

        return service.supports_bug_info

    def serialize_supports_bug_search_field(
        self,
        obj: ConfiguredBugTracker,
        **kwargs,
    ) -> bool:
        """Serialize the ``supports_bug_search`` field.

        Args:
            obj (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            bool:
            Whether the bug tracker supports bug search.
        """
        service = obj.service
        assert isinstance(service, BaseHostingService)

        return service.supports_bug_search


bug_tracker_resource = BugTrackerResource()
