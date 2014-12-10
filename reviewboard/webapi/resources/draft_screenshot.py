from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_login_required
from djblets.webapi.responses import WebAPIResponsePaginated

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_screenshot import \
    BaseScreenshotResource


class DraftScreenshotResource(BaseScreenshotResource):
    """Provides information on new screenshots being added to a draft of
    a review request.

    These are screenshots that will be shown once the pending review request
    draft is published.
    """
    name = 'draft_screenshot'
    uri_name = 'screenshots'
    model_parent_key = 'drafts'
    allowed_methods = ('GET', 'DELETE', 'POST', 'PUT',)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        try:
            draft = resources.review_request_draft.get_object(
                request, review_request_id=review_request_id, *args, **kwargs)

            inactive_ids = \
                draft.inactive_screenshots.values_list('pk', flat=True)

            q = Q(review_request=review_request_id) | Q(drafts=draft)
            query = self.model.objects.filter(q)
            query = query.exclude(pk__in=inactive_ids)
            return query
        except ObjectDoesNotExist:
            return self.model.objects.none()

    def serialize_caption_field(self, obj, **kwargs):
        return obj.draft_caption or obj.caption

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes the screenshot from the draft.

        This will remove the screenshot from the draft review request.
        This cannot be undone.

        This can be used to remove old screenshots that were previously
        shown, as well as newly added screenshots that were part of the
        draft.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of draft screenshots.

        Each screenshot in this list is an uploaded screenshot that will
        be shown in the final review request. These may include newly
        uploaded screenshots or screenshots that were already part of the
        existing review request. In the latter case, existing screenshots
        are shown so that their captions can be added.
        """
        pass

    def _get_list_impl(self, request, *args, **kwargs):
        """Returns the list of screenshots on this draft.

        This is a specialized version of the standard get_list function
        that uses this resource to serialize the children, in order to
        guarantee that we'll be able to identify them as screenshots that are
        part of the draft.
        """
        return WebAPIResponsePaginated(
            request,
            queryset=self._get_queryset(request, is_list=True,
                                        *args, **kwargs),
            results_key=self.list_result_key,
            serialize_object_func=lambda obj: self.serialize_object(
                obj, request=request, *args, **kwargs),
            extra_data={
                'links': self.get_links(self.list_child_resources,
                                        request=request, *args, **kwargs),
            },
            **self.build_response_args(request))


draft_screenshot_resource = DraftScreenshotResource()
