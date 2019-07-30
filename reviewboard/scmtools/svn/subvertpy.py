# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import logging
import os
from collections import OrderedDict
from datetime import datetime

try:
    from subvertpy import (AUTH_PARAM_DEFAULT_PASSWORD,
                           AUTH_PARAM_DEFAULT_USERNAME,
                           ra,
                           SubversionException,
                           __version__)
    from subvertpy.client import Client as SVNClient, api_version, get_config

    has_svn_backend = (__version__ >= (0, 9, 1))
except ImportError:
    # This try-except block is here for the sole purpose of avoiding
    # exceptions with nose if subvertpy isn't installed when someone runs
    # the testsuite.
    has_svn_backend = False

from django.utils import six
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _

from reviewboard.scmtools.core import Revision, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.scmtools.svn import base, SVNTool
from reviewboard.scmtools.svn.utils import (collapse_svn_keywords,
                                            has_expanded_svn_keywords)



class Client(base.Client):
    """Subvertpy-backed Subversion client."""

    required_module = 'subvertpy'

    def __init__(self, config_dir, repopath, username=None, password=None):
        """Initialize the client.

        Args:
            config_dir (unicode):
                The Subversion configuration directory.

            repopath (unicode):
                The path to the Subversion repository.

            username (unicode, optional):
                The username used to authenticate with the repository.

            password (unicode, optional):
                The password used to authenticate with the repository.
        """
        super(Client, self).__init__(config_dir, repopath, username, password)

        self.repopath = self.repopath
        self.config_dir = config_dir

        self._ssl_trust_prompt_cb = None

        auth_providers = [
            ra.get_simple_provider(),
            ra.get_username_provider(),
        ]

        if repopath.startswith('https:'):
            auth_providers += [
                ra.get_ssl_client_cert_file_provider(),
                ra.get_ssl_client_cert_pw_file_provider(),
                ra.get_ssl_server_trust_file_provider(),
                ra.get_ssl_server_trust_prompt_provider(self.ssl_trust_prompt),
            ]

        self.auth = ra.Auth(auth_providers)
        self.username = None
        self.password = None

        if username:
            self.username = username
            self.auth.set_parameter(AUTH_PARAM_DEFAULT_USERNAME,
                                    self.username)

        if password:
            self.password = password
            self.auth.set_parameter(AUTH_PARAM_DEFAULT_PASSWORD,
                                    self.password)

        cfg = get_config(self.config_dir)
        self.client = SVNClient(cfg, auth=self.auth)

    def set_ssl_server_trust_prompt(self, cb):
        """Set the callback for verifying SSL certificates.

        Args:
            cb (callable):
                The callback used to verify certificates.
        """
        self._ssl_trust_prompt_cb = cb

    def get_file(self, path, revision=HEAD):
        """Return the contents of a given file at the given revision.

        Args:
            path (unicode):
                The path to the file.

            revision (unicode or reviewboard.scmtools.core.Revision, optional):
                The revision of the file to fetch.

        Returns:
            bytes:
            The file contents.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found in the repository.
        """
        if not path:
            raise FileNotFoundError(path, revision)

        revnum = self._normalize_revision(revision)
        path = self.normalize_path(path)
        data = io.BytesIO()

        try:
            self.client.cat(path, data, revnum)
        except SubversionException as e:
            raise FileNotFoundError(e)

        contents = data.getvalue()

        if has_expanded_svn_keywords(contents):
            keywords = self.get_keywords(path, revision)

            if keywords:
                contents = collapse_svn_keywords(contents, keywords)

        return contents

    def get_keywords(self, path, revision=HEAD):
        """Return a list of SVN keywords for a given path.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (unicode or reviewboard.scmtools.core.Revision, optional):
                The revision of the file.

        Returns:
            dict:
            A dictionary of properties. All keys are Unicode strings and all
            values are bytes.
        """
        revnum = self._normalize_revision(revision)
        path = self.normalize_path(path)
        return self.client.propget('svn:keywords', path,
                                   None, revnum).get(path)

    def _normalize_revision(self, revision):
        """Normalize a revision to an integer or byte string.

        Args:
            revision (object):
                The revision to normalize. This can be an integer, byte string,
                Unicode string,
                :py:class:`~reviewboard.scmtools.core.Revision` object, or
                ``None``.

        Returns:
            object:
            The resulting revision. This may be an integer (if providing
            a revision number) or a Unicode string (if using an identifier
            like "HEAD").

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The revision indicates that the file does not yet exist.
        """
        if revision is None:
            return None
        elif revision == HEAD:
            return 'HEAD'
        elif revision == PRE_CREATION:
            raise FileNotFoundError('', revision)
        elif isinstance(revision, Revision):
            revision = int(revision.name)
        elif isinstance(revision, (six.text_type, six.binary_type)):
            revision = int(revision)

        return revision

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
        try:
            base = os.path.basename(self.repopath)
            info = self.client.info(self.repopath, 'HEAD')[base]
        except SubversionException as e:
            raise SVNTool.normalize_error(e)

        return {
            'uuid': force_text(info.repos_uuid),
            'root_url': force_text(info.repos_root_url),
            'url': force_text(info.url),
        }

    def ssl_trust_prompt(self, realm, failures, certinfo, may_save):
        """
        Callback for ``subvertpy.ra.get_ssl_server_trust_prompt_provider``.
        ``may_save`` indicates whether to save the cert info for
        subsequent requests.

        Calls ``callback_ssl_server_trust_prompt`` if it exists.

        :param certinfo: (hostname, fingerprint, valid_from, valid_until,
                          issuer_dname, ascii_cert)
        :return: (accepted_failures, may_save)
        """
        if self._ssl_trust_prompt_cb:
            trust_dict = {
                'realm': realm,
                'failures': failures,
                'hostname': certinfo[0],
                'finger_print': certinfo[1],
                'valid_from': certinfo[2],
                'valid_until': certinfo[3],
                'issuer_dname': certinfo[4],
            }
            return self._ssl_trust_prompt_cb(trust_dict)[1:]
        else:
            return None

    def accept_ssl_certificate(self, path, on_failure=None):
        """If the repository uses SSL, this method is used to determine whether
        the SSL certificate can be automatically accepted.

        If the cert cannot be accepted, the ``on_failure`` callback
        is executed.

        ``on_failure`` signature::

            void on_failure(e:Exception, path:str, cert:dict)
        """
        cert = {}

        def _accept_trust_prompt(realm, failures, certinfo, may_save):
            cert.update({
                'realm': realm,
                'failures': failures,
                'hostname': certinfo[0],
                'finger_print': certinfo[1],
                'valid_from': certinfo[2],
                'valid_until': certinfo[3],
                'issuer_dname': certinfo[4],
            })

            if on_failure:
                return 0, False
            else:
                del cert['failures']
                return failures, True

        auth = ra.Auth([
            ra.get_simple_provider(),
            ra.get_username_provider(),
            ra.get_ssl_client_cert_file_provider(),
            ra.get_ssl_client_cert_pw_file_provider(),
            ra.get_ssl_server_trust_file_provider(),
            ra.get_ssl_server_trust_prompt_provider(_accept_trust_prompt),
        ])

        if self.username:
            auth.set_parameter(AUTH_PARAM_DEFAULT_USERNAME, self.username)

        if self.password:
            auth.set_parameter(AUTH_PARAM_DEFAULT_PASSWORD, self.password)

        cfg = get_config(self.config_dir)
        client = SVNClient(cfg, auth)

        try:
            info = client.info(path)
            logging.debug('SVN: Got repository information for %s: %s' %
                          (path, info))
        except SubversionException as e:
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
        def log_cb(changed_paths, revision, props, has_children):
            commit = {
                'revision': force_text(revision),
            }

            if 'svn:date' in props:
                commit['date'] = \
                    datetime.strptime(props['svn:date'].decode('utf-8'),
                                      '%Y-%m-%dT%H:%M:%S.%fZ')

            if 'svn:author' in props:
                commit['author'] = props['svn:author']

            if 'svn:log' in props:
                commit['message'] = props['svn:log']

            commits.append(commit)

        if start is None:
            start = self.LOG_DEFAULT_START

        if end is None:
            end = self.LOG_DEFAULT_END

        commits = []
        self.client.log(log_cb,
                        paths=self.normalize_path(path),
                        start_rev=self._normalize_revision(start),
                        end_rev=self._normalize_revision(end),
                        limit=limit,
                        discover_changed_paths=discover_changed_paths,
                        strict_node_history=limit_to_path)

        return commits

    def list_dir(self, path):
        """Lists the contents of the specified path.

        The result will be an ordered dictionary of contents, mapping
        filenames or directory names with a dictionary containing:

        * ``path``        - The full path of the file or directory.
        * ``created_rev`` - The revision where the file or directory was
                            created.
        """
        result = OrderedDict()

        if api_version()[:2] >= (1, 5):
            depth = 2  # Immediate files in this path. Only in 1.5+.
        else:
            depth = 0  # This will trigger recurse=False for SVN < 1.5.

        # subvertpy asserts that svn_uri not ends with slash
        norm_path = self.normalize_path(path).rstrip('/')

        dirents = self.client.list(norm_path, None, depth)

        for name, dirent in six.iteritems(dirents):
            if name:
                result[six.text_type(name)] = {
                    'path': '%s/%s' % (path.strip('/'), name),
                    'created_rev': six.text_type(dirent['created_rev']),
                }

        return result

    def diff(self, revision1, revision2):
        """Return a diff between two revisions.

        The diff will contain the differences between the two revisions,
        and may optionally be limited to a specific path.

        Args:
            revision1 (unicode):
                The older revision for the diff.

            revision2 (unicode):
                The newer revision for the diff.

        Returns:
            bytes:
            The resulting diff.
        """
        out = None
        err = None

        try:
            out, err = self.client.diff(self._normalize_revision(revision1),
                                        self._normalize_revision(revision2),
                                        self.repopath,
                                        self.repopath,
                                        diffopts=['-u'])

            diff = out.read()
        except Exception as e:
            logging.error('Failed to generate diff using subvertpy for '
                          'revisions %s:%s for path %s: %s',
                          revision1, revision2, path, e, exc_info=1)
            raise SCMError(
                _('Unable to get diff revisions %s through %s: %s')
                % (revision1, revision2, e))
        finally:
            if out:
                out.close()

            if err:
                err.close()

        return diff
