"""PySVN client backend for Subversion."""

import logging
import os
from collections import OrderedDict
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

from django.utils.encoding import force_bytes, force_str
from django.utils.translation import gettext as _

from reviewboard.scmtools.core import HEAD, PRE_CREATION
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.scmtools.svn import base, SVNTool
from reviewboard.scmtools.svn.utils import (collapse_svn_keywords,
                                            has_expanded_svn_keywords)


logger = logging.getLogger(__name__)


class Client(base.Client):
    """PySVN-based Subversion client backend.

    This provides Subversion compatibility through the well-maintained
    `PySVN <https://pysvn.sourceforge.io/>`_ library.
    """

    required_module = 'pysvn'

    def __init__(self, config_dir, repopath, username=None, password=None):
        """Initialize the client.

        Args:
            config_dir (str):
                The path to the Subversion configuration directory.

            repopath (str):
                The path to the repository.

            username (str, optional):
                The username for the repository.

            password (str, optional):
                The password for the repository.
        """
        super(Client, self).__init__(config_dir, repopath, username, password)
        self.client = pysvn.Client(config_dir)

        if username:
            self.client.set_default_username(str(username))

        if password:
            self.client.set_default_password(password)

    def set_ssl_server_trust_prompt(self, cb):
        """Set a function for verifying a SSL certificate.

        Args:
            cb (callable):
                The function to call for verifying SSL certificates.
        """
        self.client.callback_ssl_server_trust_prompt = cb

    def ssl_trust_prompt(self, trust_dict):
        if hasattr(self, 'callback_ssl_server_trust_prompt'):
            return self.callback_ssl_server_trust_prompt(trust_dict)

    def _do_on_path(self, cb, path, revision=HEAD):
        """Perform an operation on a given path.

        This will normalize the provided path and revision and then call the
        given function with those normalized values. The error will be
        normalized and any errors converted into useful exceptions.

        Args:
            cb (callable):
                The function to call.

            path (str):
                The repository path to provide to the callback.

            revision (str):
                The revision to provide to the callback.

        Returns:
            object:
            The value from the callback.

        Raises:
            reviewboard.scmtools.errors.AuthenticationError:
                There was an error authenticating with the repository.

            reviewboard.scmtools.errors.FileNotFoundError:
                The path was empty or could not be found in the repository.

            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` argument was in an invalid format.

            reviewboard.scmtools.errors.SCMError:
                There was an error communicating with the repository.
        """
        if not path:
            raise FileNotFoundError(path, revision)

        try:
            normpath = self.normalize_path(path)
            normrev = self._normalize_revision(revision)
            return cb(normpath, normrev)

        except ClientError as e:
            exc = force_str(e)

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
        """Return the contents of a file from the server.

        If the contents have expanded keywords, they'll be collapsed.

        Args:
            normpath (str):
                The normalized path in the repository.

            normrev (str):
                The normalized revision in the repository.

        Returns:
            bytes:
            The contents of the file.
        """
        data = self.client.cat(normpath, normrev)

        if has_expanded_svn_keywords(data):
            # Find out if this file has any keyword expansion set.
            # If it does, collapse these keywords. This is because SVN
            # will return the file expanded to us, which would break patching.
            keywords = self.client.propget('svn:keywords', normpath, normrev,
                                           recurse=True)

            if normpath in keywords:
                data = collapse_svn_keywords(data,
                                             force_bytes(keywords[normpath]))

        return data

    def get_file(self, path, revision=HEAD):
        """Return the contents of a file from the repository.

        This attempts to return the raw binary contents of a file from the
        repository, given a file path and revision.

        Args:
            path (str):
                The path to the file in the repository.

            revision (reviewboard.scmtools.core.Revision, optional):
                The revision to fetch. Subclasses should default this to
                :py:data:`HEAD`.

            *args (tuple, unused):
                Additional unused positional arguments.

            **kwargs (dict, unused):
                Additional unused keyword arguments.

        Returns:
            bytes:
            The returned file contents.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found in the repository.

            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` argument was in an invalid format.

            reviewboard.scmtools.errors.SCMError:
                An unexpected error was encountered with the repository.
        """
        return self._do_on_path(self._get_file_data, path, revision)

    def _get_file_keywords(self, normpath, normrev):
        """Return the space-separated list of keywords for a file path.

        Args:
            normpath (str):
                The normalized path within the repository.

            normrev (str):
                The normalized path within the repository.

        Returns:
            str:
            The keywords for the file path.
        """
        keywords = self.client.propget("svn:keywords", normpath, normrev,
                                       recurse=True)
        return keywords.get(normpath)

    def get_keywords(self, path, revision=HEAD):
        """Return a space-separated list of SVN keywords for a given path.

        Args:
            path (str):
                The path to the file or directory.

            revision (str):
                The revision containing the keywords.

        Returns:
            str:
            The resulting keywords.
        """
        return self._do_on_path(self._get_file_keywords, path, revision)

    def _normalize_revision(self, revision):
        """Return a normalized revision for PySVN.

        Args:
            revision (str or reviewboard.scmtools.core.Revision):
                The revision to normalize.

        Returns:
            pysvn.Revision:
            The normalized revision.
        """
        if revision == HEAD:
            r = Revision(opt_revision_kind.head)
        elif revision == PRE_CREATION:
            raise FileNotFoundError('', revision)
        else:
            r = Revision(opt_revision_kind.number, str(revision))

        return r

    @property
    def repository_info(self):
        """Metadata about the repository.

        This is a dictionary containing the following keys:

        Keys:
            uuid (str):
                The UUID of the repository.

            root_url (str):
                The root URL of the configured repository.

            url (str):
                The full URL of the configured repository.

        Type:
            dict
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
        """Attempt to accept a SSL certificate.

        If the repository uses SSL, this method is used to determine whether
        the SSL certificate can be automatically accepted.

        If the cert cannot be accepted, the ``on_failure`` callback
        is executed.

        Args:
            path (str):
                The repository path.

            on_failure (callable, optional):
                A function to call if the certificate could not be accepted.

        Returns:
            dict:
            Serialized information on the certificate.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                There was an error accepting the certificate.
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
            logger.debug('SVN: Got repository information for %s: %s',
                         path, info)
        except ClientError as e:
            if on_failure:
                on_failure(e, path, cert)

        return cert

    def get_log(self, path, start=None, end=None, limit=None,
                discover_changed_paths=False, limit_to_path=False):
        """Return log entries at the specified path.

        The log entries will appear ordered from most recent to least,
        with ``start`` being the most recent commit in the range.

        Args:
            path (str):
                The path to limit log entries to.

            start (str, optional):
                The start revision for the log.

                If not specified, clients must default this to "HEAD".

            end (str, optional):
                The end revision for the log.

                If not specified, clients must default this to "1".

            limit (int, optional):
                The maximum number of entries to return.

            discover_changed_paths (bool, optional):
                Whether to include information on changed paths in the
                results.

            limit_to_path (bool, optional):
                Limits results to ``path`` without factoring in history from
                any branch operations.

        Returns:
            list of SVNLogEntry:
            The list of resulting log entries.
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
            commit['revision'] = str(commit['revision'].number)

            if 'date' in commit:
                commit['date'] = datetime.utcfromtimestamp(commit['date'])

        return commits

    def list_dir(self, path):
        """Return the directory contents of the specified path.

        The result will be an ordered dictionary of contents, mapping
        filenames or directory names with directory information.

        Args:
            path (str):
                The directory path.

        Returns:
            collections.OrderedDict:
            A dictionary mapping directory names as strings to
            :py:class:`SVNDirEntry` information.
        """
        result = OrderedDict()
        norm_path = self.normalize_path(path)
        dirents = self.client.list(norm_path, recurse=False)[1:]

        repo_path_len = len(self.repopath)

        for dirent, unused in dirents:
            name = dirent['path'].split('/')[-1]

            result[name] = {
                'path': dirent['path'][repo_path_len:],
                'created_rev': str(dirent['created_rev'].number),
            }

        return result

    def diff(self, revision1, revision2, path=None):
        """Return a diff between two revisions.

        The diff will contain the differences between the two revisions,
        and may optionally be limited to a specific path.

        Args:
            revision1 (str):
                The first revision in the range.

            revision2 (str):
                The second revision in the range.

            path (str, optional):
                An optional path to limit the diff to.

        Returns:
            bytes:
            The resulting diff contents.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error was encountered with the repository.

                This may be a more specific subclass.
        """
        if path:
            path = self.normalize_path(path)
        else:
            path = self.repopath

        tmpdir = mkdtemp(prefix='reviewboard-svn.')

        try:
            diff = force_bytes(self.client.diff(
                tmpdir,
                path,
                revision1=self._normalize_revision(revision1),
                revision2=self._normalize_revision(revision2),
                header_encoding='UTF-8',
                diff_options=['-u']))
        except Exception as e:
            logger.error('Failed to generate diff using pysvn for revisions '
                         '%s:%s for path %s: %s',
                         revision1, revision2, path, e, exc_info=True)
            raise SCMError(
                _('Unable to get diff revisions %s through %s: %s')
                % (revision1, revision2, e))
        finally:
            rmtree(tmpdir)

        return diff
