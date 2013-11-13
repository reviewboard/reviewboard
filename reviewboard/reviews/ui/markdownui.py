from __future__ import unicode_literals

import logging
from xml.dom.minidom import parseString

from djblets.cache.backend import cache_memoize
from djblets.util.compat.six.moves import cStringIO as StringIO
import markdown

from reviewboard.reviews.ui.base import FileAttachmentReviewUI


class MarkdownReviewUI(FileAttachmentReviewUI):
    """A Review UI for markdown files.

    This renders the markdown to HTML, and allows users to comment on each
    top-level block (header, paragraph, list, code block, etc).
    """
    supported_mimetypes = ['text/x-markdown']
    object_key = 'markdown'

    js_model_class = 'RB.MarkdownReviewable'
    js_view_class = 'RB.MarkdownReviewableView'

    def get_js_model_data(self):
        """Fetch extra data to be passed to the js_model_class"""
        return {
            'fileAttachmentID': self.obj.id,
            'rendered': self.render(),
        }

    def render(self):
        """Render the document."""
        return cache_memoize('markdown-attachment-%d' % self.obj.pk,
                             self._render)

    def _render(self):
        buffer = StringIO()
        self.obj.file.open()
        markdown.markdownFromFile(input=self.obj.file, output=buffer,
                                  output_format='xhtml1', safe_mode='escape')
        rendered = buffer.getvalue()
        buffer.close()

        return rendered

    def serialize_comments(self, comments):
        """Get a dictionary of the comments for this file attachment"""
        result = {}

        for comment in comments:
            result.setdefault(comment.extra_data['child_id'], []).append(
                self.serialize_comment(comment))

        return result

    def _get_thumbnail(self, child_id):
        try:
            document = parseString('<html>%s</html>' % self.render())
            child_node = document.childNodes[0].childNodes[child_id]
            return child_node.toxml()
        except Exception as e:
            logging.warning("Failure to create comment thumbnail for markdown "
                            "file attachment pk=%d: %s" % (self.obj.pk, e))
            return ''

    def get_comment_thumbnail(self, comment):
        """Get the "thumbnail" for a comment.

        This extracts the relevant paragraph that was commented on and returns
        it as HTML to be included in the list of reviews.
        """
        try:
            child_id = int(comment.extra_data['child_id'])
        except (KeyError, ValueError):
            # This may be a comment from before we had review UIs. Or,
            # corrupted data. Either way, we don't display anything.
            return None

        return cache_memoize(
            'markdown-attachment-comment-thumbnail-%d-%d' % (self.obj.pk,
                                                             child_id),
            lambda: self._get_thumbnail(child_id))
