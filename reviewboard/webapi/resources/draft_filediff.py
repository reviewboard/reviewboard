from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.models import FileAttachment
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.filediff import FileDiffResource


class DraftFileDiffResource(FileDiffResource):
    """Provides information on per-file diffs that are part of a draft.

    Each of these contains a single, self-contained diff file that
    applies to exactly one file on a repository.
    """
    added_in = '2.0'

    name = 'draft_file'
    policy_id = 'draft_file_diff'
    uri_name = 'files'
    allowed_methods = ('GET', 'PUT')
    item_result_key = 'file'
    list_result_key = 'files'
    mimetype_list_resource_name = 'files'
    mimetype_item_resource_name = 'file'

    item_child_resources = [
        resources.draft_original_file,
        resources.draft_patched_file,
    ]

    def get_queryset(self, request, diff_revision, *args, **kwargs):
        draft = resources.review_request_draft.get_object(
            request, *args, **kwargs)

        return self.model.objects.filter(
            diffset__review_request_draft=draft,
            diffset__revision=diff_revision)

    def has_access_permissions(self, request, filediff, *args, **kwargs):
        draft = resources.review_request_draft.get_object(
            request, *args, **kwargs)

        return draft.is_accessible_by(request.user)

    def has_modify_permissions(self, request, filediff, *args, **kwargs):
        draft = resources.review_request_draft.get_object(
            request, *args, **kwargs)

        return draft.is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(FileDiffResource)
    def get(self, *args, **kwargs):
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(FileDiffResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of draft per-file diffs on the review request.

        Each per-file diff has information about the diff. It does not
        provide the contents of the diff. For that, access the per-file diff's
        resource directly and use the correct mimetype.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'dest_attachment_file': {
                'type': file,
                'description': (
                    'The file attachment to upload, representing the '
                    'modified file. This can only be used for binary '
                    'files.'
                ),
            },
        },
        allow_unknown=True
    )
    def update(self, request, extra_fields={}, *args, **kwargs):
        """Updates a per-file diff.

        If this represents a binary file, then the contents of the binary
        file can be uploaded before the review request is published.

        Extra data can be stored for later lookup by passing
        ``extra_data.key_name=value``. The ``key_name`` and ``value`` can be
        any valid strings. Passing a blank ``value`` will remove the key. The
        ``extra_data.`` prefix is required.
        """
        try:
            filediff = self.get_object(request, *args, **kwargs)
            review_request_draft = filediff.diffset.review_request_draft.get()
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request_draft.is_mutable_by(request.user):
            return self._no_access_error(request.user)

        if 'dest_attachment_file' in request.FILES:
            if not filediff.binary:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'dest_attachment_file': [
                            'Cannot upload a file attachment to a '
                            'non-binary file in a diff.',
                        ]
                    }
                }

            try:
                # Check if there's already an attachment. If so, bail.
                FileAttachment.objects.get_for_filediff(filediff)

                return INVALID_FORM_DATA, {
                    'fields': {
                        'dest_attachment_file': [
                            'There is already a file attachment associated '
                            'with this binary file.',
                        ]
                    }
                }
            except ObjectDoesNotExist:
                pass

            dest_attachment_file = request.FILES.get('dest_attachment_file')

            form = UploadFileForm(review_request_draft.review_request, {}, {
                'path': dest_attachment_file,
            })

            if not form.is_valid():
                return INVALID_FORM_DATA, {
                    'fields': self._get_form_errors(form),
                }

            form.create(filediff)

        if extra_fields:
            self.import_extra_data(filediff, filediff.extra_data, extra_fields)
            filediff.save(update_fields=['extra_data'])

        return 200, {
            self.item_result_key: filediff,
        }


draft_filediff_resource = DraftFileDiffResource()
