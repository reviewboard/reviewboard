"""Base class for diff comment resources."""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template.defaultfilters import timesince
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.fields import (IntFieldType,
                                   ResourceFieldType,
                                   StringFieldType)

from reviewboard.reviews.models import Comment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_comment import BaseCommentResource


class BaseDiffCommentResource(BaseCommentResource):
    """Base class for diff comment resources.

    Provides common fields and functionality for all diff comment resources.
    The list of comments cannot be modified from this resource.
    """

    model = Comment
    name = 'diff_comment'
    fields = dict({
        'first_line': {
            'type': IntFieldType,
            'description': 'The line number that the comment starts at.',
        },
        'num_lines': {
            'type': IntFieldType,
            'description': 'The number of lines the comment spans.',
        },
        'filediff': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.filediff.'
                        'FileDiffResource',
            'description': 'The per-file diff that the comment was made on.',
        },
        'interfilediff': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.filediff.'
                        'FileDiffResource',
            'description': "The second per-file diff in an interdiff that "
                           "the comment was made on. This will be ``null`` if "
                           "the comment wasn't made on an interdiff.",
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self,
                     request,
                     review_request_id=None,
                     review_id=None,
                     is_list=False,
                     *args, **kwargs):
        """Return a queryset for Comment models.

        If the queryset is being used for a list of comment resources,
        then this can be further filtered by passing ``?interdiff-revision=``
        on the URL to match the given interdiff revision, and
        ``?line=`` to match comments on the given line number.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            review_request_id (int, optional):
                The review request ID used to filter the results. If set,
                only comments from the given review request that are public
                or owned by the requesting user will be included.

            review_id (int, optional):
                The review ID used to filter the results. If set,
                only comments from the given review that are public
                or owned by the requesting user will be included.

            is_list (bool, optional):
                Whether the incoming HTTP request is for list resources.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for Comment models.
        """
        q = Q()

        if review_request_id is not None:
            try:
                review_request = resources.review_request.get_object(
                    request, review_request_id=review_request_id,
                    *args, **kwargs)
            except ObjectDoesNotExist:
                raise self.model.DoesNotExist

            q &= Q(filediff__diffset__history__review_request=review_request,
                   review__isnull=False)

        if is_list:
            if review_id:
                q &= Q(review=review_id)

            if 'interdiff-revision' in request.GET:
                interdiff_revision = int(request.GET['interdiff-revision'])
                q &= Q(interfilediff__diffset__revision=interdiff_revision)

            if 'line' in request.GET:
                q &= Q(first_line=int(request.GET['line']))

        queryset = self.model.objects.filter(q)
        order_by = kwargs.get('order-by', None)

        if order_by:
            queryset = queryset.order_by(*[
                field
                for field in order_by.split(',')
                if '__' not in field  # Don't allow joins
            ])

        return queryset

    def serialize_public_field(self, obj, **kwargs):
        return obj.review.get().public

    def serialize_timesince_field(self, obj, **kwargs):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj, **kwargs):
        return obj.review.get().user

    @webapi_request_fields(
        optional={
            'interdiff-revision': {
                'type': IntFieldType,
                'description': 'The second revision in an interdiff revision '
                               'range. The comments will be limited to this '
                               'range.',
            },
            'line': {
                'type': IntFieldType,
                'description': 'The line number that each comment must '
                               'start on.',
            },
            'order-by': {
                'type': StringFieldType,
                'description': 'Comma-separated list of fields to order by.',
                'added_in': '1.7.10',
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
