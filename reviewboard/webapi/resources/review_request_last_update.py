from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseNotModified
from django.utils import six
from django.utils.translation import ugettext as _
from djblets.util.http import get_modified_since, http_date
from djblets.webapi.errors import DOES_NOT_EXIST
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import Review, ReviewRequest
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.resources import resources


class ReviewRequestLastUpdateResource(WebAPIResource):
    """Provides information on the last update made to a review request.

    Clients can periodically poll this to see if any new updates have been
    made.
    """
    name = 'last_update'
    policy_id = 'review_request_last_update'
    singleton = True
    allowed_methods = ('GET',)

    fields = {
        'summary': {
            'type': six.text_type,
            'description': 'A short summary of the update. This should be one '
                           'of "Review request updated", "Diff updated", '
                           '"New reply" or "New review".',
        },
        'timestamp': {
            'type': six.text_type,
            'description': 'The timestamp of this most recent update '
                           '(YYYY-MM-DD HH:MM:SS format).',
        },
        'type': {
            'type': ('review-request', 'diff', 'reply', 'review'),
            'description': "The type of the last update. ``review-request`` "
                           "means the last update was an update of the "
                           "review request's information. ``diff`` means a "
                           "new diff was uploaded. ``reply`` means a reply "
                           "was made to an existing review. ``review`` means "
                           "a new review was posted.",
        },
        'user': {
            'type': six.text_type,
            'description': 'The user who made the last update.',
        },
    }

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the last update made to the review request.

        This shows the type of update that was made, the user who made the
        update, and when the update was made. Clients can use this to inform
        the user that the review request was updated, or automatically update
        it in the background.

        This does not take into account changes to a draft review request, as
        that's generally not update information that the owner of the draft is
        interested in. Only public updates are represented.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review_request.has_access_permissions(request,
                                                               review_request):
            return self._no_access_error(request.user)

        timestamp, updated_object = review_request.get_last_activity()

        if get_modified_since(request, timestamp):
            return HttpResponseNotModified()

        user = None
        summary = None
        update_type = None

        if isinstance(updated_object, ReviewRequest):
            user = updated_object.submitter

            if updated_object.status == ReviewRequest.SUBMITTED:
                summary = _("Review request submitted")
            elif updated_object.status == ReviewRequest.DISCARDED:
                summary = _("Review request discarded")
            else:
                summary = _("Review request updated")

            update_type = "review-request"
        elif isinstance(updated_object, DiffSet):
            summary = _("Diff updated")
            update_type = "diff"
        elif isinstance(updated_object, Review):
            user = updated_object.user

            if updated_object.is_reply():
                summary = _("New reply")
                update_type = "reply"
            else:
                summary = _("New review")
                update_type = "review"
        else:
            # Should never be able to happen. The object will always at least
            # be a ReviewRequest.
            assert False

        return 200, {
            self.item_result_key: {
                'timestamp': timestamp,
                'user': user,
                'summary': summary,
                'type': update_type,
            }
        }, {
            'Last-Modified': http_date(timestamp)
        }


review_request_last_update_resource = ReviewRequestLastUpdateResource()
