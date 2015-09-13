from __future__ import unicode_literals

import logging
import os

from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.html import escape
from django.utils.encoding import smart_str, force_unicode
from django.utils.safestring import mark_safe
from djblets.cache.backend import cache_memoize
from djblets.util.templatetags.djblets_images import thumbnail
from pipeline.storage import default_storage
from pygments import highlight
from pygments.lexers import (ClassNotFound, guess_lexer_for_filename,
                             TextLexer)
import docutils.core
import markdown
import mimeparse


_registered_mimetype_handlers = []


def register_mimetype_handler(handler):
    """Registers a MimetypeHandler class.

    This will register a Mimetype Handler used by Review Board to render
    thumbnails for the file attachements across different mimetypes.

    Only MimetypeHandler subclasses are supported.
    """
    if not issubclass(handler, MimetypeHandler):
        raise TypeError('Only MimetypeHandler subclasses can be registered')

    _registered_mimetype_handlers.append(handler)


def unregister_mimetype_handler(handler):
    """Unregisters a MimetypeHandler class.

    This will unregister a previously registered mimetype handler.

    Only MimetypeHandler subclasses are supported. The class must ahve been
    registered beforehand or a ValueError will be thrown.
    """
    if not issubclass(handler, MimetypeHandler):
        raise TypeError('Only MimetypeHandler subclasses can be unregistered')

    try:
        _registered_mimetype_handlers.remove(handler)
    except ValueError:
        logging.error('Failed to unregister missing mimetype handler %r' %
                      handler)
        raise ValueError('This mimetype handler was not previously registered')


def score_match(pattern, mimetype):
    """Returns a score for how well the pattern matches the mimetype.

    This is an ordered list of precedence (_ indicates non-match):
       Type/Vendor+Subtype   2
       Type/_     +Subtype   1.9
       Type/*                1.8
          */Vendor+Subtype   1.7
          */_     +Subtype   1.6
       Type/_                1
          */_                0.7
    """
    EXACT_TYPE = 1
    ANY_TYPE = 0.7
    EXACT_SUBTYPE = 1
    VND_SUBTYPE = 0.9
    ANY_SUBTYPE = 0.8

    score = 0

    if pattern[0] == mimetype[0]:
        score += EXACT_TYPE
    elif pattern[0] == '*':
        score += ANY_TYPE
    else:
        return 0

    if pattern[1] == mimetype[1]:
        score += EXACT_SUBTYPE
    elif pattern[1] == '*' or mimetype[1] == '*':
        score += ANY_SUBTYPE
    else:
        pattern_subtype = pattern[1].split('+')
        mimetype_subtype = mimetype[1].split('+')

        if len(mimetype_subtype) > 1:
            if len(pattern_subtype) > 1:
                if pattern_subtype[1] == mimetype_subtype[1]:
                    score += VND_SUBTYPE
            elif pattern_subtype[0] == mimetype_subtype[1]:
                score += VND_SUBTYPE
        elif len(pattern_subtype) > 1:
            if pattern_subtype[1] == mimetype_subtype[0]:
                score += VND_SUBTYPE

    return score


