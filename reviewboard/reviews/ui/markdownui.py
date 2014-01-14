from __future__ import unicode_literals

import logging
from xml.dom.minidom import parseString

from djblets.util.compat.six.moves import cStringIO as StringIO
import markdown

from reviewboard.reviews.ui.text import TextBasedReviewUI


class MarkdownReviewUI(TextBasedReviewUI):
    """A Review UI for markdown files.

    This renders the markdown to HTML, and allows users to comment on each
    top-level block (header, paragraph, list, code block, etc).
    """
    supported_mimetypes = ['text/x-markdown']
    object_key = 'markdown'
    can_render_text = True

    extra_css_classes = ['markdown-review-ui']

    js_view_class = 'RB.MarkdownReviewableView'

    def generate_render(self):
        buffer = StringIO()
        self.obj.file.open()
        markdown.markdownFromFile(input=self.obj.file, output=buffer,
                                  output_format='xhtml1', safe_mode='escape',
                                  extensions=['fenced_code', 'codehilite'])
        rendered = buffer.getvalue()
        buffer.close()
        self.obj.file.close()

        try:
            doc = parseString('<html>%s</html>' % rendered)
            main_node = doc.childNodes[0]

            for node in main_node.childNodes:
                for html in self._process_markdown_html(node):
                    yield html
        except Exception as e:
            logging.error('Failed to parse resulting Markdown XHTML for '
                          'file attachment %d: %s' % (self.obj.pk, e))

    def _process_markdown_html(self, node):
        if (node.nodeType == node.ELEMENT_NODE and
            node.tagName == 'div' and
            node.attributes.get('class', 'codehilite')):
            for line in node.toxml().splitlines():
                yield '<pre>%s</pre>' % line
        else:
            yield node.toxml()
