"""API Resource for file attachments associated with files in diffs."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   INVALID_FORM_DATA,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED,
                                   WebAPIError)
from djblets.webapi.fields import (IntFieldType,
                                   ResourceFieldType,
                                   StringFieldType)

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.diffviewer.models import FileDiff
from reviewboard.webapi.base import ImportExtraDataError
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review_request_file_attachment import \
    BaseReviewRequestFileAttachmentResource

if TYPE_CHECKING:
    from django.http import HttpRequest


class DiffFileAttachmentResource(BaseReviewRequestFileAttachmentResource):
    """Provides information on file attachments associated with files in diffs.

    The list of file attachments are tied to files either committed to the
    repository or proposed in diffs to a review request on the repository.
    All are associated with a file in a diff.

    Files that are newly introduced in a diff and do not have a revision as
    of that diff will have the ``added_in_filediff`` link set, and
    ``repository_revision`` will be null.

    Version Changed:
        7.0:
        Added support for HTTP POST to the list resource.
    """

    added_in = '2.0'

    name = 'diff_file_attachment'
    model_parent_key = 'repository'
    allowed_methods = ('GET', 'POST')

    mimetype_list_resource_name = 'diff-file-attachments'
    mimetype_item_resource_name = 'diff-file-attachment'

    fields = dict({
        'repository_file_path': {
            'type': StringFieldType,
            'description': 'The file path inside the repository that this '
                           'file attachment represents.',
        },
        'repository_revision': {
            'type': StringFieldType,
            'description': 'The revision that introduced this version of the '
                           'file, if committed in the repository.',
        },
        'added_in_filediff': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.filediff.'
                        'FileDiffResource',
            'description': 'The file diff that introduced this file. If set, '
                           'this file is just part of a proposed change, and '
                           'not necessarily committed in the repository.',
        },
    }, **BaseReviewRequestFileAttachmentResource.fields)

    def serialize_repository_file_path_field(self, attachment, **kwargs):
        if attachment.added_in_filediff_id:
            return attachment.added_in_filediff.dest_file
        else:
            return attachment.repo_path

    def serialize_repository_revision_field(self, attachment, **kwargs):
        return attachment.repo_revision or None

    def has_access_permissions(self, request, obj, *args, **kwargs):
        repository = self.get_parent_object(obj)

        return repository.is_accessible_by(request.user)

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        repository = resources.repository.get_object(request, *args, **kwargs)
        queryset = self.model.objects.filter_for_repository(repository)

        if is_list:
            q = Q()

            if 'repository-file-path' in kwargs:
                path = kwargs['repository-file-path']

                q = q & (Q(repo_path=path) |
                         Q(added_in_filediff__source_file=path))

            if 'repository-revision' in kwargs:
                q = q & Q(repo_revision=kwargs['repository-revision'])

            if 'mimetype' in kwargs:
                q = q & Q(mimetype=kwargs['mimetype'])

            queryset = queryset.filter(q)

        return queryset

    def get_parent_object(self, obj):
        if obj.repository_id is None:
            assert obj.added_in_filediff_id is not None
            return obj.added_in_filediff.get_repository()
        else:
            return obj.repository

    @webapi_request_fields(
        optional=dict({
            'repository-file-path': {
                'type': StringFieldType,
                'description': (
                    'Filter file attachments with the given path in the '
                    'repository.'
                ),
            },
            'repository-revision': {
                'type': StringFieldType,
                'description': (
                    'Filter file attachments for files with the given '
                    'revision.'
                ),
            },
            'mimetype': {
                'type': StringFieldType,
                'description': (
                    'Filter file attachments with the given mimetype.'
                ),
            },
        }, **BaseReviewRequestFileAttachmentResource.get_list.optional_fields),
        required=BaseReviewRequestFileAttachmentResource.get_list
                                                        .required_fields
    )
    @augment_method_from(BaseReviewRequestFileAttachmentResource)
    def get_list(self, request, *args, **kwargs):
        """Returns the list of file attachments associated with diffs.

        Each item in this list is a file attachment associated with a file
        or a proposed change against the parent repository. A file attachment
        may be referenced by one or more diffs.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED,
                            INVALID_FORM_DATA, NOT_LOGGED_IN)
    @webapi_request_fields(
        required={
            'filediff': {
                'type': IntFieldType,
                'description': 'The ID of the FileDiff to create the '
                               'attachment for.',
            },
        },
        allow_unknown=True,
    )
    def create(
        self,
        request: HttpRequest,
        filediff: Optional[int] = None,
        extra_fields: Dict[str, Any] = {},
        *args,
        **kwargs,
    ) -> Union[tuple, WebAPIError]:
        """Creates a new diff file attachment.

        This will create a new file attachment and connect it to the provided
        FileDiff, for use with binary files in diffs.
        """
        try:
            repository = \
                resources.repository.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not repository.is_accessible_by(request.user):
            return self.get_no_access_error(request)

        try:
            filediff_obj = FileDiff.objects.get(pk=filediff)
        except ObjectDoesNotExist as e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'filediff': [str(e)],
                }
            }

        review_request = filediff_obj.get_review_request()

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        form_data = request.POST.copy()
        form = UploadFileForm(review_request, form_data, request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form),
            }

        try:
            file = form.create(filediff=filediff_obj)
        except ValueError as e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [str(e)],
                },
            }

        if extra_fields:
            try:
                self.import_extra_data(file, file.extra_data, extra_fields)
            except ImportExtraDataError as e:
                return e.error_payload

            file.save(update_fields=('extra_data',))

        return 201, {
            self.item_result_key: self.serialize_object(
                file, request=request, *args, **kwargs),
        }


diff_file_attachment_resource = DiffFileAttachmentResource()
