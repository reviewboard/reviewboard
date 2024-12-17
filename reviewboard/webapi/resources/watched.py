"""Resource that links to watched items resources for a user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (
    webapi_check_local_site,
    webapi_check_login_required,
)
from reviewboard.webapi.resources import resources

if TYPE_CHECKING:
    from django.http import HttpRequest

    from djblets.webapi.resources.base import WebAPIResourceHandlerResult


class WatchedResource(WebAPIResource):
    """Resource that links to watched items resources for a user.

    This is more of a linking resource rather than a data resource, much like
    the root resource is. The sole purpose of this resource is for easy
    navigation to the more specific Watched Items resources.
    """

    name = 'watched'
    singleton = True

    list_child_resources = [
        resources.watched_review_group,
        resources.watched_review_request,
    ]

    @webapi_check_login_required
    @webapi_check_local_site
    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> WebAPIResourceHandlerResult:
        """Retrieves the list of Watched Items resources.

        Unlike most resources, the result of this resource is just a list of
        links, rather than any kind of data. It exists in order to index the
        more specific Watched Review Groups and Watched Review Requests
        resources.
        """
        return 200, {
            'links': self.get_links(self.list_child_resources,
                                    request=request,
                                    *args, **kwargs),
        }


watched_resource = WatchedResource()
