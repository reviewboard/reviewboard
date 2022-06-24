"""Base class for file attachment comment resources."""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template.defaultfilters import timesince
from djblets.util.decorators import augment_method_from
from djblets.webapi.fields import ResourceFieldType, StringFieldType

from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_comment import BaseCommentResource


class BaseFileAttachmentCommentResource(BaseCommentResource):
    """Base class for file attachment comment resources.

    Provides common fields and functionality for all file attachment comment
    resources. The list of comments cannot be modified from this resource.
    """

    added_in = '1.6'

    model = FileAttachmentComment
    name = 'file_attachment_comment'
    fields = dict({
        'diff_against_file_attachment': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.file_attachment.'
                        'FileAttachmentResource',
            'description': 'The file changes were made against in a diff.',
            'added_in': '2.0',
        },
        'file_attachment': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.file_attachment.'
                        'FileAttachmentResource',
            'description': 'The file the comment was made on.',
        },
        'link_text': {
            'type': StringFieldType,
            'description': 'The text used to describe a link to the file. '
                           'This may differ depending on the comment.',
            'added_in': '1.7.10',
        },
        'review_url': {
            'type': StringFieldType,
            'description': 'The URL to the review UI for the comment on this '
                           'file attachment.',
            'added_in': '1.7.10',
        },
        'thumbnail_html': {
            'type': StringFieldType,
            'description': 'The HTML representing a thumbnail, if any, for '
                           'this comment.',
            'added_in': '1.7.10',
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'
    allowed_methods = ('GET',)

    def get_queryset(self, request, review_request_id=None, *args, **kwargs):
        """Return a queryset for FileAttachmentComment models.

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
            A queryset for FileAttachmentComment models.
        """
        q = Q(review__isnull=False)

        if review_request_id is not None:
            try:
                review_request = resources.review_request.get_object(
                    request, review_request_id=review_request_id,
                    *args, **kwargs)
            except ObjectDoesNotExist:
                raise self.model.DoesNotExist

            q &= (Q(file_attachment__review_request=review_request) |
                  Q(file_attachment__inactive_review_request=review_request))

        return self.model.objects.filter(q)

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
