from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.webapi.decorators import webapi_login_required
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources


class ReviewDraftResource(WebAPIResource):
    """A redirecting resource that points to the current draft review."""
    name = 'review_draft'
    singleton = True
    uri_name = 'draft'

    @webapi_check_local_site
    @webapi_login_required
    def get(self, request, *args, **kwargs):
        """Returns an HTTP redirect to the current draft review."""
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            review = review_request.get_pending_review(request.user)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review:
            return DOES_NOT_EXIST

        return 302, {}, {
            'Location': self._build_redirect_with_args(
                request,
                resources.review.get_href(review, request, *args, **kwargs)),
        }


review_draft_resource = ReviewDraftResource()
