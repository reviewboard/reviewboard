from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_login_required

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_file_attachment import \
    BaseFileAttachmentResource


class FileAttachmentResource(BaseFileAttachmentResource):
    """A resource representing a file attachment on a review request."""
    model_parent_key = 'review_request'

    item_child_resources = [
        resources.file_attachment_comment,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    mimetype_list_resource_name = 'file-attachments'
    mimetype_item_resource_name = 'file-attachment'

    def get_parent_object(self, obj):
        return obj.get_review_request()

    @augment_method_from(BaseFileAttachmentResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of file attachments on the review request.

        Each item in this list is a file attachment attachment that is shown on
        the review request.
        """
        pass

    @augment_method_from(BaseFileAttachmentResource)
    def create(self, request, *args, **kwargs):
        """Creates a new file attachment from a file attachment.

        This accepts any file type and associates it with a draft of a
        review request.

        Creating a new file attachment will automatically create a new review
        request draft, if one doesn't already exist. This attachment will
        be part of that draft, and will be shown on the review request
        when it's next published.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The file's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.zip"

            <Content here>
            -- SoMe BoUnDaRy --
        """
        pass

    @augment_method_from(BaseFileAttachmentResource)
    def update(self, request, caption=None, *args, **kwargs):
        """Updates the file attachment's data.

        This allows updating information on the file attachment.

        Updating a file attachment will automatically create a new review
        request draft, if one doesn't already exist. The updates won't be
        public until the review request draft is published.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(BaseFileAttachmentResource)
    def delete(self, *args, **kwargs):
        """Deletes the file attachment.

        This will remove the file attachment from the draft review request.
        This cannot be undone.

        Deleting a file attachment will automatically create a new review
        request draft, if one doesn't already exist. The attachment won't
        be actually removed until the review request draft is published.

        This can be used to remove old file attachments that were previously
        shown, as well as newly added file attachments that were part of the
        draft.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass


file_attachment_resource = FileAttachmentResource()
