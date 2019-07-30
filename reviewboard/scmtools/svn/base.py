# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from reviewboard.scmtools.core import HEAD


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
