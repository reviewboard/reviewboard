from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources.base_file_attachment_comment import \
    BaseFileAttachmentCommentResource


class FileAttachmentCommentResource(BaseFileAttachmentCommentResource):
    """Provides information on filess comments made on a review request.

    The list of comments cannot be modified from this resource. It's meant
    purely as a way to see existing comments that were made on a file. These
    comments will span all public reviews.

    If the ``text_type`` field is set to ``markdown``, then the ``text``
    field should be interpreted by the client as Markdown text.

    The returned text in the payload can be provided in a different format
    by passing ``?force-text-type=`` in the request. This accepts all the
    possible values listed in the ``text_type`` field below.
    """
    model_parent_key = 'file_attachment'
    uri_object_key = None

    def get_queryset(self, request, file_attachment_id, *args, **kwargs):
        q = super(FileAttachmentCommentResource, self).get_queryset(
            request, *args, **kwargs)
        q = q.filter(file_attachment=file_attachment_id)
        return q

    @webapi_check_local_site
    @augment_method_from(BaseFileAttachmentCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of comments on a file attachment.

        This list of comments will cover all comments made on this
        file from all reviews.
        """
        pass


file_attachment_comment_resource = FileAttachmentCommentResource()
