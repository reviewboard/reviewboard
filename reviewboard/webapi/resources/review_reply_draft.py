from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.webapi.decorators import webapi_login_required
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources


class ReviewReplyDraftResource(WebAPIResource):
    """A redirecting resource that points to the current draft reply.

    This works as a convenience to access the current draft reply, so that
    clients can discover the proper location.
    """
    name = 'reply_draft'
    policy_id = 'review_reply_draft'
    singleton = True
    uri_name = 'draft'

    @webapi_check_local_site
    @webapi_login_required
    def get(self, request, *args, **kwargs):
        """Returns the location of the current draft reply.

        If the draft reply exists, this will return :http:`302` with
        a ``Location`` header pointing to the URL of the draft. Any
        operations on the draft can be done at that URL.

        If the draft reply does not exist, this will return a Does Not
        Exist error.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
            reply = review.get_pending_reply(request.user)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not reply:
            return DOES_NOT_EXIST

        return 302, {}, {
            'Location': self._build_redirect_with_args(
                request,
                resources.review_reply.get_href(reply, request, *args,
                                                **kwargs)),
        }


review_reply_draft_resource = ReviewReplyDraftResource()
