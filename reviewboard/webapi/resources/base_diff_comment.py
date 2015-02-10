from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.template.defaultfilters import timesince
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields

from reviewboard.reviews.models import Comment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_comment import BaseCommentResource


class BaseDiffCommentResource(BaseCommentResource):
    """Base class for diff comment resources.

    Provides common fields and functionality for all diff comment resources.
    """
    model = Comment
    name = 'diff_comment'
    fields = dict({
        'first_line': {
            'type': int,
            'description': 'The line number that the comment starts at.',
        },
        'num_lines': {
            'type': int,
            'description': 'The number of lines the comment spans.',
        },
        'filediff': {
            'type': 'reviewboard.webapi.resources.filediff.FileDiffResource',
            'description': 'The per-file diff that the comment was made on.',
        },
        'interfilediff': {
            'type': 'reviewboard.webapi.resources.filediff.FileDiffResource',
            'description': "The second per-file diff in an interdiff that "
                           "the comment was made on. This will be ``null`` if "
                           "the comment wasn't made on an interdiff.",
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self, request, review_id=None, is_list=False,
                     *args, **kwargs):
        """Returns a queryset for Comment models.

        This filters the query for comments on the specified review request
        which are either public or owned by the requesting user.

        If the queryset is being used for a list of comment resources,
        then this can be further filtered by passing ``?interdiff-revision=``
        on the URL to match the given interdiff revision, and
        ``?line=`` to match comments on the given line number.
        """
        try:
            review_request = resources.review_request.get_object(
                request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise self.model.DoesNotExist

        q = self.model.objects.filter(
            filediff__diffset__history__review_request=review_request,
            review__isnull=False)

        if is_list:
            if review_id:
                q = q.filter(review=review_id)

            if 'interdiff-revision' in request.GET:
                interdiff_revision = int(request.GET['interdiff-revision'])
                q = q.filter(
                    interfilediff__diffset__revision=interdiff_revision)

            if 'line' in request.GET:
                q = q.filter(first_line=int(request.GET['line']))

        order_by = kwargs.get('order-by', None)

        if order_by:
            q = q.order_by(*[
                field
                for field in order_by.split(',')
                if '__' not in field  # Don't allow joins
            ])

        return q

    def serialize_public_field(self, obj, **kwargs):
        return obj.review.get().public

    def serialize_timesince_field(self, obj, **kwargs):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj, **kwargs):
        return obj.review.get().user

    @webapi_request_fields(
        optional={
            'interdiff-revision': {
                'type': int,
                'description': 'The second revision in an interdiff revision '
                               'range. The comments will be limited to this '
                               'range.',
            },
            'line': {
                'type': int,
                'description': 'The line number that each comment must '
                               'start on.',
            },
            'order-by': {
                'type': six.text_type,
                'description': 'Comma-separated list of fields to order by',
                'added_in': '1.7.10'
            },
        },
        allow_unknown=True
    )
    @augment_method_from(BaseCommentResource)
    def get_list(self, request, review_id=None, *args, **kwargs):
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on the comment."""
        pass
