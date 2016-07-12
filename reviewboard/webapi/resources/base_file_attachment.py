from __future__ import unicode_literals

from django.utils import six

from reviewboard.attachments.models import FileAttachment
from reviewboard.webapi.base import WebAPIResource


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
    }

    uri_object_key = 'file_attachment_id'

    def serialize_absolute_url_field(self, obj, request, **kwargs):
        return request.build_absolute_uri(obj.get_absolute_url())

    def serialize_caption_field(self, obj, **kwargs):
        # We prefer 'caption' here, because when creating a new file
        # attachment, it won't be full of data yet (and since we're posting
        # to file-attachments/, it doesn't hit DraftFileAttachmentResource).
        # DraftFileAttachmentResource will prefer draft_caption, in case people
        # are changing an existing one.

        return obj.caption or obj.draft_caption
