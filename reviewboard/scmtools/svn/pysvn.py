# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import os
from datetime import datetime
from shutil import rmtree
from tempfile import mkdtemp

try:
    import pysvn
    from pysvn import ClientError, Revision, opt_revision_kind
    has_svn_backend = True
except ImportError:
    # This try-except block is here for the sole purpose of avoiding
    # exceptions with nose if pysvn isn't installed when someone runs
    # the testsuite.
    has_svn_backend = False

from django.utils import six
from django.utils.datastructures import SortedDict
from django.utils.six.moves.urllib.parse import (urlsplit, urlunsplit, quote)
from django.utils.translation import ugettext as _

from reviewboard.scmtools.core import HEAD, PRE_CREATION
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.scmtools.svn import base, SVNTool


class Client(base.Client):
    required_module = 'pysvn'

    def __init__(self, config_dir, repopath, username=None, password=None):
        super(Client, self).__init__(config_dir, repopath, username, password)
        self.client = pysvn.Client(config_dir)

        if username:
            self.client.set_default_username(six.text_type(username))

        if password:
            self.client.set_default_password(password)

    def set_ssl_server_trust_prompt(self, cb):
        self.client.callback_ssl_server_trust_prompt = cb

    def ssl_trust_prompt(self, trust_dict):
        if hasattr(self, 'callback_ssl_server_trust_prompt'):
            return self.callback_ssl_server_trust_prompt(trust_dict)

    def _do_on_path(self, cb, path, revision=HEAD):
        if not path:
            raise FileNotFoundError(path, revision)

        try:
            normpath = self.normalize_path(path)

            # SVN expects to have URLs escaped. Take care to only
            # escape the path part of the URL.
            if self.client.is_url(normpath):
                pathtuple = urlsplit(normpath)
                path = pathtuple[2]
                if isinstance(path, six.text_type):
                    path = path.encode('utf-8', 'ignore')
                normpath = urlunsplit((pathtuple[0],
                                       pathtuple[1],
                                       quote(path),
                                       '', ''))

            normrev = self._normalize_revision(revision)
            return cb(normpath, normrev)

        except ClientError as e:
            exc = bytes(e).decode('utf-8')
            if 'File not found' in exc or 'path not found' in exc:
                raise FileNotFoundError(path, revision, detail=exc)
            elif 'callback_ssl_server_trust_prompt required' in exc:
                raise SCMError(
                    _('HTTPS certificate not accepted.  Please ensure that '
                      'the proper certificate exists in %s '
                      'for the user that reviewboard is running as.')
                    % os.path.join(self.config_dir, 'auth'))
            else:
                raise SVNTool.normalize_error(e)

    def _get_file_data(self, normpath, normrev):
        data = self.client.cat(normpath, normrev)

        # Find out if this file has any keyword expansion set.
        # If it does, collapse these keywords. This is because SVN
        # will return the file expanded to us, which would break patching.
        keywords = self.client.propget("svn:keywords", normpath, normrev,
                                       recurse=True)
        if normpath in keywords:
            data = self.collapse_keywords(data, keywords[normpath])

        return data

    def get_file(self, path, revision=HEAD):
        """Returns the contents of a given file at the given revision."""
        return self._do_on_path(self._get_file_data, path, revision)

    def _get_file_keywords(self, normpath, normrev):
        keywords = self.client.propget("svn:keywords", normpath, normrev,
                                       recurse=True)
        return keywords.get(normpath)

    def get_keywords(self, path, revision=HEAD):
        """Returns a list of SVN keywords for a given path."""
        return self._do_on_path(self._get_file_keywords, path, revision)

    def _normalize_revision(self, revision):
        if revision == HEAD:
            r = Revision(opt_revision_kind.head)
        elif revision == PRE_CREATION:
            raise FileNotFoundError('', revision)
        else:
            r = Revision(opt_revision_kind.number, six.text_type(revision))

        return r

    @property
    def repository_info(self):
        """Returns metadata about the repository:

        * UUID
        * Root URL
        * URL
        """
        try:
            info = self.client.info2(self.repopath, recurse=False)
        except ClientError as e:
            raise SVNTool.normalize_error(e)

        return {
            'uuid': info[0][1].repos_UUID,
            'root_url': info[0][1].repos_root_URL,
            'url': info[0][1].URL
        }

    def accept_ssl_certificate(self, path, on_failure=None):
        """If the repository uses SSL, this method is used to determine whether
        the SSL certificate can be automatically accepted.

        If the cert cannot be accepted, the ``on_failure`` callback
        is executed.

        ``on_failure`` signature::

            void on_failure(e:Exception, path:str, cert:dict)
        """
        cert = {}

        def ssl_server_trust_prompt(trust_dict):
            cert.update(trust_dict.copy())

            if on_failure:
                return False, 0, False
            else:
                del cert['failures']
                return True, trust_dict['failures'], True

        self.client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt

        try:
            info = self.client.info2(path, recurse=False)
            logging.debug('SVN: Got repository information for %s: %s' %
                          (path, info))
        except ClientError as e:
            if on_failure:
                on_failure(e, path, cert)

        return cert

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
        if start is None:
            start = self.LOG_DEFAULT_START

        if end is None:
            end = self.LOG_DEFAULT_END

        commits = self.client.log(
            self.normalize_path(path),
            limit=limit,
            revision_start=self._normalize_revision(start),
            revision_end=self._normalize_revision(end),
            discover_changed_paths=discover_changed_paths,
            strict_node_history=limit_to_path)

        for commit in commits:
            commit['revision'] = six.text_type(commit['revision'].number)

            if 'date' in commit:
                commit['date'] = datetime.utcfromtimestamp(commit['date'])

        return commits

    def list_dir(self, path):
        """Lists the contents of the specified path.

        The result will be an ordered dictionary of contents, mapping
        filenames or directory names with a dictionary containing:

        * ``path``        - The full path of the file or directory.
        * ``created_rev`` - The revision where the file or directory was
                            created.
        """
        result = SortedDict()
        norm_path = self.normalize_path(path)
        dirents = self.client.list(norm_path, recurse=False)[1:]

        repo_path_len = len(self.repopath)

        for dirent, unused in dirents:
            name = dirent['path'].split('/')[-1]

            result[name] = {
                'path': dirent['path'][repo_path_len:],
                'created_rev': six.text_type(dirent['created_rev'].number),
            }

        return result

    def diff(self, revision1, revision2, path=None):
        """Returns a diff between two revisions.

        The diff will contain the differences between the two revisions,
        and may optionally be limited to a specific path.

        The returned diff will be returned as a Unicode object.
        """
        if path:
            path = self.normalize_path(path)
        else:
            path = self.repopath

        tmpdir = mkdtemp(prefix='reviewboard-svn.')

        try:
            diff = self.client.diff(
                tmpdir,
                path,
                revision1=self._normalize_revision(revision1),
                revision2=self._normalize_revision(revision2),
                header_encoding='UTF-8',
                diff_options=['-u'])
        except Exception as e:
            logging.error('Failed to generate diff using pysvn for revisions '
                          '%s:%s for path %s: %s',
                          revision1, revision2, path, e, exc_info=1)
            raise SCMError(
                _('Unable to get diff revisions %s through %s: %s')
                % (revision1, revision2, e))
        finally:
            rmtree(tmpdir)

        return diff
