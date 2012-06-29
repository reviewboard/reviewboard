import mimeparse
import os

from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.html import escape
from django.utils.safestring import mark_safe
from djblets.util.templatetags.djblets_images import crop_image, thumbnail
from pipeline.storage import default_storage


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
        best_score, best_fit = (0, cls)

        for mt in cls.supported_mimetypes:
            try:
                score = score_match(mimeparse.parse_mime_type(mt), mimetype)

                if score > best_score:
                    best_score, best_fit = (score, cls)
            except ValueError:
                continue

        for handler in cls.__subclasses__():
            score, best_handler = handler.get_best_handler(mimetype)

            if score > best_score:
                best_score, best_fit = (score, best_handler)

        return (best_score, best_fit)

    @classmethod
    def for_type(cls, attachment):
        """Returns the handler that is the best fit for provided mimetype."""
        mimetype = mimeparse.parse_mime_type(attachment.mimetype)
        score, handler = cls.get_best_handler(mimetype)
        return handler(attachment, mimetype)

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

    def _get_mimetype_file(self, name):
        return '%s/%s.png' % (self.MIMETYPES_DIR, name)


class ImageMimetype(MimetypeHandler):
    """Handles image mimetypes."""
    supported_mimetypes = ['image/*']

    def get_thumbnail(self):
        """Returns a thumbnail of the image."""
        return mark_safe('<img src="%s" class="file-thumbnail" alt="%s" />'
                         % (thumbnail(self.attachment.file),
                            self.attachment.caption))


class TextMimetype(MimetypeHandler):
    """Handles text mimetypes."""
    supported_mimetypes = ['text/*']

    def get_thumbnail(self):
        """Returns the first few truncated lines of the file."""
        height = 4
        length = 50

        f = self.attachment.file.file
        preview = escape(f.readline()[:length])
        for i in range(height - 1):
            preview = preview + '<br />' + escape(f.readline()[:length])
        f.close()

        return mark_safe('<pre class="file-thumbnail">%s</pre>'
                         % preview)


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
