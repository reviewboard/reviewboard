from __future__ import unicode_literals

import re

from django import template
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from reviewboard.diffviewer.chunk_generator import DiffChunkGenerator


register = template.Library()


@register.filter
def highlightregion(value, regions):
    """Highlights the specified regions of text.

    This is used to insert ``<span class="hl">...</span>`` tags in the
    text as specified by the ``regions`` variable.
    """
    if not regions:
        return value

    html = []

    # We need to insert span tags into a string already consisting
    # of span tags. We have a list of ranges that our span tags should
    # go into, but those ranges are in the markup-less string.
    #
    # We go through the string and keep track of the location in the
    # markup and in the markup-less string. We make sure to insert our
    # span tag any time that we're within the current region, so long
    # as we haven't already created one. We close the span tag whenever
    # we're done with the region or when we're about to enter a tag in
    # the markup string.
    #
    # This code makes the assumption that the list of regions is sorted.
    # This is safe to assume in practice, but if we ever at some point
    # had reason to doubt it, we could always sort the regions up-front.
    in_hl = False
    i = j = r = 0
    region_start, region_end = regions[r]

    while i < len(value):
        c = value[i]

        if c == '<':
            if in_hl:
                html.append('</span>')
                in_hl = False

            k = value.find('>', i)
            assert k != -1

            html.append(value[i:k + 1])
            i = k
        else:
            if not in_hl and region_start <= j < region_end:
                html.append('<span class="hl">')
                in_hl = True

            if c == '&':
                k = value.find(';', i)
                assert k != -1

                html.append(value[i:k + 1])
                i = k
                j += 1
            else:
                j += 1
                html.append(c)

        if j == region_end:
            if in_hl:
                html.append('</span>')
                in_hl = False

            r += 1

            if r == len(regions):
                break

            region_start, region_end = regions[r]

        i += 1

    if i + 1 < len(value):
        html.append(value[i + 1:])

    return mark_safe(''.join(html))


extraWhitespace = re.compile(r'(\s+(</span>)?$| +\t)')


@register.filter
def showextrawhitespace(value):
    """
    Marks up any extra whitespace in the specified text.

    Any trailing whitespace or tabs following one or more spaces are
    marked up by inserted ``<span class="ew">...</span>`` tags.
    """
    value = extraWhitespace.sub(r'<span class="ew">\1</span>', value)
    return value.replace("\t", '<span class="tb">\t</span>')

showextrawhitespace.is_safe = True


def _diff_expand_link(context, expandable, text, tooltip,
                      expand_pos, image_class):
    """Utility function to render a diff expansion link.

    This is used internally by other template tags to provide a diff
    expansion link. It assumes nothing about the content and serves only
    to render the data from a template.
    """
    return render_to_string('diffviewer/expand_link.html', {
        'tooltip': tooltip,
        'text': text,
        'chunk': context['chunk'],
        'file': context['file'],
        'expand_pos': expand_pos,
        'image_class': image_class,
        'expandable': expandable,
    })


@register.simple_tag(takes_context=True)
def diff_expand_link(context, expanding, tooltip,
                     expand_pos_1=None, expand_pos_2=None, text=None):
    """Renders a diff expansion link.

    This link will expand the diff entirely, or incrementally in one
    or more directions.

    'expanding' is expected to be one of 'all', 'above', or 'below'.
    """
    if expanding == 'all':
        image_class = 'rb-icon-diff-expand-all'
        expand_pos = None
    else:
        lines_of_context = context['lines_of_context']
        expand_pos = (lines_of_context[0] + expand_pos_1,
                      lines_of_context[1] + expand_pos_2)
        image_class = 'rb-icon-diff-expand-%s' % expanding

    return _diff_expand_link(context, True, text, tooltip, expand_pos,
                             image_class)


@register.simple_tag(takes_context=True)
def diff_chunk_header(context, header):
    """Renders a diff header as HTML.

    This diff header may be expandable, depending on whether or not the
    function/class referenced in the header is contained within the collapsed
    region.
    """
    lines_of_context = context['lines_of_context']
    chunk = context['chunk']

    line = chunk['lines'][0]

    if header['line'] >= line[1]:
        expand_offset = line[1] + chunk['numlines'] - header['line']
        expandable = True
    else:
        expand_offset = 0
        expandable = False

    return _diff_expand_link(context, expandable,
                             '<code>%s</code>' % escape(header['text']),
                             _('Expand to header'),
                             (lines_of_context[0],
                              expand_offset + lines_of_context[1]),
                             'rb-icon-diff-expand-header')


