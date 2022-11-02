"""Root diff comments API resource.

Version Added:
    5.0
"""

from django.db.models import Q
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.fields import (BooleanFieldType,
                                   DateTimeFieldType,
                                   IntFieldType,
                                   StringFieldType)

from reviewboard.accounts.models import User
from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.reviews.models import Comment
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources.base_diff_comment import \
    BaseDiffCommentResource


class RootDiffCommentResource(BaseDiffCommentResource):
    """Provide information on diff comments.

    This is a top level endpoint that allows you to list and query all
    diff comments in the system, across different review requests.

    Version Added:
        5.0
    """

    added_in = '5.0'
    allowed_methods = ('GET', )
    model = Comment
    name = 'review_diff_comment'

    @webapi_check_local_site
    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Return a queryset for Comment models.

        By default, this returns all comments that are accessible to
        the requester.

        The queryset can be further filtered by one or more arguments
        in the URL. These are listed in :py:meth:`get_list`.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            is_list (bool, unused):
                Whether the coming HTTP request is request for list resources.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for Comment models.
        """
        local_site = request.local_site
        q = Q()

        if 'file-diff-id' in request.GET:
            q &= Q(filediff=request.GET.get('file-diff-id'))

        if 'interdiff-revision' in request.GET:
            q &= Q(('interfilediff__diffset__revision',
                   request.GET.get('interdiff-revision')))

        if 'is-reply' in request.GET:
            val = request.GET.get('is-reply')
            q &= Q(reply_to_id__isnull=(not val))

        if 'last-updated-from' in request.GET:
            q &= Q(timestamp__gte=request.GET.get('last-updated-from'))

        if 'last-updated-to' in request.GET:
            q &= Q(timestamp__lt=request.GET.get('last-updated-to'))

        if 'review-id' in request.GET:
            q &= Q(review=request.GET.get('review-id'))

        if 'review-request-id' in request.GET:
            review_request_id = request.GET.get('review-request-id')

            if local_site is None:
                q &= Q(review__review_request=review_request_id)
            else:
                q &= (Q(review__review_request__local_id=review_request_id) &
                      Q(review__review_request__local_site=local_site))

        if 'user' in request.GET:
            user = list((
                User.objects
                .filter(username=request.GET.get('user'))
                .values_list('pk', flat=True)
            ))

            if user:
                q &= Q(review__user=user[0])
            else:
                return self.model.objects.none()

        return self.model.objects.accessible(request.user,
                                             extra_query=q,
                                             local_site=local_site)

    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'file-diff-id': {
                'type': StringFieldType,
                'description': 'The file diff ID that the diff comments must '
                               'be belonged to.',
            },
            'interdiff-revision': {
                'type': IntFieldType,
                'description': 'The second revision in an interdiff revision '
                               'range. The comments will be limited to this '
                               'range.',
            },
            'is-reply': {
                'type': BooleanFieldType,
                'description': 'Determine whether to return diff comments '
                               'that are replies or not.',
            },
            'last-updated-from': {
                'type': DateTimeFieldType,
                'description': "The earliest date/time the diff comments "
                               "could be last updated. This is compared "
                               "against the diff comment's "
                               "``timestamp`` field. This must be a valid "
                               ":term:`date/time format`.",
            },
            'last-updated-to': {
                'type': DateTimeFieldType,
                'description': "The date/time that all diff comments must "
                               "be last updated before. This is compared "
                               "against the diff comment's "
                               "``timestamp`` field. This must be a valid "
                               ":term:`date/time format`.",
            },
            'line': {
                'type': IntFieldType,
                'description': 'Filter for comments that start on a '
                               'particular line in the file.',
            },
            'review-id': {
                'type': StringFieldType,
                'description': 'The review ID that the diff comments must '
                               'be belonged to.',
            },
            'review-request-id': {
                'type': StringFieldType,
                'description': 'The review request ID that the diff comments '
                               'must be belonged to.',
            },
            'user': {
                'type': StringFieldType,
                'description': 'The username of the user that the diff '
                               'comments must be owned by.',
            },
        },
        allow_unknown=True
    )
    @augment_method_from(BaseDiffCommentResource)
    def get_list(self, *args, **kwargs):
        """Return the list of file attachment comments."""
        pass

    def serialize_object(self, obj, request=None, *args, **kwargs):
        """Serialize a diff comment.

        Args:
            obj (reviewboard.reviews.models.diff_comment.Comment):
                The diff comment to serialize.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The serialized diff comment.
        """
        result = super(RootDiffCommentResource, self).serialize_object(
            obj, request=request, *args, **kwargs)

        if not dvcs_feature.is_enabled(request=request):
            result.pop('base_filediff_id', None)

        return result


root_diff_comment_resource = RootDiffCommentResource()
