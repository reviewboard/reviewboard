from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set, Union

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Q
from django.http import HttpRequest
from django.utils.translation import gettext as _
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   INVALID_FORM_DATA,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED,
                                   WebAPIError)
from djblets.webapi.fields import (BooleanFieldType,
                                   FileFieldType,
                                   IntFieldType,
                                   StringFieldType)

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models.review_request import FileAttachmentState
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.base import ImportExtraDataError
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_file_attachment import \
    BaseFileAttachmentResource


logger = logging.getLogger(__name__)


class BaseReviewRequestFileAttachmentResource(BaseFileAttachmentResource):
    """A base resource representing file attachments."""

    fields = dict({
        'attachment_history_id': {
            'type': IntFieldType,
            'description': 'ID of the corresponding FileAttachmentHistory.',
            'added_in': '2.5',
        },
        'review_url': {
            'type': StringFieldType,
            'description': 'The URL to a review UI for this file.',
            'added_in': '1.7',
        },
        'revision': {
            'type': IntFieldType,
            'description': 'The revision of the file attachment.',
            'added_in': '2.5',
        },
        'url': {
            'type': StringFieldType,
            'description': "The URL of the file, for downloading purposes. "
                           "If this is not an absolute URL, then it's "
                           "relative to the Review Board server's URL. "
                           "This is deprecated and will be removed in a "
                           "future version.",
            'deprecated_in': '2.0',
        },
    }, **BaseFileAttachmentResource.fields)

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)

        q = (Q(review_request=review_request) &
             Q(added_in_filediff__isnull=True) &
             Q(repository__isnull=True) &
             Q(user__isnull=True))

        if not is_list:
            q = q | Q(inactive_review_request=review_request)

        if review_request.is_mutable_by(request.user):
            try:
                draft = resources.review_request_draft.get_object(
                    request, *args, **kwargs)

                q = q | Q(drafts=draft)

                if not is_list:
                    q = q | Q(inactive_drafts=draft)
            except ObjectDoesNotExist:
                pass

        return self.model.objects.filter(q)

    def serialize_url_field(self, obj, **kwargs):
        return obj.get_absolute_url()

    def serialize_review_url_field(self, obj, **kwargs):
        if obj.review_ui:
            review_request = obj.get_review_request()
            if review_request.local_site_id:
                local_site_name = review_request.local_site.name
            else:
                local_site_name = None

            return local_site_reverse(
                'file-attachment', local_site_name=local_site_name,
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': obj.pk,
                })

        return ''

    def serialize_revision_field(self, obj, *args, **kwargs):
        return obj.attachment_revision

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED,
                            INVALID_FORM_DATA, NOT_LOGGED_IN)
    @webapi_request_fields(
        required={
            'path': {
                'type': FileFieldType,
                'description': 'The file to upload.',
            },
        },
        optional={
            'caption': {
                'type': StringFieldType,
                'description': 'The optional caption describing the '
                               'file.',
            },
            'attachment_history': {
                'type': IntFieldType,
                'description': 'ID of the corresponding '
                               'FileAttachmentHistory.',
                'added_in': '2.5',
            },
        },
        allow_unknown=True
    )
    def create(
        self,
        request: HttpRequest,
        extra_fields: Dict[str, Any] = {},
        *args,
        **kwargs,
    ) -> Union[tuple, WebAPIError]:
        """Creates a new file from a file attachment.

        This accepts any file type and associates it with a draft of a
        review request.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The file's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.zip"

            <Content here>
            -- SoMe BoUnDaRy --

        Extra data can be stored for later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        form_data = request.POST.copy()
        form = UploadFileForm(review_request, form_data, request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form),
            }

        try:
            file = form.create()
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

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'caption': {
                'type': StringFieldType,
                'description': 'The new caption for the file.',
            },
            'pending_deletion': {
                'type': BooleanFieldType,
                'description': 'Whether the file attachment is currently '
                               'pending deletion. This can be set to '
                               '``false`` to undo the pending deletion of '
                               'a published file attachment.',
                'added_in': '6.0',
            },
            'thumbnail': {
                'type': StringFieldType,
                'description': 'The thumbnail data for the file.',
                'added_in': '1.7.7',
            },
        },
        allow_unknown=True
    )
    def update(
        self,
        request: HttpRequest,
        caption: Optional[str] = None,
        thumbnail: Optional[bytes] = None,
        pending_deletion: Optional[bool] = None,
        extra_fields: Dict[str, Any] = {},
        *args,
        **kwargs,
    ) -> Union[tuple, WebAPIError]:
        """Updates the file's data.

        This allows updating the file in a draft. Currently, only the caption,
        thumbnail and extra_data can be updated. See
        :ref:`webapi2.0-extra-data` for more information.

        Set ``pending_deletion=false`` in the request to undo the pending
        deletion of a published file attachment. Setting this to ``true`` is
        unsupported and will not delete the file attachment. To perform a
        deletion, perform a HTTP DELETE on the resource instead.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return PERMISSION_DENIED

        try:
            file = resources.file_attachment.get_object(request, *args,
                                                        **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            draft = resources.review_request_draft.prepare_draft(
                request,
                review_request)
        except PermissionDenied:
            return self.get_no_access_error(request)

        if caption is not None:
            file.draft_caption = caption

        try:
            self.import_extra_data(file, file.extra_data, extra_fields)
        except ImportExtraDataError as e:
            return e.error_payload

        file.save()

        if thumbnail is not None:
            try:
                file.thumbnail = thumbnail
            except Exception as e:
                logger.error(
                    'Failed to store thumbnail for attachment %d: %s',
                    file.pk, e,
                    extra={'request': request})
                return INVALID_FORM_DATA, {
                    'fields': {
                        'thumbnail': [str(e)],
                    }
                }

        if pending_deletion is True:
            return INVALID_FORM_DATA, {
                'fields': {
                    'pending_deletion': _(
                        'This can only be set to false to undo the pending '
                        'deletion of a published file attachment. You cannot '
                        'set this to true.'
                    ),
                },
            }
        elif pending_deletion is False:
            state = draft.get_file_attachment_state(file)

            if state != FileAttachmentState.PENDING_DELETION:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'pending_deletion': _(
                            'This can only be used to undo the pending '
                            'deletion of a file attachment. This file '
                            'attachment is not currently pending deletion.'
                        ),
                    },
                }

            update_ids: Set[Any] = {file.pk}

            if file.attachment_history_id is not None:
                # Undo the pending deletion for all revisions of the file.
                all_revs = list(
                    FileAttachment.objects
                    .filter(attachment_history=file.attachment_history_id)
                    .values_list('pk', flat=True)
                )

                update_ids.update(all_revs)

            draft.inactive_file_attachments.remove(*update_ids)
            draft.file_attachments.add(*update_ids)

        # Make sure the last_updated field gets updated.
        draft.save(update_fields=('last_updated',))

        return 200, {
            self.item_result_key: self.serialize_object(
                file, request=request, *args, **kwargs),
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(
        self,
        request: HttpRequest,
        *args,
        **kwargs
    ) -> Union[tuple, WebAPIError]:
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            file_attachment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, file_attachment, *args,
                                           **kwargs):
            return self.get_no_access_error(request)

        try:
            draft = resources.review_request_draft.prepare_draft(
                request, review_request)
        except PermissionDenied:
            return self.get_no_access_error(request)

        if (not file_attachment.review_request.exists() and
            not file_attachment.inactive_review_request.exists()):
            # If this file attachment has never been made public,
            # delete the model itself.
            file_attachment.delete()
        else:
            # Put the file attachment and all of its revisions in a pending
            # deletion state.
            update_ids: Set[Any] = {file_attachment.pk}
            attachment_history_id = file_attachment.attachment_history_id

            if file_attachment.attachment_history_id is not None:
                all_revs = list(
                    FileAttachment.objects
                    .filter(attachment_history=attachment_history_id)
                    .values_list('pk', flat=True)
                )

                update_ids.update(all_revs)

            draft.inactive_file_attachments.add(*update_ids)
            draft.file_attachments.remove(*update_ids)

        # Make sure the last_updated field gets updated.
        draft.save(update_fields=('last_updated',))

        return 204, {}
