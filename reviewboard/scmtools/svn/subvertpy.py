# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import os

try:
    from subvertpy import ra, SubversionException
    from subvertpy.client import Client as SVNClient, get_config
    imported_dependency = True
except ImportError:
    # This try-except block is here for the sole purpose of avoiding
    # exceptions with nose if subvertpy isn't installed when someone runs
    # the testsuite.
    imported_dependency = False

from django.core.cache import cache
from django.utils import six

from reviewboard.scmtools.core import (Branch, Commit, Revision,
                                       HEAD, PRE_CREATION)
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         SCMError)
from reviewboard.scmtools.svn import base

B = six.binary_type
DIFF_UNIFIED = [B('-u')]
SVN_AUTHOR = B('svn:author')
SVN_DATE = B('svn:date')
SVN_KEYWORDS = B('svn:keywords')
SVN_LOG = B('svn:log')


class Client(base.Client):
    required_module = 'subvertpy'

    def __init__(self, config_dir, repopath, username=None, password=None):
        super(Client, self).__init__(config_dir, repopath, username, password)
        self.repopath = B(self.repopath)
        self.config_dir = B(config_dir)
        auth_providers = [
            ra.get_simple_provider(),
            ra.get_username_provider(),
        ]
        if repopath.startswith('https:'):
            auth_providers.append(
                ra.get_ssl_server_trust_prompt_provider(self.ssl_trust_prompt))
        self.auth = ra.Auth(auth_providers)
        if username:
            self.auth.set_parameter(B('svn:auth:username'), B(username))
        if password:
            self.auth.set_parameter(B('svn:auth:password'), B(password))
        cfg = get_config(self.config_dir)
        self.client = SVNClient(cfg, auth=self.auth)

    @property
    def ra(self):
        """Lazily creates the ``RemoteAccess`` object so
        ``accept_ssl_certificate`` works properly.
        """
        if not hasattr(self, '_ra'):
            self._ra = ra.RemoteAccess(self.repopath, auth=self.auth)
        return self._ra

    @property
    def branches(self):
        """Returns a list of branches.

        This assumes the standard layout in the repository."""
        results = []
        try:
            root_dirents = \
                self.ra.get_dir(B('.'), -1, ra.DIRENT_CREATED_REV)[0]
        except SubversionException as e:
            raise SCMError(e)

        trunk = B('trunk')
        if trunk in root_dirents:
            # Looks like the standard layout. Adds trunk and any branches.
            created_rev = root_dirents[trunk]['created_rev']
            results.append(Branch('trunk', six.text_type(created_rev), True))

            try:
                dirents = self.ra.get_dir(B('branches'), -1,
                                          ra.DIRENT_CREATED_REV)[0]

                branches = {}
                for name, dirent in six.iteritems(dirents):
                    branches[six.text_type(name)] = six.text_type(
                        dirent['created_rev'])

                for name in sorted(six.iterkeys(branches)):
                    results.append(Branch(name, branches[name]))
            except SubversionException as e:
                pass
        else:
            # If the repository doesn't use the standard layout, just use a
            # listing of the root directory as the "branches". This probably
            # corresponds to a list of projects instead of branches, but it
            # will at least give people a useful result.
            branches = {}
            for name, dirent in six.iteritems(root_dirents):
                branches[six.text_type(name)] = six.text_type(
                    dirent['created_rev'])

            default = True
            for name in sorted(six.iterkeys(branches)):
                results.append(Branch(name, branches[name], default))
                default = False

        return results

    def get_commits(self, start):
        """Returns a list of commits."""
        results = []

        if start.isdigit():
            start = int(start)
        commits = list(self.ra.iter_log(None, start, end=0, limit=31))
        # We fetch one more commit than we care about, because the entries in
        # the svn log doesn't include the parent revision.
        for i, (_, rev, props, _) in enumerate(commits[:-1]):
            parent = commits[i + 1]
            commit = Commit(props[SVN_AUTHOR], six.text_type(rev),
                            # [:-1] to remove the Z
                            props[SVN_DATE][:-1], props[SVN_LOG],
                            six.text_type(parent[1]))
            results.append(commit)
        return results

    def get_change(self, revision, cache_key):
        """Get an individual change.

        This returns a tuple with the commit message and the diff contents.
        """
        revision = int(revision)

        commit = cache.get(cache_key)
        if commit:
            message = commit.message
            author_name = commit.author_name
            date = commit.date
            base_revision = commit.parent
        else:
            commits = list(self.ra.iter_log(None, revision, 0, limit=2))
            rev, props = commits[0][1:3]
            message = props[SVN_LOG]
            author_name = props[SVN_AUTHOR]
            date = props[SVN_DATE]

            if len(commits) > 1:
                base_revision = commits[1][1]
            else:
                base_revision = 0

        try:
            out, err = self.client.diff(int(base_revision), int(revision),
                                        self.repopath, self.repopath,
                                        diffopts=DIFF_UNIFIED)
        except Exception as e:
            raise SCMError(e)

        commit = Commit(author_name, six.text_type(revision), date,
                        message, six.text_type(base_revision))
        commit.diff = out.read()
        return commit

    def get_file(self, path, revision=HEAD):
        """Returns the contents of a given file at the given revision."""
        if not path:
            raise FileNotFoundError(path, revision)
        revnum = self._normalize_revision(revision)
        path = B(self.normalize_path(path))
        data = six.StringIO()
        try:
            self.client.cat(path, data, revnum)
        except SubversionException as e:
            raise FileNotFoundError(e)
        contents = data.getvalue()
        keywords = self.get_keywords(path, revision)
        if keywords:
            contents = self.collapse_keywords(contents, keywords)
        return contents

    def get_keywords(self, path, revision=HEAD):
        """Returns a list of SVN keywords for a given path."""
        revnum = self._normalize_revision(revision, negatives_allowed=False)
        path = self.normalize_path(path)
        return self.client.propget(SVN_KEYWORDS, path, None, revnum).get(path)

    def _normalize_revision(self, revision, negatives_allowed=True):
        if revision == HEAD:
            return B('HEAD')
        elif revision == PRE_CREATION:
            raise FileNotFoundError('', revision)
        elif isinstance(revision, Revision):
            revnum = int(revision.name)
        elif isinstance(revision, (B,) + six.string_types):
            revnum = int(revision)
        return revnum

    def get_filenames_in_revision(self, revision):
        """Returns a list of filenames associated with the revision."""
        paths = {}

        def log_cb(changed_paths, rev, props, has_children=False):
            paths.update(changed_paths)

        revnum = self._normalize_revision(revision)
        self.client.log(log_cb, self.repopath, revnum, revnum, limit=1,
                        discover_changed_paths=True)
        if paths:
            return paths.keys()
        else:
            return []

    @property
    def repository_info(self):
        """Returns metadata about the repository:

        * UUID
        * Root URL
        * URL
        """
        try:
            base = os.path.basename(self.repopath)
            info = self.client.info(self.repopath, 'HEAD')[base]
        except SubversionException as e:
            raise SCMError(e)

        return {
            'uuid': info.repos_uuid,
            'root_url': info.repos_root_url,
            'url': info.url
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
        if hasattr(self, 'callback_ssl_server_trust_prompt'):
            trust_dict = {
                'realm': realm,
                'failures': failures,
                'hostname': certinfo[0],
                'finger_print': certinfo[1],
                'valid_from': certinfo[2],
                'valid_until': certinfo[3],
                'issuer_dname': certinfo[4],
            }
            return self.callback_ssl_server_trust_prompt(trust_dict)[1:]
        else:
            return None

    def _accept_trust_prompt(self, realm, failures, certinfo, may_save):
        """
        Callback for ``subvertpy.ra.get_ssl_server_trust_prompt_provider``.
        ``may_save`` indicates whether to save the cert info for
        subsequent requests.

        USED ONLY FOR ``accept_ssl_certificate``.

        :param certinfo: (hostname, fingerprint, valid_from, valid_until,
                            issuer_dname, ascii_cert)
        :return: (accepted_failures, may_save)
        """
        self._accept_cert.update({
            'realm': realm,
            'failures': failures,
            'hostname': certinfo[0],
            'finger_print': certinfo[1],
            'valid_from': certinfo[2],
            'valid_until': certinfo[3],
            'issuer_dname': certinfo[4],
        })
        if self._accept_on_failure:
            return None
        else:
            return failures, True

    def accept_ssl_certificate(self, path, on_failure=None):
        """If the repository uses SSL, this method is used to determine whether
        the SSL certificate can be automatically accepted.

        If the cert cannot be accepted, the ``on_failure`` callback
        is executed.

        ``on_failure`` signature::

            void on_failure(e:Exception, path:str, cert:dict)
        """
        self._accept_cert = {}
        self._accept_on_failure = on_failure

        auth = ra.Auth([
            ra.get_simple_provider(),
            ra.get_username_provider(),
            ra.get_ssl_server_trust_prompt_provider(self._accept_trust_prompt),
        ])
        cfg = get_config(self.config_dir)
        client = SVNClient(cfg, auth)
        try:
            info = client.info(path)
            logging.debug('SVN: Got repository information for %s: %s' %
                          (path, info))
        except SubversionException as e:
            if on_failure:
                on_failure(e, path, self._accept_cert)
