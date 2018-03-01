from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, DUPLICATE_ITEM,
                                   INVALID_FORM_DATA, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import FileFieldType, StringFieldType

from reviewboard.admin.server import build_server_url
from reviewboard.attachments.forms import UploadUserFileForm
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_file_attachment import \
    BaseFileAttachmentResource


class UserFileAttachmentResource(BaseFileAttachmentResource):
    """A resource representing a file attachment owned by a user.

    The file attachment is not tied to any particular review request, and
    instead is owned by a user for usage in Markdown-formatted text.

    The file contents are optional when first creating a file attachment. This
    is to allow a caller to create the attachment and get the resulting URL for
    embedding in a text field. The file's contents can then be added separately
    (and only once) in a PUT request.
    """

    name = 'user_file_attachment'
    model_parent_key = 'user'

    added_in = '3.0'

    mimetype_list_resource_name = 'user-file-attachments'
    mimetype_item_resource_name = 'user-file-attachment'

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def serialize_absolute_url_field(self, obj, request, **kwargs):
        if obj.local_site:
            local_site_name = request._local_site_name
        else:
            local_site_name = None

        return build_server_url(local_site_reverse(
            'user-file-attachment',
            local_site_name=local_site_name,
            kwargs={
                'file_attachment_uuid': obj.uuid,
                'username': obj.user.username,
            }))

    def get_serializer_for_object(self, obj):
        return user_file_attachment_resource

    def get_queryset(self, request, is_list=False, local_site_name=None, *args,
                     **kwargs):
        user = resources.user.get_object(
            request, local_site_name=local_site_name, *args, **kwargs)

        local_site = self._get_local_site(local_site_name)

        return self.model.objects.filter(user=user, local_site=local_site)

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        return obj.is_mutable_by(request.user)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return obj.is_mutable_by(request.user)

    def has_list_access(self, request, user):
        return (request.user.is_authenticated() and
                (request.user.is_superuser or request.user == user))

    @augment_method_from(BaseFileAttachmentResource)
    def get(self, *args, **kwargs):
        """Returns information on a user's file attachment."""
        pass

    @augment_method_from(BaseFileAttachmentResource)
    def get_list(self, request, *args, **kwargs):
        """Returns a list of file attachments that are owned by the user."""
        try:
            user = resources.user.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_list_access(request, user):
            return self.get_no_access_error(request)

        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED,
                            NOT_LOGGED_IN, INVALID_FORM_DATA)
    @webapi_request_fields(
        optional={
            'caption': {
                'type': StringFieldType,
                'description': 'The optional caption describing the '
                               'file.',
            },
            'path': {
                'type': FileFieldType,
                'description': 'The file to upload.',
            },
        },
    )
    def create(self, request, local_site_name=None, *args, **kwargs):
        """Creates a new file attachment that is owned by the user.

        This accepts any file type and associates it with the user. Optionally,
        the file may be omitted here and uploaded later by updating the file
        attachment.

        If file data is provided, then it is expected that the data will be
        encoded as :mimetype:`multipart/form-data`. The file's name and content
        should be stored in the ``path`` field. A typical request may look
        like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.zip"

            <Content here>
            -- SoMe BoUnDaRy --
        """
        try:
            user = resources.user.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        local_site = self._get_local_site(local_site_name)

        if ((local_site and not local_site.is_accessible_by(request.user)) or
           not self.has_list_access(request, user)):
            return self.get_no_access_error(request)

        form = UploadUserFileForm(request.POST, request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form),
            }

        file_attachment = form.create(request.user, local_site)

        return 201, {
            self.item_result_key: self.serialize_object(
                file_attachment, request=request, *args, **kwargs),
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, DUPLICATE_ITEM,
                            INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'caption': {
                'type': StringFieldType,
                'description': 'The optional caption describing the '
                               'file.',
            },
            'path': {
                'type': FileFieldType,
                'description': 'The file to upload.',
            },
        },
    )
    def update(self, request, local_site_name=None, *args, **kwargs):
        """Updates the file attachment's data.

        This allows updating information on the file attachment. It also allows
        the file to be uploaded if this was not done when the file attachment
        was created.

        The file attachment's file cannot be updated once it has been uploaded.
        Attempting to update the file attachment's file if it has already been
        uploaded will result in a :ref:`webapi2.0-error-111`.

        The file attachment can only be updated by its owner or by an
        administrator.

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
            file_attachment = self.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, file_attachment,
                                           *args, **kwargs):
            return self.get_no_access_error(request)

        if 'path' in request.FILES and file_attachment.file:
            return DUPLICATE_ITEM

        form = UploadUserFileForm(request.POST, request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form),
            }

        file_attachment = form.update(file_attachment)

        return 200, {
            self.item_result_key: file_attachment
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED, NOT_LOGGED_IN)
    def delete(self, request, local_site_name=None, *args, **kwargs):
        """Deletes a file attachment.

        This will permanently remove the file attachment owned by the user.
        This cannot be undone.

        The file attachment can only be deleted by its owner or an
        administrator.
        """
        try:
            file_attachment = self.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, file_attachment,
                                           *args, **kwargs):
            return self.get_no_access_error(request)

        if file_attachment.file:
            file_attachment.file.delete()

        file_attachment.delete()

        return 204, {}

user_file_attachment_resource = UserFileAttachmentResource()
