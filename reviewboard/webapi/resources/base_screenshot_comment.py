from __future__ import unicode_literals

from django.db.models import Q
from django.template.defaultfilters import timesince
from django.utils import six
from djblets.util.decorators import augment_method_from

from reviewboard.reviews.models import ScreenshotComment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_comment import BaseCommentResource


class BaseScreenshotCommentResource(BaseCommentResource):
    """A base resource for screenshot comments."""
    model = ScreenshotComment
    name = 'screenshot_comment'

    fields = dict({
        'screenshot': {
            'type': 'reviewboard.webapi.resources.screenshot.'
                    'ScreenshotResource',
            'description': 'The screenshot the comment was made on.',
        },
        'x': {
            'type': int,
            'description': 'The X location of the comment region on the '
                           'screenshot.',
        },
        'y': {
            'type': int,
            'description': 'The Y location of the comment region on the '
                           'screenshot.',
        },
        'w': {
            'type': int,
            'description': 'The width of the comment region on the '
                           'screenshot.',
        },
        'h': {
            'type': int,
            'description': 'The height of the comment region on the '
                           'screenshot.',
        },
        'thumbnail_url': {
            'type': six.text_type,
            'description': 'The URL to an image showing what was commented '
                           'on.',
            'added_in': '1.7.10',
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self, request, *args, **kwargs):
        review_request = \
            resources.review_request.get_object(request, *args, **kwargs)
        return self.model.objects.filter(
            Q(screenshot__review_request=review_request) |
            Q(screenshot__inactive_review_request=review_request),
            review__isnull=False)

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