class MimetypeHandler(object):
    """Handles mimetype-specific properties.

    This class also acts as a generic handler for mimetypes not matched
    explicitly by any handler. Note that this is not the same as '*/*'.
    """
    MIMETYPES_DIR = 'rb/images/mimetypes'

    supported_mimetypes = []

    def __init__(self, attachment, mimetype):
        self.attachment = attachment
        self.mimetype = mimetype
        self.storage = default_storage

    @classmethod
    def get_best_handler(cls, mimetype):
        """Returns the handler and score that that best fit the mimetype."""
        best_score, best_fit = (0, None)

        for mimetype_handler in _registered_mimetype_handlers:
            for mt in mimetype_handler.supported_mimetypes:
                try:
                    score = score_match(mimeparse.parse_mime_type(mt),
                                        mimetype)

                    if score > best_score:
                        best_score, best_fit = (score, mimetype_handler)
                except ValueError:
                    continue

        return (best_score, best_fit)

    @classmethod
    def for_type(cls, attachment):
        """Returns the handler that is the best fit for provided mimetype."""
        if not attachment.mimetype:
            return None

        try:
            mimetype = mimeparse.parse_mime_type(attachment.mimetype)
        except:
            logging.warning('Unable to parse MIME type "%s" for %s',
                            attachment, attachment.mimetype)
            mimetype = ('application', 'octet-stream', {})

        # Override the mimetype if mimeparse is known to misinterpret this
        # type of file as `octet-stream`
        extension = os.path.splitext(attachment.filename)[1]

        if extension in MIMETYPE_EXTENSIONS:
            mimetype = MIMETYPE_EXTENSIONS[extension]

        score, handler = cls.get_best_handler(mimetype)

        if handler:
            try:
                return handler(attachment, mimetype)
            except Exception as e:
                logging.error('Unable to load Mimetype Handler for %s: %s',
                              attachment, e, exc_info=1)

        return MimetypeHandler(attachment, mimetype)

    def get_icon_url(self):
        mimetype_string = self.mimetype[0] + '/' + self.mimetype[1]

        if mimetype_string in MIMETYPE_ICON_ALIASES:
            path = self._get_mimetype_file(
                MIMETYPE_ICON_ALIASES[mimetype_string])
        else:
            path = self._get_mimetype_file(self.mimetype[0] + '-' +
                                           self.mimetype[1])
            if not self.storage.exists(path):
                path = self._get_mimetype_file(self.mimetype[0] + '-x-generic')

                if not self.storage.exists(path):
                    # We'll just use this as our fallback.
                    path = self._get_mimetype_file('text-x-generic')

        return static(path)

    def get_thumbnail(self):
        """Returns HTML that represents a preview of the attachment.

        The outer-most object should have the class 'file-thubmnail'.
        """
        return mark_safe('<pre class="file-thumbnail"></pre>')

    def set_thumbnail(self):
        """Set the thumbnail data.

        This should be implemented by subclasses if they need the thumbnail to
        be generated client-side."""
        raise NotImplementedError

    def _get_mimetype_file(self, name):
        return '%s/%s.png' % (self.MIMETYPES_DIR, name)


class ImageMimetype(MimetypeHandler):
    """Handles image mimetypes."""
    supported_mimetypes = ['image/*']

    def get_thumbnail(self):
        """Returns a thumbnail of the image."""
        return mark_safe('<img src="%s" data-at2x="%s" '
                         'class="file-thumbnail" alt="%s" />'
                         % (thumbnail(self.attachment.file),
                            thumbnail(self.attachment.file, '800x200'),
                            escape(self.attachment.caption)))


class TextMimetype(MimetypeHandler):
    """Handles text mimetypes."""
    supported_mimetypes = ['text/*']

    # Read up to 'FILE_CROP_CHAR_LIMIT' number of characters from
    # the file attachment to prevent long reads caused by malicious
    # or auto-generated files.
    FILE_CROP_CHAR_LIMIT = 2000
    TEXT_CROP_NUM_HEIGHT = 8

    def _generate_preview_html(self, data):
        """Returns the first few truncated lines of the text file."""
        from reviewboard.diffviewer.chunk_generator import \
            NoWrapperHtmlFormatter

        charset = self.mimetype[2].get('charset', 'ascii')
        try:
            text = data.decode(charset)
        except UnicodeDecodeError:
            logging.error('Could not decode text file attachment %s using '
                          'charset "%s"',
                          self.attachment.pk, charset)
            text = data.decode('utf-8', 'replace')

        try:
            lexer = guess_lexer_for_filename(self.attachment.filename, text)
        except ClassNotFound:
            lexer = TextLexer()

        lines = highlight(text, lexer, NoWrapperHtmlFormatter()).splitlines()

        return ''.join([
            '<pre>%s</pre>' % line
            for line in lines[:self.TEXT_CROP_NUM_HEIGHT]
        ])

    def _generate_thumbnail(self):
        """Returns the HTML for a thumbnail preview for a text file."""
        try:
            f = self.attachment.file.file
        except IOError as e:
            logging.error('Failed to locate file attachment %s: %s',
                          self.attachment.pk, e)
            return ''

        try:
            f.open()
            data = f.read(self.FILE_CROP_CHAR_LIMIT)
        except (ValueError, IOError) as e:
            logging.error('Failed to read from file attachment %s: %s',
                          self.attachment.pk, e)
            return ''
        finally:
            f.close()

        return mark_safe('<div class="file-thumbnail-clipped">%s</div>'
                         % self._generate_preview_html(data))

    def get_thumbnail(self):
        """Returns the thumbnail of the text file as rendered as html"""
        # Caches the generated thumbnail to eliminate the need on each page
        # reload to:
        # 1) re-read the file attachment
        # 2) re-generate the html based on the data read
        return mark_safe(
            cache_memoize('file-attachment-thumbnail-%s-html-%s'
                          % (self.__class__.__name__, self.attachment.pk),
                          self._generate_thumbnail))


