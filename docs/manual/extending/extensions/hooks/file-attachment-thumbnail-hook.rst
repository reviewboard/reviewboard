.. _extension-file-attachment-thumbnail-hook:
.. _file-attachment-thumbnail-hook:

===========================
FileAttachmentThumbnailHook
===========================

:py:class:`reviewboard.extensions.hooks.FileAttachmentThumbnailHook` allows
extensions to create custom thumbnailers for new file types. This is
particularly useful when combined with :ref:`extension-review-ui-integration`.

To use this, define a subclass of
:py:class:`reviewboard.attachments.mimetypes.MimetypeHandler`, where you'll
define a list of ``supported_mimetypes`` and a method for creating the
thumbnail:


Example
=======

.. code-block:: python

    import logging

    import pygments
    from django.utils.encoding import force_unicode
    from django.utils.safestring import mark_safe
    from reviewboard.attachments.mimetypes import MimetypeHandler
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import FileAttachmentThumbnailHook


    class XMLMimetype(MimetypeHandler):
        # Generate thumbnails for these mimetypes
        supported_mimetypes = ['application/xml', 'text/xml']

        def get_thumbnail(self):
            # This renders the XML using pygments to syntax highlight it. The
            # HTML will then be stuck inside the thumbnail element styled to
            # use a small font and clipped to the size of the thumbnail box.
            f = self.attachment.file.file
            f.open()

            try:
                # Only use the first 2000 characters
                data_string = f.read(2000)
            except (ValueError, IOError), e:
                logging.error('Failed to read from file attachment %s: %s'
                              % (self.attachment.pk, e))

            f.close()

            html = pygments.highlight(force_unicode(data_string),
                                      pygments.lexers.XmlLexer(),
                                      pygments.formatters.HtmlFormatter())

            return mark_safe('<div class="file-thumbnail-clipped">%s</div>'
                             % html)


    class XMLThumbnailExtension(Extension):
        def initialize(self):
            FileAttachmentThumbnailHook(self, [XMLMimetype])
