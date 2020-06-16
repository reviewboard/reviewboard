# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from django.utils.six.moves.urllib.parse import quote
from django.utils.translation import ugettext as _

from reviewboard.scmtools.core import HEAD
from reviewboard.scmtools.errors import SCMError


class Client(object):
    """Base SVN client."""

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
        """Metadata about the repository.

        This is a dictionary containing the following keys:

        ``uuid`` (:py:class:`unicode`):
            The UUID of the repository.

        ``root_url`` (:py:class:`unicode`):
            The root URL of the configured repository.

        ``url`` (:py:class:`unicoe`):
            The full URL of the configured repository.
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
        mangled. There are many characters Subversion does consider valid that
        would normally be quoted, so this isn't true URL quoting.

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
            # Some important notes for the quoting below:
            #
            # 1) Subversion requires that we operate off of a URI-based
            #    repository path in order for file lookups to at all work, so
            #    we can be sure we're building a URI here. That means we're
            #    safe to quote.
            #
            # 2) This is largely being mentioned because the original
            #    contribution to fix a lookup issue here with special
            #    characters was written to be compatible with local file
            #    paths. Support for that is a pretty common assumption, but
            #    is unnecessary, so the code here is safe.
            #
            # 3) We can't rely on urllib's standard quoting behavior.
            #    completely. Subversion has a specific table of characters
            #    that must be quoted, and ones that can't be. There is enough
            #    we can leverage from urlquote's own table, but we need to
            #    mark several more as safe.
            #
            #    See the "svn_uri_char_validity" look up table and notes here:
            #
            #    https://github.com/apache/subversion/blob/trunk/subversion/libsvn_subr/path.c
            #
            # 4) file:// URLs don't allow non-printable characters (character
            #    codes < 32), while non-file:// URLs do. We don't want to
            #    trigger issues in Subversion (earlier versions assume this
            #    is our responsibility), so we validate here.
            #
            # 5) Modern Subversion seems to handle its own normalization now,
            #    from what we can tell. That might not always be true, though,
            #    and we need to support older versions, so we'll continue to
            #    maintain this going forward.
            if self.repopath.startswith('file:'):
                # Validate that this doesn't have any unprintable ASCII
                # characters or older versions of Subversion will throw a
                # fit.
                for c in path:
                    if 0 <= ord(c) < 32:
                        raise SCMError(
                            _('Invalid character code %(code)s found in '
                              'path %(path)r.')
                            % {
                                'code': ord(c),
                                'path': path,
                            })

            norm_path = '%s/%s' % (
                self.repopath,
                quote(path.lstrip('/'), safe="!$&'()*+,'-./:=@_~")
            )

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
