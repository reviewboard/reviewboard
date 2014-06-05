# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import os
from datetime import datetime
from shutil import rmtree
from tempfile import mkdtemp

try:
    import pysvn
    from pysvn import (ClientError, Revision, opt_revision_kind,
                       SVN_DIRENT_CREATED_REV)
    imported_dependency = True
except ImportError:
    # This try-except block is here for the sole purpose of avoiding
    # exceptions with nose if pysvn isn't installed when someone runs
    # the testsuite.
    imported_dependency = False

from django.core.cache import cache
from django.utils import six
from django.utils.datastructures import SortedDict
from django.utils.six.moves.urllib.parse import (urlsplit, urlunsplit, quote)
from django.utils.translation import ugettext as _

from reviewboard.scmtools.core import (Branch, Commit,
                                       HEAD, PRE_CREATION)
from reviewboard.scmtools.errors import (AuthenticationError,
                                         FileNotFoundError,
                                         SCMError)
from reviewboard.scmtools.svn import base


class Client(base.Client):
    required_module = 'pysvn'

    def __init__(self, config_dir, repopath, username=None, password=None):
        super(Client, self).__init__(config_dir, repopath, username, password)
        self.client = pysvn.Client(config_dir)

        if username:
            self.client.set_default_username(six.text_type(username))

        if password:
            self.client.set_default_password(six.text_type(password))

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

            normrev = self.__normalize_revision(revision)
            return cb(normpath, normrev)

        except ClientError as e:
            stre = six.text_type(e)
            if 'File not found' in stre or 'path not found' in stre:
                raise FileNotFoundError(path, revision,
                                        detail=six.text_type(e))
            elif 'callback_ssl_server_trust_prompt required' in stre:
                raise SCMError(
                    _('HTTPS certificate not accepted.  Please ensure that '
                      'the proper certificate exists in %s '
                      'for the user that reviewboard is running as.')
                    % os.path.join(self.config_dir, 'auth'))
            elif 'callback_get_login required' in stre:
                raise AuthenticationError(
                    msg=_('Login to the SCM server failed.'))
            else:
                raise SCMError(e)

    @property
    def branches(self):
        """Returns a list of branches.

        This assumes the standard layout in the repository."""
        results = []

        try:
            root_dirents = self.client.list(
                self.normalize_path('/'),
                dirent_fields=SVN_DIRENT_CREATED_REV,
                recurse=False)[1:]
        except ClientError as e:
            raise SCMError(e)

        root_entries = SortedDict()
        for dirent, unused in root_dirents:
            name = dirent['path'].split('/')[-1]
            rev = six.text_type(dirent['created_rev'].number)
            root_entries[name] = rev

        if 'trunk' in root_entries:
            # Looks like the standard layout. Adds trunks and any branches
            results.append(
                Branch('trunk', root_entries['trunk'], True))

            try:
                branches = self.client.list(
                    self.normalize_path('branches'),
                    dirent_fields=SVN_DIRENT_CREATED_REV)[1:]
                for branch, unused in branches:
                    results.append(Branch(
                        branch['path'].split('/')[-1],
                        six.text_type(branch['created_rev'].number)))
            except ClientError:
                # It's possible there aren't any branches. Ignore errors for
                # this part.
                pass
        else:
            # If the repository doesn't use the standard layout, just use a
            # listing of the root directory as the "branches". This probably
            # corresponds to a list of projects instead of branches, but it
            # will at least give people a useful result.
            default = True
            for name, rev in six.iteritems(root_entries):
                results.append(Branch(name, rev, default))
                default = False

        return results

    def get_commits(self, start):
        """Returns a list of commits."""
        commits = self.client.log(
            self.repopath,
            revision_start=Revision(opt_revision_kind.number,
                                    int(start)),
            limit=31)

        results = []

        # We fetch one more commit than we care about, because the entries in
        # the svn log doesn't include the parent revision.
        for i in range(len(commits) - 1):
            commit = commits[i]
            parent = commits[i + 1]

            date = datetime.utcfromtimestamp(commit['date'])
            results.append(Commit(
                commit.get('author', ''),
                six.text_type(commit['revision'].number),
                date.isoformat(),
                commit['message'],
                six.text_type(parent['revision'].number)))

        # If there were fewer than 31 commits fetched, also include the last
        # one in the list so we don't leave off the initial revision.
        if len(commits) < 31:
            commit = commits[-1]
            date = datetime.utcfromtimestamp(commit['date'])
            results.append(Commit(
                commit['author'],
                six.text_type(commit['revision'].number),
                date.isoformat(),
                commit['message']))

        return results

    def get_change(self, revision, cache_key):
        """Get an individual change.

        This returns a tuple with the commit message and the diff contents.
        """
        revision = int(revision)
        head_revision = Revision(opt_revision_kind.number, revision)

        commit = cache.get(cache_key)
        if commit:
            message = commit.message
            author_name = commit.author_name
            date = commit.date
            base_revision = Revision(opt_revision_kind.number, commit.parent)
        else:
            commits = self.client.log(
                self.repopath,
                revision_start=head_revision,
                limit=2)
            commit = commits[0]
            message = commit['message'].decode('utf-8', 'replace')
            author_name = commit['author'].decode('utf-8', 'replace')
            date = datetime.utcfromtimestamp(commit['date']).\
                isoformat()

            try:
                commit = commits[1]
                base_revision = commit['revision']
            except IndexError:
                base_revision = Revision(opt_revision_kind.number, 0)

        tmpdir = mkdtemp(prefix='reviewboard-svn.')

        diff = self.client.diff(
            tmpdir,
            self.repopath,
            revision1=base_revision,
            revision2=head_revision,
            header_encoding='utf-8',
            diff_options=['-u']).decode('utf-8')

        rmtree(tmpdir)

        commit = Commit(author_name, six.text_type(head_revision.number), date,
                        message, six.text_type(base_revision.number))
        commit.diff = diff
        return commit

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

    def get_filenames_in_revision(self, revision):
        """Returns a list of filenames associated with the revision."""
        r = self.__normalize_revision(revision)
        logs = self.client.log(self.repopath, r, r, True)

        if len(logs) == 0:
            return []
        elif len(logs) == 1:
            return [f['path'] for f in logs[0]['changed_paths']]
        else:
            assert False

    def __normalize_revision(self, revision):
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
            raise SCMError(e)

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
