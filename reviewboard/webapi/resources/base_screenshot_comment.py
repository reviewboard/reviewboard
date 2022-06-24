"""Base class for screenshot comment resources."""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template.defaultfilters import timesince
from djblets.util.decorators import augment_method_from
from djblets.webapi.fields import (IntFieldType,
                                   ResourceFieldType,
                                   StringFieldType)

from reviewboard.reviews.models import ScreenshotComment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_comment import BaseCommentResource


class BaseScreenshotCommentResource(BaseCommentResource):
    """Base class for screenshot comment resources.

    Provides common fields and functionality for all screenshot comment
    resources. The list of comments cannot be modified from this resource.
    """

    model = ScreenshotComment
    name = 'screenshot_comment'

    fields = dict({
        'screenshot': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.screenshot.'
                        'ScreenshotResource',
            'description': 'The screenshot the comment was made on.',
        },
        'x': {
            'type': IntFieldType,
            'description': 'The X location of the comment region on the '
                           'screenshot.',
        },
        'y': {
            'type': IntFieldType,
            'description': 'The Y location of the comment region on the '
                           'screenshot.',
        },
        'w': {
            'type': IntFieldType,
            'description': 'The width of the comment region on the '
                           'screenshot.',
        },
        'h': {
            'type': IntFieldType,
            'description': 'The height of the comment region on the '
                           'screenshot.',
        },
        'thumbnail_url': {
            'type': StringFieldType,
            'description': 'The URL to an image showing what was commented '
                           'on.',
            'added_in': '1.7.10',
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self, request, review_request_id=None, *args, **kwargs):
        """Return a queryset for ScreenshotComment models.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            review_request_id (int, optional):
                The review request ID used to filter the results. If set,
                only comments from the given review request that are public
                or owned by the requesting user will be included.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for ScreenshotComment models.
        """
        q = Q(review__isnull=False)

        if review_request_id is not None:
            try:
                review_request = resources.review_request.get_object(
                    request, review_request_id=review_request_id,
                    *args, **kwargs)
            except ObjectDoesNotExist:
                raise self.model.DoesNotExist

            q &= (Q(screenshot__review_request=review_request) |
                  Q(screenshot__inactive_review_request=review_request))

        return self.model.objects.filter(q)

    def serialize_public_field(self, obj, **kwargs):
        return obj.review.get().public

    def serialize_timesince_field(self, obj, **kwargs):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj, **kwargs):
        return obj.review.get().user

    def serialize_thumbnail_url_field(self, obj, **kwargs):
        return obj.get_image_url()

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on the comment.

        This contains the comment text, time the comment was made,
        and the location of the comment region on the screenshot, amongst
        other information. It can be used to reconstruct the exact
        position of the comment for use as an overlay on the screenshot.
        """
        pass
