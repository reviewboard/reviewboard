"""Common utility functions for working with Subversion."""

from __future__ import unicode_literals

import re


AUTHOR_KEYWORDS = [b'author', b'lastchangedby']
DATE_KEYWORDS = [b'date', b'lastchangeddate']
REVISION_KEYWORDS = [b'revision', b'lastchangedrevision', b'rev']
URL_KEYWORDS = [b'headurl', b'url']
ID_KEYWORDS = [b'id']
HEADER_KEYWORDS = [b'header']


# Mapping of keywords to known aliases
keyword_aliases = {
    # Standard keywords
    b'author': AUTHOR_KEYWORDS,
    b'date': DATE_KEYWORDS,
    b'header': HEADER_KEYWORDS,
    b'headurl': URL_KEYWORDS,
    b'id': ID_KEYWORDS,
    b'revision': REVISION_KEYWORDS,

    # Aliases
    b'lastchangedby': AUTHOR_KEYWORDS,
    b'lastchangeddate': DATE_KEYWORDS,
    b'lastchangedrevision': REVISION_KEYWORDS,
    b'rev': REVISION_KEYWORDS,
    b'url': URL_KEYWORDS,
}


def has_expanded_svn_keywords(data):
    """Return whether file data appears to have expanded SVN keywords.

    This can be used to determine whether it's worth fetching information from
    a Subversion repository to expand file data.

    Args:
        data (bytes):
            The file content.

    Returns:
        bool:
        ``True`` if the data appears to have SVN keywords. ``False`` if it
        does not.
    """
    assert isinstance(data, bytes), (
        'data must be a byte string, not %s' % type(data))

    return bool(re.search(br'\$[A-Za-z0-9]+::?\s+([^\$\s]+)[^\$]*\$',
                          data))


def collapse_svn_keywords(data, keyword_str):
    """Collapse SVN keywords in string.

    SVN allows for several keywords (such as ``$Id$`` and ``$Revision$``) to be
    expanded, though these keywords are limited to a fixed set (and associated
    aliases) and must be enabled per-file.

    Keywords can take two forms: ``$Keyword$`` and ``$Keyword::     $``.
    The latter allows the field to take a fixed size when expanded.

    When we cat a file on SVN, the keywords come back expanded, which isn't
    good for us as we need to diff against the collapsed version. This
    function makes that transformation.

    Args:
        data (bytes):
            The file content.

        keyword_str (bytes):
            One or more keywords, separated by spaces.

    Returns:
        bytes:
        The file content with keywords collapsed.
    """
    def repl(m):
        if m.group(2):
            return b'$%s::%s$' % (m.group(1), b' ' * len(m.group(3)))

        return b'$%s$' % m.group(1)

    assert isinstance(data, bytes), (
        'data must be a byte string, not %s' % type(data))
    assert isinstance(keyword_str, bytes), (
        'keyword_str must be a byte string, not %s' % type(keyword_str))

    # Get any aliased keywords
    keywords = [
        re.escape(keyword)
        for name in re.split(br'\W+', keyword_str)
        for keyword in keyword_aliases.get(name.lower(), [])
    ]

    return re.sub(br'\$(%s):(:?)([^\$\n\r]*)\$' % b'|'.join(keywords),
                  repl, data, flags=re.IGNORECASE)
