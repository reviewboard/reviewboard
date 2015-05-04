from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources.base_archived_object import \
    BaseArchivedObjectResource


class MutedReviewRequestResource(BaseArchivedObjectResource):
    """List and manipulate entries for review requests muted by the user.

    These are requests that the user has muted. This resource can be used
    for adding and removing muted review requests.

    Each item in the resource is an association between the user and the
    review request.
    """
    name = 'muted_review_request'
    visibility = ReviewRequestVisit.MUTED

    @webapi_check_local_site
    @augment_method_from(BaseArchivedObjectResource)
    def create(self, *args, **kwargs):
        """Mark a review request as muted.

        The ID of the review reqiest must be passed as ``object_id``, and will
        store that review request in the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseArchivedObjectResource)
    def delete(self, *args, **kwargs):
        """Delete a muted review request entry.

        This is the same effect as unmuting a review request. It does
        not actually delete the review request, just the entry in the list.
        """
        pass

muted_review_request_resource = MutedReviewRequestResource()