class ReStructuredTextMimetype(TextMimetype):
    """Handles ReStructuredText (.rst) mimetypes."""
    supported_mimetypes = ['text/x-rst', 'text/rst']

    def _generate_preview_html(self, data_string):
        """Returns html of the ReST file as produced by docutils."""
        # Use safe filtering against injection attacks
        docutils_settings = {
            'file_insertion_enabled': False,
            'raw_enabled': False,
            '_disable_config': True
        }

        parts = docutils.core.publish_parts(
            source=smart_str(data_string),
            writer_name='html4css1',
            settings_overrides=docutils_settings)

        return parts['html_body']


class MarkDownMimetype(TextMimetype):
    """Handles MarkDown (.md) mimetypes."""
    supported_mimetypes = ['text/x-markdown', 'text/markdown']

    def _generate_preview_html(self, data_string):
        """Returns html of the MarkDown file as produced by markdown."""
        # Use safe filtering against injection attacks
        return markdown.markdown(
            force_unicode(data_string), safe_mode='escape',
            enable_attributes=False)


# A mapping of mimetypes to icon names.
#
# Normally, a mimetype will be normalized and looked up in our bundled
# list of mimetype icons. However, if the mimetype is in this list, the
# associated name is used instead.
MIMETYPE_ICON_ALIASES = {
    'application/magicpoint': 'x-office-presentation',
    'application/msword': 'x-office-document',
    'application/ogg': 'audio-x-generic',
    'application/pdf': 'x-office-document',
    'application/postscript': 'x-office-document',
    'application/rtf': 'x-office-document',
    'application/vnd.lotus-1-2-3': 'x-office-spreadsheet',
    'application/vnd.ms-excel': 'x-office-spreadsheet',
    'application/vnd.ms-powerpoint': 'x-office-presentation',
    'application/vnd.oasis.opendocument.graphics': 'x-office-drawing',
    'application/vnd.oasis.opendocument.graphics-template':
        'x-office-drawing-template',
    'application/vnd.oasis.opendocument.image': 'x-office-drawing',
    'application/vnd.oasis.opendocument.presentation': 'x-office-presentation',
    'application/vnd.oasis.opendocument.presentation-template':
        'x-office-presentation-template',
    'application/vnd.oasis.opendocument.spreadsheet': 'x-office-spreadsheet',
    'application/vnd.oasis.opendocument.spreadsheet-template':
        'x-office-spreadsheet-template',
    'application/vnd.oasis.opendocument.text': 'x-office-document',
    'application/vnd.oasis.opendocument.text-template':
        'x-office-document-template',
    'application/vnd.oasis.opendocument.text-web': 'text-html',
    'application/vnd.rn-realmedia': 'video-x-generic',
    'application/vnd.rn-realmedia-secure': 'video-x-generic',
    'application/vnd.rn-realmedia-vbr': 'video-x-generic',
    'application/vnd.stardivision.calc': 'x-office-spreadsheet',
    'application/vnd.stardivision.impress': 'x-office-presentation',
    'application/vnd.stardivision.writer': 'x-office-document',
    'application/vnd.sun.xml.calc': 'x-office-spreadsheet',
    'application/vnd.sun.xml.calc.template': 'x-office-spreadsheet-template',
    'application/vnd.sun.xml.draw': 'x-office-drawing',
    'application/vnd.sun.xml.draw.template': 'x-office-drawing-template',
    'application/vnd.sun.xml.impress': 'x-office-presentation',
    'application/vnd.sun.xml.impress.template':
        'x-office-presentation-template',
    'application/vnd.sun.xml.writer': 'x-office-document',
    'application/vnd.sun.xml.writer.template': 'x-office-document-template',
    'application/wordperfect': 'x-office-document',
    'application/x-7z-compressed': 'package-x-generic',
    'application/x-abiword': 'x-office-document',
    'application/x-applix-spreadsheet': 'x-office-spreadsheet',
    'application/x-applix-word': 'x-office-document',
    'application/x-archive': 'package-x-generic',
    'application/x-arj': 'package-x-generic',
    'application/x-bzip-compressed-tar': 'package-x-generic',
    'application/x-bzip': 'package-x-generic',
    'application/x-compressed-tar': 'package-x-generic',
    'application/x-compress': 'package-x-generic',
    'application/x-cpio-compressed': 'package-x-generic',
    'application/x-cpio': 'package-x-generic',
    'application/x-deb': 'package-x-generic',
    'application/x-dvi': 'x-office-document',
    'application/x-executable': 'application-x-executable',
    'application/x-font-afm': 'font-x-generic',
    'application/x-font-bdf': 'font-x-generic',
    'application/x-font-linux-psf': 'font-x-generic',
    'application/x-font-pcf': 'font-x-generic',
    'application/x-font-sunos-news': 'font-x-generic',
    'application/x-font-ttf': 'font-x-generic',
    'application/x-gnumeric': 'x-office-spreadsheet',
    'application/x-gzip': 'package-x-generic',
    'application/gzip': 'package-x-generic',
    'application/x-gzpostscript': 'x-office-document',
    'application/xhtml+xml': 'text-html',
    'application/x-jar': 'package-x-generic',
    'application/x-killustrator': 'image-x-generic',
    'application/x-kpresenter': 'x-office-presentation',
    'application/x-kspread': 'x-office-spreadsheet',
    'application/x-kword': 'x-office-document',
    'application/x-lha': 'package-x-generic',
    'application/x-lhz': 'package-x-generic',
    'application/x-lzma-compressed-tar': 'package-x-generic',
    'application/x-lzma': 'package-x-generic',
    'application/x-ms-dos-executable': 'application-x-executable',
    'application/x-perl': 'text-x-script',
    'application/x-php': 'text-html',
    'application/x-python-bytecode': 'text-x-script',
    'application/x-rar': 'package-x-generic',
    'application/x-rpm': 'package-x-generic',
    'application/x-scribus': 'x-office-document',
    'application/x-shellscript': 'text-x-script',
    'application/x-shockwave-flash': 'video-x-generic',
    'application/x-stuffit': 'package-x-generic',
    'application/x-tar': 'package-x-generic',
    'application/x-tarz': 'package-x-generic',
    'application/x-tex': 'x-office-document',
    'application/zip': 'package-x-generic',
    'text/html': 'text-html',
    'text/vnd.wap.wml': 'text-html',
    'text/x-csh': 'text-x-script',
    'text/x-python': 'text-x-script',
    'text/x-sh': 'text-x-script',
    'text/x-vcalendar': 'x-office-calendar',
    'text/x-vcard': 'x-office-address-book',
    'text/x-zsh': 'text-x-script',
}


# A mapping of file extensions to mimetypes
#
# Normally mimetypes are determined by mimeparse, then matched with
# one of the supported mimetypes classes through a best-match algorithm.
# However, mimeparse isn't always able to catch the unofficial mimetypes
# such as 'text/x-rst' or 'text/x-markdown', so we just go by the
# extension name.
MIMETYPE_EXTENSIONS = {
    '.rst': ('text', 'x-rst', {}),
    '.md': ('text', 'x-markdown', {}),
}
