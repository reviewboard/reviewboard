import re

from django import template
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from djblets.util.decorators import basictag

from reviewboard.diffviewer.chunk_generator import DiffChunkGenerator


register = template.Library()


@register.filter
def revision_link_list(history, current_pair):
    """
    Returns a list of revisions in the specified diffset history, indicating
    which of the revisions is already selected, as determined by the current
    diffset pair.
    """
    for diffset in history.diffsets.all():
        yield {
            'revision': diffset.revision,
            'is_current': current_pair[0] == diffset and
                          current_pair[1] == None
        }


@register.filter
def interdiff_link_list(history, current_pair):
    """
    Returns a list of revisions in the specified diffset history based on
    the passed interdiff pair.
    """
    for diffset in history.diffsets.all():
        if current_pair[0].revision < diffset.revision:
            path = "%s-%s" % (current_pair[0].revision, diffset.revision)
        else:
            path = "%s-%s" % (diffset.revision, current_pair[0].revision)

        yield {
            'revision': diffset.revision,
            'path': path,
            'is_current': current_pair[0] == diffset or
                          current_pair[1] == diffset
        }


@register.filter
def highlightregion(value, regions):
    """
    Highlights the specified regions of text.

    This is used to insert ``<span class="hl">...</span>`` tags in the
    text as specified by the ``regions`` variable.
    """
    if not regions:
        return value

    s = ""

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
    in_tag = in_entity = in_hl = False
    i = j = r = 0
    region = regions[r]

    for i in xrange(len(value)):
        if value[i] == "<":
            in_tag = True

            if in_hl:
                s += "</span>"
                in_hl = False
        elif value[i] == ">":
            in_tag = False
        elif value[i] == ';' and in_entity:
            in_entity = False
            j += 1
        elif not in_tag and not in_entity:
            if not in_hl and region[0] <= j < region[1]:
                s += '<span class="hl">'
                in_hl = True

            if value[i] == '&':
                in_entity = True
            else:
                j += 1

        s += value[i]

        if j == region[1]:
            r += 1

            if in_hl:
                s += '</span>'
                in_hl = False

            if r == len(regions):
                break

            region = regions[r]

    if i + 1 < len(value):
        s += value[i + 1:]

    return s
highlightregion.is_safe = True


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
                      expand_pos, image, image_alt='[+]',
                      image_width=14, image_height=14):
    """Utility function to render a diff expansion link.

    This is used internally by other template tags to provide a diff
    expansion link. It assumes nothing about the content and serves only
    to render the data from a template.
    """
    return render_to_string('diffviewer/expand_link.html', {
        'tooltip': tooltip,
        'text': text,
        'base_url': context['base_url'],
        'chunk': context['chunk'],
        'file': context['file'],
        'expand_pos': expand_pos,
        'image': image,
        'image_width': image_width,
        'image_height': image_height,
        'image_alt': image_alt,
        'expandable': expandable,
    })

@register.tag
@basictag(takes_context=True)
def diff_expand_link(context, expanding, tooltip,
                     expand_pos_1=None, expand_pos_2=None, text=None):
    """Renders a diff expansion link.

    This link will expand the diff entirely, or incrementally in one
    or more directions.

    'expanding' is expected to be one of 'all', 'above', or 'below'.
    """
    if expanding == 'all':
        image = 'rb/images/diff-expand-all.png'
        expand_pos = None
        image_alt = '[20]'
        image_width = 14
    else:
        lines_of_context = context['lines_of_context']
        expand_pos = (lines_of_context[0] + expand_pos_1,
                      lines_of_context[1] + expand_pos_2)
        image = 'rb/images/diff-expand-%s.png' % expanding
        image_width = 28
        image_alt = '[+20]'


    return _diff_expand_link(context, True, text, tooltip, expand_pos,
                             image, image_alt, image_width)

@register.tag
@basictag(takes_context=True)
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
                             'rb/images/diff-expand-header.png')


@register.simple_tag
def diff_lines(file, chunk, standalone, line_fmt, anchor_fmt,
               begin_collapse_fmt, end_collapse_fmt, moved_fmt):
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
    is_equal = (change == 'equal')
    is_replace = (change == 'replace')
    is_insert = (change == 'insert')
    is_delete = (change == 'delete')

    result = []

    for i, line in enumerate(lines):
        class_attr = ''
        line1 = line[2]
        line2 = line[5]
        linenum1 = line[1]
        linenum2 = line[4]
        show_collapse = False
        anchor = None

        if not is_equal:
            classes = ''

            if i == 0:
                classes += 'first '
                anchor = '%s.%s' % (file['index'], chunk_index)

            if i == num_lines - 1:
                classes += 'last '

            if line[7]:
                classes += 'whitespace-line'

            if classes:
                class_attr = ' class="%s"' % classes

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

        if len(line) > 8 and line[8]:
            if is_insert:
                moved_from = {
                    'class': 'moved-from',
                    'line': mark_safe(line[8]),
                    'target': mark_safe(linenum2),
                    'text': _('Moved from %s') % line[8],
                }

            if is_delete:
                moved_to = {
                    'class': 'moved-to',
                    'line': mark_safe(line[8]),
                    'target': mark_safe(linenum1),
                    'text': _('Moved to %s') % line[8],
                }

        anchor_html = ''
        begin_collapse_html = ''
        end_collapse_html = ''
        moved_from_html = ''
        moved_to_html = ''

        context = {
            'chunk_index': chunk_index,
            'class_attr': class_attr,
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
