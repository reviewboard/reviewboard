from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   INVALID_ATTRIBUTE,
                                   INVALID_FORM_DATA,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import (BooleanFieldType,
                                   FileFieldType,
                                   StringFieldType)

from reviewboard.diffviewer.commit_utils import deserialize_validation_info
from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.webapi.base import ImportExtraDataError
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.diff import DiffResource


class DraftDiffResource(DiffResource):
    """Provides information on pending draft diffs for a review request.

    This list will only ever contain a maximum of one diff in current
    versions. This is to preserve compatibility with the public
    :ref:`webapi2.0-diff-resource`.

    POSTing to this resource will create or update a review request draft
    with the provided diff. This also mirrors the public diff resource.
    """
    added_in = '2.0'

    name = 'draft_diff'
    uri_name = 'diffs'
    model_parent_key = 'review_request_draft'
    item_result_key = 'diff'
    list_result_key = 'diffs'
    mimetype_list_resource_name = 'diffs'
    mimetype_item_resource_name = 'diff'

    item_child_resources = [
        resources.draft_diffcommit,
        resources.draft_filediff,
    ]

    def get_parent_object(self, diffset):
        return diffset.review_request_draft.get()

    def has_access_permissions(self, request, diffset, *args, **kwargs):
        return diffset.review_request_draft.get().is_accessible_by(
            request.user)

    def get_queryset(self, request, *args, **kwargs):
        try:
            draft = resources.review_request_draft.get_object(
                request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise self.model.DoesNotExist

        return self.model.objects.filter(review_request_draft=draft)

    @webapi_login_required
    @augment_method_from(DiffResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of draft diffs on the review request.

        Each diff has the target revision and list of per-file diffs
        associated with it.
        """
        pass

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_ATTRIBUTE,
                            INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'cumulative_diff': {
                'type': FileFieldType,
                'description': (
                    'The cumulative diff of the entire commit series this '
                    'resource represents.'
                ),
            },
            'finalize_commit_series': {
                'type': BooleanFieldType,
                'description': (
                    'Whether or not this is a request to finalize '
                    'the commit series represented by this resource.\n'
                    '\n'
                    'If this is set to ``true``, then both the '
                    '``cumulative_diff`` and ``validation_info`` fields are '
                    'required.'
                ),
            },
            'parent_diff': {
                'type': FileFieldType,
                'description': (
                    'The parent diff of the cumulative diff of the entire '
                    'commit series this resource represents.'
                ),
            },
            'validation_info': {
                'type': StringFieldType,
                'description': (
                    'Validation information returned when validating the last '
                    'commit in the series with the :ref:`DiffCommit '
                    'validation resource '
                    '<webapi2.0-validate-diff-commit-resource>`.'
                ),
            },
        },
        allow_unknown=True
    )
    def update(self, request, finalize_commit_series=False,
               validation_info=None, extra_fields={}, *args, **kwargs):
        """Update a diff.

        This is used for two purposes:

        1. For updating extra data on a draft diff.

           Extra data can be stored later lookup. See
           :ref:`webapi2.0-extra-data` for more information.

        2. For finalization of a draft diff on a review request created with
           commit history.
        """
        try:
            review_request = resources.review_request.get_object(
                request, *args, **kwargs)
            diffset = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        if extra_fields:
            try:
                self.import_extra_data(diffset, diffset.extra_data,
                                       extra_fields)
            except ImportExtraDataError as e:
                return e.error_payload

        if finalize_commit_series:
            if review_request.created_with_history:
                cumulative_diff = request.FILES.get('cumulative_diff')
                parent_diff = request.FILES.get('parent_diff')

                error_rsp = self._finalize_commit_series(request,
                                                         diffset,
                                                         cumulative_diff,
                                                         parent_diff,
                                                         validation_info)

                if error_rsp is not None:
                    return error_rsp

                # Only add default reviewers if this is the first time we've
                # published any diffsets.
                if review_request.can_add_default_reviewers():
                    diffset.review_request_draft.get().add_default_reviewers()
            elif dvcs_feature.is_enabled(request=request):
                return INVALID_ATTRIBUTE, {
                    'reason': 'This review request was not created with '
                              'commit history support.',
                }
            else:
                # Otherwise we silently ignore this option.
                finalize_commit_series = False

        if extra_fields or finalize_commit_series:
            diffset.save(update_fields=('extra_data',))

        return 200, {
            self.item_result_key: diffset,
        }

    def _finalize_commit_series(self, request, diffset, cumulative_diff,
                                parent_diff, validation_info):

        """Finalize the commit series represented by the given diffset.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            diffset (reviewboard.diffviewer.models.diffset.DiffSet):
                The diffset representing a commit series.

            cumulative_diff (django.core.files.uploadedfile.UploadedFile):
                The cumulative diff of the entire commit series.

            parent_diff (django.core.files.uploadedfile.UploadedFile):
                The parent diff, if any.

            validation_info (unicode):
                Validation information from the :py:class:`~reviewboard.webapi.
                resources.validate_diffcommit.ValidateDiffCommitResource`.

        Returns:
            tuple:
            If the finalization process is successful, ``None`` will be
            returned. Otherwise, a 2-tuple of the following will be returned:

            * The WebAPI error (:py:class:`~djblets.webapi.errors.
              WebAPIError`).
            * A response to serialize with the error (:py:class:`dict`).
        """
        field_errors = {}

        if cumulative_diff is None:
            field_errors['cumulative_diff'] = [
                'This field is required when finalize_commit_series is set.',
            ]

        if validation_info is None or not validation_info.strip():
            field_errors['validation_info'] = [
                'This field is required when finalize_commit_series is set.',
            ]
        else:
            try:
                validation_info = deserialize_validation_info(validation_info)
            except (TypeError, ValueError) as e:
                field_errors['validation_info'] = [
                    'Could not parse field: %s' % e,
                ]

        if diffset.is_commit_series_finalized:
            return INVALID_ATTRIBUTE, {
                'reason': 'This diff is already finalized.',
            }

        if field_errors:
            return INVALID_FORM_DATA, {
                'fields': field_errors,
            }

        if parent_diff:
            parent_diff_file_contents = parent_diff.read()
        else:
            parent_diff_file_contents = None

        diff_file_contents = cumulative_diff.read()

        try:
            diffset.finalize_commit_series(
                cumulative_diff=diff_file_contents,
                validation_info=validation_info,
                parent_diff=parent_diff_file_contents,
                request=request,
                save=False)
        except ValidationError as e:
            if e.code == 'invalid':
                return INVALID_ATTRIBUTE, {
                    'reason': e.message,
                }
            elif e.code == 'validation_info':
                return INVALID_FORM_DATA, {
                    'fields': {
                        'validation_info': [e.message],
                    },
                }

draft_diff_resource = DraftDiffResource()
