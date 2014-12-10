from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_watched_object import \
    BaseWatchedObjectResource


class WatchedReviewRequestResource(BaseWatchedObjectResource):
    """Lists and manipulates entries for review requests watched by the user.

    These are requests that the user has starred in their Dashboard.
    This resource can be used for listing existing review requests and adding
    new review requests to watch.

    Each item in the resource is an association between the user and the
    review request. The entries in the list are not the review requests
    themselves, but rather an entry that represents this association by
    listing the association's ID (which can be used for removing the
    association) and linking to the review request.
    """
    name = 'watched_review_request'
    uri_name = 'review-requests'
    profile_field = 'starred_review_requests'
    star_function = 'star_review_request'
    unstar_function = 'unstar_review_request'

    @property
    def watched_resource(self):
        """Return the watched resource.

        This is implemented as a property in order to work around
        a circular reference issue.
        """
        return resources.review_request

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get(self, *args, **kwargs):
        """Returned an :http:`302` pointing to the review request being
        watched.

        Rather than returning a body with the entry, performing an HTTP GET
        on this resource will redirect the client to the actual review request
        being watched.

        Clients must properly handle :http:`302` and expect this redirect
        to happen.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of watched review requests.

        Each entry in the list consists of a numeric ID that represents the
        entry for the watched review request. This is not necessarily the ID
        of the review request itself. It's used for looking up the resource
        of the watched item so that it can be removed.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def create(self, *args, **kwargs):
        """Marks a review request as being watched.

        The ID of the review group must be passed as ``object_id``, and will
        store that review group in the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def delete(self, *args, **kwargs):
        """Deletes a watched review request entry.

        This is the same effect as unstarring a review request. It does
        not actually delete the review request, just the entry in the list.
        """
        pass

    def serialize_object(self, obj, *args, **kwargs):
        return {
            'id': obj.display_id,
            self.item_result_key: obj,
        }

    def get_watched_object(self, queryset, obj_id, local_site_name=None,
                           *args, **kwargs):
        if local_site_name:
            return queryset.get(local_id=obj_id)
        else:
            return queryset.get(pk=obj_id)


watched_review_request_resource = WatchedReviewRequestResource()
