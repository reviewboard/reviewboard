from __future__ import unicode_literals

import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Q
from django.utils import six
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.models import FileAttachment
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources


class BaseFileAttachmentResource(WebAPIResource):
    """A base resource representing file attachments."""
    added_in = '1.6'

    model = FileAttachment
    name = 'file_attachment'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the file.',
        },
        'caption': {
            'type': six.text_type,
            'description': "The file's descriptive caption.",
        },
        'filename': {
            'type': six.text_type,
            'description': "The name of the file.",
        },
        'url': {
            'type': six.text_type,
            'description': "The URL of the file, for downloading purposes. "
                           "If this is not an absolute URL, then it's "
                           "relative to the Review Board server's URL. "
                           "This is deprecated and will be removed in a "
                           "future version.",
            'deprecated_in': '2.0',
        },
        'absolute_url': {
            'type': six.text_type,
            'description': "The absolute URL of the file, for downloading "
                           "purposes.",
            'added_in': '2.0',
        },
        'icon_url': {
            'type': six.text_type,
            'description': 'The URL to a 24x24 icon representing this file. '
                           'The use of these icons is deprecated and this '
                           'property will be removed in a future version.',
            'deprecated_in': '2.5',
        },
        'mimetype': {
            'type': six.text_type,
            'description': 'The mimetype for the file.',
            'added_in': '2.0',
        },
        'thumbnail': {
            'type': six.text_type,
            'description': 'A thumbnail representing this file.',
            'added_in': '1.7',
        },
        'review_url': {
            'type': six.text_type,
            'description': 'The URL to a review UI for this file.',
            'added_in': '1.7',
        },
        'revision': {
            'type': int,
            'description': 'The revision of the file attachment.',
            'added_in': '2.5',
        },
        'attachment_history_id': {
            'type': int,
            'description': 'ID of the corresponding FileAttachmentHistory.',
            'added_in': '2.5',
        },
    }

    uri_object_key = 'file_attachment_id'

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)

        q = (Q(review_request=review_request) &
             Q(added_in_filediff__isnull=True) &
             Q(repository__isnull=True))

        if not is_list:
            q = q | Q(inactive_review_request=review_request)

        if request.user == review_request.submitter:
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

    def serialize_absolute_url_field(self, obj, request, **kwargs):
        return request.build_absolute_uri(obj.get_absolute_url())

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
                'type': file,
                'description': 'The file to upload.',
            },
        },
        optional={
            'caption': {
                'type': six.text_type,
                'description': 'The optional caption describing the '
                               'file.',
            },
            'attachment_history': {
                'type': int,
                'description': 'ID of the corresponding '
                               'FileAttachmentHistory.',
                'added_in': '2.5',
            },
        },
    )
    def create(self, request, *args, **kwargs):
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
                    'path': [six.text_type(e)],
                },
            }

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
                'type': six.text_type,
                'description': 'The new caption for the file.',
            },
            'thumbnail': {
                'type': six.text_type,
                'description': 'The thumbnail data for the file.',
                'added_in': '1.7.7',
            },
        }
    )
    def update(self, request, caption=None, thumbnail=None, *args, **kwargs):
        """Updates the file's data.

        This allows updating the file in a draft. The caption, currently,
        is the only thing that can be updated.
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

        if caption is not None:
            try:
                resources.review_request_draft.prepare_draft(request,
                                                             review_request)
            except PermissionDenied:
                return self.get_no_access_error(request)

            file.draft_caption = caption
            file.save()

        if thumbnail is not None:
            try:
                file.thumbnail = thumbnail
            except Exception as e:
                logging.error(
                    'Failed to store thumbnail for attachment %d: %s',
                    file.pk, e, request=request)
                return INVALID_FORM_DATA, {
                    'fields': {
                        'thumbnail': [six.text_type(e)],
                    }
                }

        return 200, {
            self.item_result_key: self.serialize_object(
                file, request=request, *args, **kwargs),
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            file_attachment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, file_attachment, *args,
                                           **kwargs):
            return self.get_no_access_error(request)

        # If this file attachment has never been made public,
        # delete the model itself.
        if (not file_attachment.review_request.exists() and
            not file_attachment.inactive_review_request.exists()):
            file_attachment.delete()
            return 204, {}

        # If this file attachment has never been made public,
        # delete the model itself.
        if (not file_attachment.review_request.exists() and
            not file_attachment.inactive_review_request.exists()):
            file_attachment.delete()
            return 204, {}

        try:
            draft = resources.review_request_draft.prepare_draft(
                request, review_request)
        except PermissionDenied:
            return self.get_no_access_error(request)

        if file_attachment.attachment_history_id is None:
            draft.inactive_file_attachments.add(file_attachment)
            draft.file_attachments.remove(file_attachment)
        else:
            # "Delete" all revisions of the given file
            all_revs = FileAttachment.objects.filter(
                attachment_history=file_attachment.attachment_history_id)

            for revision in all_revs:
                draft.inactive_file_attachments.add(revision)
                draft.file_attachments.remove(revision)

        draft.save()

        return 204, {}
