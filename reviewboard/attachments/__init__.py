from __future__ import unicode_literals

from reviewboard.signals import initializing


def _register_mimetype_handlers(**kwargs):
    """Register all bundled Mimetype Handlers."""
    from reviewboard.attachments.mimetypes import (ImageMimetype,
                                                   MarkDownMimetype,
                                                   MimetypeHandler,
                                                   register_mimetype_handler,
                                                   ReStructuredTextMimetype,
                                                   TextMimetype,
                                                   VideoMimetype)

    register_mimetype_handler(ImageMimetype)
    register_mimetype_handler(MarkDownMimetype)
    register_mimetype_handler(MimetypeHandler)
    register_mimetype_handler(ReStructuredTextMimetype)
    register_mimetype_handler(TextMimetype)
    register_mimetype_handler(VideoMimetype)


initializing.connect(_register_mimetype_handlers)
