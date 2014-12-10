from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_watched_object import \
    BaseWatchedObjectResource


class WatchedReviewGroupResource(BaseWatchedObjectResource):
    """Lists and manipulates entries for review groups watched by the user.

    These are groups that the user has starred in their Dashboard.
    This resource can be used for listing existing review groups and adding
    new review groups to watch.

    Each item in the resource is an association between the user and the
    review group. The entries in the list are not the review groups themselves,
    but rather an entry that represents this association by listing the
    association's ID (which can be used for removing the association) and
    linking to the review group.
    """
    name = 'watched_review_group'
    uri_name = 'review-groups'
    profile_field = 'starred_groups'
    star_function = 'star_review_group'
    unstar_function = 'unstar_review_group'

    @property
    def watched_resource(self):
        """Return the watched resource.

        This is implemented as a property in order to work around
        a circular reference issue.
        """
        return resources.review_group

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get(self, *args, **kwargs):
        """Returned an :http:`302` pointing to the review group being
        watched.

        Rather than returning a body with the entry, performing an HTTP GET
        on this resource will redirect the client to the actual review group
        being watched.

        Clients must properly handle :http:`302` and expect this redirect
        to happen.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of watched review groups.

        Each entry in the list consists of a numeric ID that represents the
        entry for the watched review group. This is not necessarily the ID
        of the review group itself. It's used for looking up the resource
        of the watched item so that it can be removed.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def create(self, *args, **kwargs):
        """Marks a review group as being watched.

        The ID of the review group must be passed as ``object_id``, and will
        store that review group in the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def delete(self, *args, **kwargs):
        """Deletes a watched review group entry.

        This is the same effect as unstarring a review group. It does
        not actually delete the review group, just the entry in the list.
        """
        pass


watched_review_group_resource = WatchedReviewGroupResource()
