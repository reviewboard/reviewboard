"""File attachment mimetype registration and scoring."""

from __future__ import unicode_literals

import docutils.core
import logging
import os
import subprocess

import mimeparse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.html import format_html, format_html_join
from django.utils.encoding import smart_str, force_unicode
from django.utils.safestring import mark_safe
from djblets.cache.backend import cache_memoize
from djblets.util.filesystem import is_exe_in_path
from djblets.util.templatetags.djblets_images import thumbnail
from pygments import highlight
from pygments.lexers import (ClassNotFound, guess_lexer_for_filename,
                             TextLexer)

from reviewboard.reviews.markdown_utils import render_markdown


_registered_mimetype_handlers = []


DEFAULT_MIMETYPE = 'application/octet-stream'


def guess_mimetype(uploaded_file):
    """Guess the mimetype of an uploaded file.

    Uploaded files don't necessarily have valid mimetypes provided,
    so attempt to guess them when they're blank.

    This only works if `file` is in the path. If it's not, or guessing fails,
    we fall back to a mimetype of :mimetype:`application/octet-stream`.

    Args:
        uploaded_file (django.core.files.File):
            The uploaded file object.

    Returns:
        unicode:
        The guessed mimetype.
    """
    if not is_exe_in_path('file'):
        return DEFAULT_MIMETYPE

    # The browser didn't know what this was, so we'll need to do
    # some guess work. If we have 'file' available, use that to
    # figure it out.
    p = subprocess.Popen(['file', '--mime-type', '-b', '-'],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE)

    # Write the content from the file until file has enough data to
    # make a determination.
    for chunk in uploaded_file.chunks():
        try:
            p.stdin.write(chunk)
        except IOError:
            # file closed, so we hopefully have an answer.
            break

    p.stdin.close()
    ret = p.wait()

    if ret == 0:
        mimetype = p.stdout.read().strip()

    # Reset the read position so we can properly save this.
    uploaded_file.seek(0)

    return mimetype or DEFAULT_MIMETYPE


def get_uploaded_file_mimetype(uploaded_file):
    """Return the mimetype of a file that was uploaded.

    There are several things that can go wrong with browser-provided mimetypes.
    In one case (bug 3427), Firefox on Linux Mint was providing a mimetype that
    looked like ``text/text/application/pdf``, which is unparseable. IE also
    has a habit of setting any unknown file type to
    :mimetype:`application/octet-stream`, rather than just choosing not to
    provide a mimetype. In the case where what we get from the browser is
    obviously wrong, try to guess.

    Args:
        uploaded_file (django.core.files.File):
            The uploaded file object.

    Returns:
        unicode:
        The guessed mimetype.
    """
    if (uploaded_file.content_type and
        len(uploaded_file.content_type.split('/')) == 2 and
            uploaded_file.content_type != 'application/octet-stream'):
        mimetype = uploaded_file.content_type
    else:
        mimetype = guess_mimetype(uploaded_file)

    return mimetype


def register_mimetype_handler(handler):
    """Register a MimetypeHandler class.

    This will register a mimetype Handler used by Review Board to render
    thumbnails for the file attachments across different mimetypes.

    Args:
        handler (type):
            The mimetype handler to register. This must be a subclass of
            :py:class:`MimetypeHandler`.

    Raises:
        TypeError:
            The provided class is not of the correct type.
    """
    if not issubclass(handler, MimetypeHandler):
        raise TypeError('Only MimetypeHandler subclasses can be registered')

    _registered_mimetype_handlers.append(handler)


