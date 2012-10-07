import re

from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from djblets.util.decorators import basictag

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
                             '<code>%s</code>' % header['text'],
                             _('Expand to header'),
                             (lines_of_context[0],
                              expand_offset + lines_of_context[1]),
                             'rb/images/diff-expand-header.png')
