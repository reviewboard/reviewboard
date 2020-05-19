# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from django.utils.six.moves.urllib.parse import quote

from reviewboard.scmtools.core import HEAD


class Client(object):
    '''Base SVN client.'''

    LOG_DEFAULT_START = 'HEAD'
    LOG_DEFAULT_END = '1'

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

    @property
    def repository_info(self):
        """Returns metadata about the repository:

        * UUID
        * Root URL
        * URL
        """
        raise NotImplementedError

    def normalize_path(self, path):
        """Normalize a path to a file/directory for a request to Subversion.

        If the path is an absolute path beginning at the base of the
        repository, it will be returned as-is. Otherwise, it will be appended
        onto the repository path, with any leading ``/`` characters on the
        path removed.

        If appending the path, care will be taken to quote special characters
        like a space, ``#``, or ``?``, in order to ensure that they're not
        mangled. Modern Subversion doesn't really need these to be quoted,
        but it helps with compatibility.

        All trailing ``/`` characters will also be removed.

        Args:
            path (unicode):
                The path to normalize.

        Returns:
            unicode:
            The normalized path.
        """
        if path.startswith(self.repopath):
            norm_path = path
        else:
            # Note that Subversion requires that we operate off of a URI-based
            # repository path in order for file lookups to at all work, so
            # we can be sure we're building a URI here. That means we're safe
            # to quote.
            #
            # This is largely being mentioned because the original contribution
            # to fix a lookup issue here with special characters was written
            # to be compatible with local file paths. Support for that is a
            # pretty common assumption, but is unnecessary, so the code here is
            # safe.
            #
            # Note also that modern Subversion seems to not require special
            # characters to be escaped, but we seem to have had to at one
            # point in the past, so we will continue to for compatibility.
            norm_path = '%s/%s' % (self.repopath, quote(path.lstrip('/')))

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
