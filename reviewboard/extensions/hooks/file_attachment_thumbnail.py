"""A hook for creating new thumbnailers for file attachments."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

from reviewboard.attachments.mimetypes import (register_mimetype_handler,
                                               unregister_mimetype_handler)


class FileAttachmentThumbnailHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """This hook allows custom thumbnails to be defined for file attachments.

    This accepts a list of mimetype handlers specified by the Extension
    that must:

    * Subclass :py:class:`reviewboard.attachments.mimetypes.MimetypeHandler`
    * Define a list of file mimetypes it can handle in a class variable
      called ``supported_mimetypes``
    * Define how to generate a thumbnail of that mimetype by overriding
      the instance function ``def get_thumbnail(self):``

    These mimetype handlers are registered when the hook is created. Likewise,
    it unregisters the same list of mimetype handlers when the extension is
    disabled.
    """

    def initialize(self, mimetype_handlers):
        """Initialize the hook.

        This will register each of the provided mimetype handler classes.

        Args:
            mimetype_handlers (list of type):
                The list of mimetype handlers to register. Each must be a
                subclass of
                :py:class:`~reviewboard.attachments.mimetypes.MimetypeHandler`.

        Raises:
            TypeError:
                One or more of the provided classes are not of the correct
                type.
        """
        self.mimetype_handlers = mimetype_handlers

        for mimetype_handler in self.mimetype_handlers:
            register_mimetype_handler(mimetype_handler)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the mimetype handler classes.
        """
        for mimetype_handler in self.mimetype_handlers:
            unregister_mimetype_handler(mimetype_handler)
