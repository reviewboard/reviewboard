import re

from django import template
from django.conf import settings
from django.template import NodeList
from django.template.loader import render_to_string
from djblets.util.decorators import blocktag

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
    return extraWhitespace.sub(r'<span class="ew">\1</span>', value);
showextrawhitespace.is_safe = True
