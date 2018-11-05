from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)
from djblets.webapi.fields import IntFieldType

from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.models import FileDiff
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_diff_comment import \
    BaseDiffCommentResource


class ReviewDiffCommentResource(BaseDiffCommentResource):
    """Provides information on diff comments made on a review.

    If the review is a draft, then comments can be added, deleted, or
    changed on this list. However, if the review is already published,
    then no changes can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    policy_id = 'review_diff_comment'
    model_parent_key = 'review'

    mimetype_list_resource_name = 'review-diff-comments'
    mimetype_item_resource_name = 'review-diff-comment'

    def get_queryset(self, request, review_id, *args, **kwargs):
        q = super(ReviewDiffCommentResource, self).get_queryset(
            request, *args, **kwargs)
        return q.filter(review=review_id)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required=dict({
            'filediff_id': {
                'type': IntFieldType,
                'description': 'The ID of the file diff the comment is on.',
            },
            'first_line': {
                'type': IntFieldType,
                'description': 'The line number the comment starts at.',
            },
            'num_lines': {
                'type': IntFieldType,
                'description': 'The number of lines the comment spans.',
            },
        }, **BaseDiffCommentResource.REQUIRED_CREATE_FIELDS),
        optional=dict({
            'base_filediff_id': {
                'type': IntFieldType,
                'description': 'The ID of the base filediff for the '
                               ':term:`cumulative diff` the comment is on.\n'
                               '\n'
                               'This is only supported for review requests '
                               'created with commit history support.',
            },
            'interfilediff_id': {
                'type': IntFieldType,
                'description': 'The ID of the second file diff in the '
                               'interdiff the comment is on.',
            },
        }, **BaseDiffCommentResource.OPTIONAL_CREATE_FIELDS),
        allow_unknown=True,
    )
    def create(self, request, filediff_id, interfilediff_id=None,
               base_filediff_id=None, *args, **kwargs):
        """Creates a new diff comment.

        This will create a new diff comment on this review. The review
        must be a draft review.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review.has_modify_permissions(request, review):
            return self.get_no_access_error(request)

        filediff = None
        interfilediff = None
        invalid_fields = {}

        try:
            filediff = FileDiff.objects.get(
                pk=filediff_id,
                diffset__history__review_request=review_request)
        except ObjectDoesNotExist:
            invalid_fields['filediff_id'] = [
                'This is not a valid filediff ID.',
            ]

        if filediff is None or not dvcs_feature.is_enabled(request=request):
            base_filediff_id = None

        if base_filediff_id is not None:
            if not review_request.created_with_history:
                invalid_fields['base_filediff_id'] = [
                    'This field cannot be specified on review requests '
                    'created without history support.'
                ]
            elif interfilediff_id is not None:
                invalid_fields.update({
                    'base_filediff_id': [
                        'This field cannot be specified with '
                        'interfilediff_id.',
                    ],
                    'interfilediff_id': [
                        'This field cannot be specified with '
                        'base_filediff_id.',
                    ],
                })
            elif base_filediff_id == filediff_id:
                invalid_fields['base_filediff_id'] = [
                    'This cannot be the same as filediff_id.',
                ]

            elif base_filediff_id > filediff_id:
                invalid_fields['base_filediff_id'] = [
                    'This is not a valid base filediff ID.',
                ]
            else:
                base_filediff_exists = (
                    FileDiff.objects
                    .filter(diffset_id=filediff.diffset_id,
                            pk=base_filediff_id)
                    .exclude(commit_id=filediff.commit_id)
                    .exists()
                )

                if not base_filediff_exists:
                    invalid_fields['base_filediff_id'] = [
                        'This is not a valid base filediff ID.',
                    ]
                else:
                    ancestor_ids = (
                        ancestor.pk
                        for ancestor in filediff.get_ancestors(
                            minimal=False)
                    )

                    if base_filediff_id not in ancestor_ids:
                        invalid_fields['base_filediff_id'] = [
                            'This is not a valid base filediff ID.',
                        ]

        if filediff and interfilediff_id:
            if interfilediff_id == filediff.id:
                invalid_fields.setdefault('interfilediff_id', []).append(
                    'This cannot be the same as filediff_id.')
            else:
                try:
                    interfilediff = FileDiff.objects.get(
                        pk=interfilediff_id,
                        diffset__history=filediff.diffset.history)
                except ObjectDoesNotExist:
                    invalid_fields.setdefault('interfilediff_id', []).append(
                        'This is not a valid interfilediff ID.')

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
            }

        return self.create_comment(
            request=request,
            review=review,
            comments_m2m=review.comments,
            filediff=filediff,
            interfilediff=interfilediff,
            fields=('filediff', 'interfilediff', 'first_line', 'num_lines'),
            base_filediff_id=base_filediff_id,
            **kwargs)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional=dict({
            'first_line': {
                'type': IntFieldType,
                'description': 'The line number the comment starts at.',
            },
            'num_lines': {
                'type': IntFieldType,
                'description': 'The number of lines the comment spans.',
            },
        }, **BaseDiffCommentResource.OPTIONAL_UPDATE_FIELDS),
        allow_unknown=True,
    )
    def update(self, request, *args, **kwargs):
        """Updates a diff comment.

        This can update the text or line range of an existing comment.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
            diff_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return self.update_comment(request=request,
                                   review=review,
                                   comment=diff_comment,
                                   update_fields=('first_line', 'num_lines'),
                                   **kwargs)

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes the comment.

        This will remove the comment from the review. This cannot be undone.

        Only comments on draft reviews can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of comments made on a review.

        This list can be filtered down by using the ``?line=`` and
        ``?interdiff-revision=``.

        To filter for comments that start on a particular line in the file,
        using ``?line=``.

        To filter for comments that span revisions of diffs, you can specify
        the second revision in the range using ``?interdiff-revision=``.
        """
        pass

    def create_comment(self, request, comments_m2m, base_filediff_id=None,
                       **kwargs):
        """Create a review comment.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            comments_m2m (django.db.models.ManyToManyField):
                The review's comments relation, where the new comment will be
                added.

            base_filediff_id (int, optional):
                The ID of the base filediff for the :term:`cumulative diff` the
                comment is on.

            **kwargs (dict):
                Additional keyword arguments to pass on to the base class
                method.

        Returns:
            tuple or djblets.webapi.errors.WebAPIError:
            Either a successful payload containing the comment, or an error
            payload.
        """
        rsp = super(ReviewDiffCommentResource, self).create_comment(
            comments_m2m=comments_m2m,
            save=False,
            **kwargs)

        if (isinstance(rsp, tuple) and
            isinstance(rsp[1], dict) and
            self.item_result_key in rsp[1]):
            comment = rsp[1][self.item_result_key]

            if (base_filediff_id is not None and
                dvcs_feature.is_enabled(request=request)):
                comment.base_filediff_id = base_filediff_id

            comment.save()
            comments_m2m.add(comment)

        return rsp

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
        result = super(ReviewDiffCommentResource, self).serialize_object(
            obj, request=request, *args, **kwargs)

        if not dvcs_feature.is_enabled(request=request):
            result.pop('base_filediff_id', None)

        return result


review_diff_comment_resource = ReviewDiffCommentResource()
