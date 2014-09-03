from __future__ import unicode_literals

import markdown
from django import template
from django.utils import six
from django.utils.safestring import mark_safe
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from reviewboard.reviews.markdown_utils import markdown_unescape


register = template.Library()


class InlineStyleProcessor(Treeprocessor):
    def process_element(self, context, el):
        # This adds a handful of inline styles to the resulting document which
        # mimic the .rich-text rules in reviews.less. This does not do quite
        # everything that the reviews.less rules do, because implementing CSS
        # selectors in python is pretty gross to begin with, and even then
        # we're at the mercy of whatever the e-mail client is going to do. The
        # end result is that the e-mail will look similar but not identical to
        # the page.
        style = {
            'margin': 0,
            'padding': 0,
            'line-height': 'inherit',
            'text-rendering': 'inherit',
            'white-space': 'normal',
        }
        tag = el.tag

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            style['font-size'] = '100%'

        if tag == 'ul':
            style['margin'] = '0 0 0 1em'
        elif tag == 'ol':
            style['margin'] = '0 0 0 2em'
        elif tag == 'code':
            style['color'] = '#4444cc'
        elif tag == 'p':
            style['white-space'] = 'inherit'
        elif tag == 'blockquote':
            style.update({
                'border-left': '1px solid #bbb',
                'padding': '0 0 0 1em',
                'margin': '0 0 0 0.5em',
            })
        elif tag == 'hr':
            style['border'] = '1px solid #ddd'
        elif tag in ('th', 'td'):
            style.update({
                'border-bottom': '1px solid #bbb',
                'padding': '0.2em 1em',
            })

        # Create a valid CSS string and set it as the style attribute
        el.set('style', ''.join([
            '%s: %s;' % (k, v)
            for k, v in six.iteritems(style)
        ]))

        # Recurse into children
        context.append(tag)
        for child in el:
            self.process_element(context, child)
        context.pop()

    def run(self, root):
        # We don't just process the root element, because if we add any style
        # characteristics to it, markdown can't strip off the top-level <div>
        # tag. Why it doesn't use the element tree to do the stripping is
        # beyond me.
        for child in root:
            self.process_element([], child)


class InlineStyleExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.treeprocessors.add('inlinestyle', InlineStyleProcessor(), '_end')


@register.filter
def markdown_email_html(text, is_rich_text):
    if not is_rich_text:
        return text

    marked = markdown.markdown(
        text,
        extensions=['fenced_code', 'codehilite(noclasses=True)', 'tables',
                    InlineStyleExtension()],
        output_format='xhtml1',
        safe_mode='escape')
    return mark_safe(marked)


@register.filter
def markdown_email_text(text, is_rich_text):
    if not is_rich_text:
        return text

    return markdown_unescape(text)