def unregister_mimetype_handler(handler):
    """Unregister a MimetypeHandler class.

    This will unregister a previously registered mimetype handler.

    Args:
        handler (type):
            The mimetype handler to unregister. This must be a subclass of
            :py:class:`MimetypeHandler`.

    Raises:
        TypeError:
            The provided class is not of the correct type.

        ValueError:
            The mimetype handler was not previously registered.
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
    """Return a score for how well the pattern matches the mimetype.

    This is an ordered list of precedence (``_`` indicates non-match):

    ======================= ==========
    Format                  Precedence
    ======================= ==========
    ``Type/Vendor+Subtype`` 2
    ``Type/_     +Subtype`` 1.9
    ``Type/*``              1.8
    ``*/Vendor+Subtype``    1.7
    ``*/_     +Subtype``    1.6
    ``Type/_``              1
    ``*/_``                 0.7
    ======================= ==========

    Args:
        pattern (unicode):
            The pattern to match.

        mimetype (unicode):
            The mimetype to check for the pattern.

    Returns:
        float:
        The resulting score for the match.
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
    explicitly by any handler. Note that this is not the same as ``*/*``.

    Attributes:
        attachment (reviewboard.attachments.models.FileAttachment):
            The file attachment being handled.

        mimetype (unicode):
            The mimetype for the file attachment.
    """

    MIMETYPES_DIR = 'rb/images/mimetypes'

    #: A list of mimetypes supported by this handler.
    supported_mimetypes = []

    #: Whether HD thumbnails are provided by this handler.
    #:
    #: Subclasses (especially in extensions) can use this to introspect what
    #: size thumbnails they should generate.
    use_hd_thumbnails = True

    def __init__(self, attachment, mimetype):
        """Initialize the handler.

        Args:
            attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment being handled.

            mimetype (unicode):
                The mimetype for the file attachment.
        """
        self.attachment = attachment
        self.mimetype = mimetype
        self.storage = staticfiles_storage

    @classmethod
    def get_best_handler(cls, mimetype):
        """Return the handler and score that that best fit the mimetype.

        Args:
            mimetype (unicode):
                The mimetype to find the best handler for.

        Returns:
            tuple:
            A tuple of ``(best_score, mimetype_handler)``. If no handler
            was found, this will be ``(0, None)``.
        """
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
        """Return the handler that is the best fit for provided mimetype.

        Args:
            attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment to find the best handler for.

        Returns:
            MimetypeHandler:
            The best mimetype handler for the attachment, or ``None`` if
            one could not be found.
        """
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
                              attachment, e)

        return MimetypeHandler(attachment, mimetype)

    def get_icon_url(self):
        """Return the appropriate icon URL for this mimetype.

        Returns:
            unicode:
            The URL to an icon representing this mimetype.
        """
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
        """Return HTML that represents a preview of the attachment.

        Subclasses can override this to provide a suitable thumbnail. The
        outer element of the thumbnail should have a ``file-thumbnail`` CSS
        class.

        By default, this returns an empty thumbnail.

        Returns:
            django.utils.safestring.SafeText:
            The HTML for the thumbnail for the associated attachment.
        """
        return mark_safe('<pre class="file-thumbnail"></pre>')

    def set_thumbnail(self):
        """Set the thumbnail data for this attachment.

        This should be implemented by subclasses if they need the thumbnail to
        be generated client-side.
        """
        raise NotImplementedError

    def _get_mimetype_file(self, name):
        return '%s/%s.png' % (self.MIMETYPES_DIR, name)


class ImageMimetype(MimetypeHandler):
    """Handles image mimetypes."""

    supported_mimetypes = ['image/*']

    def get_thumbnail(self):
        """Return a thumbnail of the image.

        Returns:
            django.utils.safestring.SafeText:
            The HTML for the thumbnail for the associated attachment.
        """
        return format_html(
            '<div class="file-thumbnail">'
            ' <img src="{src_1x}" srcset="{src_1x} 1x, {src_2x} 2x"'
            ' alt="{caption}" width="300" />'
            '</div>',
            src_1x=thumbnail(self.attachment.file, (300, None)),
            src_2x=thumbnail(self.attachment.file, (600, None)),
            caption=self.attachment.caption)


class TextMimetype(MimetypeHandler):
    """Handles text mimetypes.

    Text mimetypes provide thumbnails containing the first few lines of the
    file, syntax-highlighted.
    """

    supported_mimetypes = ['text/*']

    # Read up to 'FILE_CROP_CHAR_LIMIT' number of characters from
    # the file attachment to prevent long reads caused by malicious
    # or auto-generated files.
    FILE_CROP_CHAR_LIMIT = 1000
    TEXT_CROP_NUM_HEIGHT = 50

    def _generate_preview_html(self, data):
        """Return the first few truncated lines of the text file.

        Args:
            data (bytes):
                The contents of the attachment.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML-safe thumbnail content.
        """
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

        return format_html_join(
            '',
            '<pre>{0}</pre>',
            (
                (mark_safe(line),)
                for line in lines[:self.TEXT_CROP_NUM_HEIGHT]
            ))

    def _generate_thumbnail(self):
        """Return the HTML for a thumbnail preview for a text file.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML-safe thumbnail content.
        """
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

        return format_html(
            '<div class="file-thumbnail">'
            ' <div class="file-thumbnail-clipped">{0}</div>'
            '</div>',
            self._generate_preview_html(data))

    def get_thumbnail(self):
        """Return the thumbnail of the text file as rendered as html.

        The content will be generated and then cached for future requests.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML-safe thumbnail content.
        """
        # Caches the generated thumbnail to eliminate the need on each page
        # reload to:
        # 1) re-read the file attachment
        # 2) re-generate the html based on the data read
        return mark_safe(
            cache_memoize('file-attachment-thumbnail-%s-html-%s'
                          % (self.__class__.__name__, self.attachment.pk),
                          self._generate_thumbnail))


class ReStructuredTextMimetype(TextMimetype):
    """Handles ReStructuredText (.rst) mimetypes.

    ReST mimetypes provide thumbnails containing the first few lines of
    rendered content from the file.
    """

    supported_mimetypes = ['text/x-rst', 'text/rst']

    def _generate_preview_html(self, data_string):
        """Return the HTML for a thumbnail preview for a ReST file.

        Args:
            data_string (bytes):
                The contents of the file.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML-safe thumbnail content.
        """
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

        return mark_safe(parts['html_body'])


class MarkDownMimetype(TextMimetype):
    """Handle MarkDown (.md) mimetypes.

    Markdown mimetypes provide thumbnails containing the first few lines of
    rendered content from the file.
    """

    supported_mimetypes = ['text/x-markdown', 'text/markdown']

    def _generate_preview_html(self, data_string):
        """Return the HTML for a thumbnail preview for a Markdown file.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML-safe thumbnail content.
        """
        return mark_safe(render_markdown(force_unicode(data_string)))


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
