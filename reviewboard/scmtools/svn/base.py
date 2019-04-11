# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from reviewboard.scmtools.core import HEAD


class Client(object):
    """Base SVN client."""

    AUTHOR_KEYWORDS = [b'author', b'lastchangedby']
    DATE_KEYWORDS = [b'date', b'lastchangeddate']
    REVISION_KEYWORDS = [b'revision', b'lastchangedrevision', b'rev']
    URL_KEYWORDS = [b'headurl', b'url']
    ID_KEYWORDS = [b'id']
    HEADER_KEYWORDS = [b'header']

    LOG_DEFAULT_START = 'HEAD'
    LOG_DEFAULT_END = '1'

    # Mapping of keywords to known aliases
    keywords = {
        # Standard keywords
        b'author': AUTHOR_KEYWORDS,
        b'date': DATE_KEYWORDS,
        b'revision': REVISION_KEYWORDS,
        b'headURL': URL_KEYWORDS,
        b'id': ID_KEYWORDS,
        b'header': HEADER_KEYWORDS,

        # Aliases
        b'lastchangedby': AUTHOR_KEYWORDS,
        b'lastchangeddate': DATE_KEYWORDS,
        b'lastchangedrevision': REVISION_KEYWORDS,
        b'rev': REVISION_KEYWORDS,
        b'url': URL_KEYWORDS,
    }

    def __init__(self, config_dir, repopath, username=None, password=None):
        self.repopath = repopath

    def set_ssl_server_trust_prompt(self, cb):
        raise NotImplementedError

    def get_file(self, path, revision=HEAD):
        """Returns the contents of a given file at the given revision."""
        raise NotImplementedError

    def get_keywords(self, path, revision=HEAD):
        """Returns a list of SVN keywords for a given path."""
        raise NotImplementedError

    def get_log(self, path, start=None, end=None, limit=None,
                discover_changed_paths=False, limit_to_path=False):
        """Returns log entries at the specified path.

        The log entries will appear ordered from most recent to least,
        with 'start' being the most recent commit in the range.

        If 'start' is not specified, then it will default to 'HEAD'. If
        'end' is not specified, it will default to '1'.

        To limit the commits to the given path, not factoring in history
        from any branch operations, set 'limit_to_path' to True.
        """
        raise NotImplementedError

    def list_dir(self, path):
        """Lists the contents of the specified path.

        The result will be an ordered dictionary of contents, mapping
        filenames or directory names with a dictionary containing:

        * ``path``        - The full path of the file or directory.
        * ``created_rev`` - The revision where the file or directory was
                            created.
        """
        raise NotImplementedError

    def diff(self, revision1, revision2, path=None):
        """Returns a diff between two revisions.

        The diff will contain the differences between the two revisions,
        and may optionally be limited to a specific path.

        The returned diff will be returned as a Unicode object.
        """
        raise NotImplementedError

    def collapse_keywords(self, data, keyword_str):
        """Collapse SVN keywords in string.

        SVN allows for several keywords (such as ``$Id$`` and ``$Revision$``)
        to be expanded, though these keywords are limited to a fixed set
        (and associated aliases) and must be enabled per-file.

        Keywords can take two forms: ``$Keyword$`` and ``$Keyword::     $``
        The latter allows the field to take a fixed size when expanded.

        When we cat a file on SVN, the keywords come back expanded, which
        isn't good for us as we need to diff against the collapsed version.
        This function makes that transformation.

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
            'data must be a byte string, not %r' % type(data))
        assert isinstance(keyword_str, bytes), (
            'keyword_str must be a byte string, not %r' % type(data))

        # Get any aliased keywords
        keywords = [
            re.escape(keyword)
            for name in re.split(br'\W+', keyword_str)
            for keyword in self.keywords.get(name.lower(), [])
        ]

        return re.sub(br'\$(%s):(:?)([^\$\n\r]*)\$' % b'|'.join(keywords),
                      repl, data, flags=re.IGNORECASE)

    @property
    def repository_info(self):
        """Returns metadata about the repository:

        * UUID
        * Root URL
        * URL
        """
        raise NotImplementedError

    def normalize_path(self, path):
        if path.startswith(self.repopath):
            norm_path = path
        elif path.startswith('//'):
            norm_path = self.repopath + path[1:]
        elif path[0] == '/':
            norm_path = self.repopath + path
        else:
            norm_path = '%s/%s' % (self.repopath, path)

        return norm_path.rstrip('/')

    def accept_ssl_certificate(self, path, on_failure=None):
        """If the repository uses SSL, this method is used to determine whether
        the SSL certificate can be automatically accepted.

        If the cert cannot be accepted, the ``on_failure`` callback
        is executed.

        ``on_failure`` signature::

            void on_failure(e:Exception, path:str, cert:dict)
        """
        raise NotImplementedError