@register.simple_tag
def diff_lines(index, chunk, standalone, line_fmt, anchor_fmt='',
               begin_collapse_fmt='', end_collapse_fmt='', moved_fmt=''):
    """Renders the lines of a diff.

    This will render each line in the diff viewer. The function expects
    some basic data on what will be rendered, as well as printf-formatted
    templates for the contents.

    printf-formatted templates are used instead of standard Django templates
    because they're much faster to render, which makes a huge difference
    when rendering thousands of lines or more.
    """
    lines = chunk['lines']
    num_lines = len(lines)
    chunk_index = chunk['index']
    change = chunk['change']
    is_equal = False
    is_replace = False
    is_insert = False
    is_delete = False

    if change == 'equal':
        is_equal = True
    elif change == 'replace':
        is_replace = True
    elif change == 'insert':
        is_insert = True
    elif change == 'delete':
        is_delete = True

    result = []

    for i, line in enumerate(lines):
        row_classes = []
        header_1_classes = []
        header_2_classes = []
        cell_1_classes = ['l']
        cell_2_classes = ['r']
        row_class_attr = ''
        header_1_class_attr = ''
        header_2_class_attr = ''
        cell_1_class_attr = ''
        cell_2_class_attr = ''
        line1 = line[2]
        line2 = line[5]
        linenum1 = line[1]
        linenum2 = line[4]
        show_collapse = False
        anchor = None

        if i == 0:
            row_classes.append('first')

        if i == num_lines - 1:
            row_classes.append('last')

        if not is_equal:
            if i == 0:
                anchor = '%s.%s' % (index, chunk_index)

            if line[7]:
                row_classes.append('whitespace-line')

            if is_replace:
                if len(line1) < DiffChunkGenerator.STYLED_MAX_LINE_LEN:
                    line1 = highlightregion(line1, line[3])

                if len(line2) < DiffChunkGenerator.STYLED_MAX_LINE_LEN:
                    line2 = highlightregion(line2, line[6])
        else:
            show_collapse = (i == 0 and standalone)

        if (not is_insert and
                len(line1) < DiffChunkGenerator.STYLED_MAX_LINE_LEN):
            line1 = showextrawhitespace(line1)

        if (not is_delete and
                len(line2) < DiffChunkGenerator.STYLED_MAX_LINE_LEN):
            line2 = showextrawhitespace(line2)

        moved_from = {}
        moved_to = {}
        is_moved_row = False
        is_first_moved_row = False

        if len(line) > 8 and isinstance(line[8], dict):
            moved_info = line[8]

            if 'from' in moved_info:
                moved_from_linenum, moved_from_first = moved_info['from']
                is_moved_row = True

                header_2_classes.append('moved-from')
                cell_2_classes.append('moved-from')

                if moved_from_first:
                    # This is the start of a new move range.
                    is_first_moved_row = True
                    header_2_classes.append('moved-from-start')
                    cell_2_classes.append('moved-from-start')
                    moved_from = {
                        'class': 'moved-flag',
                        'line': mark_safe('moved-from-%s'
                                          % moved_from_linenum),
                        'target': mark_safe('moved-to-%s' % linenum2),
                        'text': _('Moved from line %s') % moved_from_linenum,
                    }

            if 'to' in moved_info:
                moved_to_linenum, moved_to_first = moved_info['to']
                is_moved_row = True

                header_1_classes.append('moved-to')
                cell_1_classes.append('moved-to')

                if moved_to_first:
                    # This is the start of a new move range.
                    is_first_moved_row = True
                    header_1_classes.append('moved-to-start')
                    cell_1_classes.append('moved-to-start')
                    moved_to = {
                        'class': 'moved-flag',
                        'line': mark_safe('moved-to-%s' % moved_to_linenum),
                        'target': mark_safe('moved-from-%s' % linenum1),
                        'text': _('Moved to line %s') % moved_to_linenum,
                    }

        if is_moved_row:
            row_classes.append('moved-row')

        if is_first_moved_row:
            row_classes.append('moved-row-start')

        if row_classes:
            row_class_attr = ' class="%s"' % ' '.join(row_classes)

        if cell_1_classes:
            cell_1_class_attr = ' class="%s"' % ' '.join(cell_1_classes)

        if cell_2_classes:
            cell_2_class_attr = ' class="%s"' % ' '.join(cell_2_classes)

        if header_1_classes:
            header_1_class_attr = ' class="%s"' % ' '.join(header_1_classes)

        if header_2_classes:
            header_2_class_attr = ' class="%s"' % ' '.join(header_2_classes)

        anchor_html = ''
        begin_collapse_html = ''
        end_collapse_html = ''
        moved_from_html = ''
        moved_to_html = ''

        context = {
            'chunk_index': chunk_index,
            'row_class_attr': row_class_attr,
            'header_1_class_attr': header_1_class_attr,
            'header_2_class_attr': header_2_class_attr,
            'cell_1_class_attr': cell_1_class_attr,
            'cell_2_class_attr': cell_2_class_attr,
            'linenum_row': line[0],
            'linenum1': linenum1,
            'linenum2': linenum2,
            'line1': line1,
            'line2': line2,
            'moved_from': moved_from,
            'moved_to': moved_to,
        }

        if anchor:
            anchor_html = anchor_fmt % {
                'anchor': anchor,
            }

        if show_collapse:
            begin_collapse_html = begin_collapse_fmt % context
            end_collapse_html = end_collapse_fmt % context

        if moved_from:
            moved_from_html = moved_fmt % moved_from

        if moved_to:
            moved_to_html = moved_fmt % moved_to

        context.update({
            'anchor_html': anchor_html,
            'begin_collapse_html': begin_collapse_html,
            'end_collapse_html': end_collapse_html,
            'moved_from_html': moved_from_html,
            'moved_to_html': moved_to_html,
        })

        result.append(line_fmt % context)

    return ''.join(result)
