from __future__ import unicode_literals

from django.db.models import Q
from django.template.defaultfilters import timesince
from django.utils import six
from djblets.util.decorators import augment_method_from

from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_comment import BaseCommentResource


class BaseFileAttachmentCommentResource(BaseCommentResource):
    """A base resource for file comments."""
    added_in = '1.6'

    model = FileAttachmentComment
    name = 'file_attachment_comment'
    fields = dict({
        'diff_against_file_attachment': {
            'type': 'reviewboard.webapi.resources.file_attachment.'
                    'FileAttachmentResource',
            'description': 'The file changes were made against in a diff.',
            'added_in': '2.0',
        },
        'file_attachment': {
            'type': 'reviewboard.webapi.resources.file_attachment.'
                    'FileAttachmentResource',
            'description': 'The file the comment was made on.',
        },
        'link_text': {
            'type': six.text_type,
            'description': 'The text used to describe a link to the file. '
                           'This may differ depending on the comment.',
            'added_in': '1.7.10',
        },
        'review_url': {
            'type': six.text_type,
            'description': 'The URL to the review UI for the comment on this '
                           'file attachment.',
            'added_in': '1.7.10',
        },
        'thumbnail_html': {
            'type': six.text_type,
            'description': 'The HTML representing a thumbnail, if any, for '
                           'this comment.',
            'added_in': '1.7.10',
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'
    allowed_methods = ('GET',)

    def get_queryset(self, request, *args, **kwargs):
        review_request = \
            resources.review_request.get_object(request, *args, **kwargs)

        return self.model.objects.filter(
            (Q(file_attachment__review_request=review_request) |
             Q(file_attachment__inactive_review_request=review_request)) &
            Q(review__isnull=False))

    def serialize_link_text_field(self, obj, **kwargs):
        return obj.get_link_text()

    def serialize_public_field(self, obj, **kwargs):
        return obj.review.get().public

    def serialize_review_url_field(self, obj, **kwargs):
        return obj.get_review_url()

    def serialize_thumbnail_html_field(self, obj, **kwargs):
        return obj.thumbnail

    def serialize_timesince_field(self, obj, **kwargs):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj, **kwargs):
        return obj.review.get().user

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on the comment.

        This contains the comment text, time the comment was made,
        and the file the comment was made on, amongst other information.
        """
        pass
