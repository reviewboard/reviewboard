from __future__ import unicode_literals

import calendar
from datetime import datetime, timedelta
import re
import time

try:
    from bzrlib import bzrdir, revisionspec
    from bzrlib.errors import BzrError, NotBranchError
    from bzrlib.transport import register_lazy_transport
    from bzrlib.transport.remote import RemoteSSHTransport
    from bzrlib.transport.ssh import (SubprocessVendor, register_ssh_vendor,
                                      register_default_ssh_vendor)
    has_bzrlib = True
except ImportError:
    has_bzrlib = False
from django.utils import six

from reviewboard.scmtools.core import SCMTool, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import RepositoryNotFoundError, SCMError
from reviewboard.ssh import utils as sshutils

try:
    import urlparse
    uses_netloc = urlparse.uses_netloc
except ImportError:
    import urllib.parse
    uses_netloc = urllib.parse.uses_netloc

# Register these URI schemes so we can handle them properly.
sshutils.ssh_uri_schemes.append('bzr+ssh')
uses_netloc.extend(['bzr', 'bzr+ssh'])


if has_bzrlib:
    class RBSSHVendor(SubprocessVendor):
        """SSH vendor class that uses rbssh"""
        executable_path = 'rbssh'

        def __init__(self, local_site_name=None, *args, **kwargs):
            super(RBSSHVendor, self).__init__(*args, **kwargs)
            self.local_site_name = local_site_name

        def _get_vendor_specific_argv(self, username, host, port,
                                      subsystem=None, command=None):
            args = [self.executable_path]

            if port is not None:
                args.extend(['-p', six.text_type(port)])

            if username is not None:
                args.extend(['-l', username])

            if self.local_site_name:
                args.extend(['--rb-local-site', self.local_site_name])

            if subsystem is not None:
                args.extend(['-s', host, subsystem])
            else:
                args.extend([host] + command)

            return args

    class RBRemoteSSHTransport(RemoteSSHTransport):
        LOCAL_SITE_PARAM_RE = \
            re.compile(r'\?rb-local-site-name=([A-Za-z0-9\-_.]+)')

        def __init__(self, base, *args, **kwargs):
            m = self.LOCAL_SITE_PARAM_RE.search(base)

            if m:
                self.local_site_name = m.group(1)
                base = base.replace(m.group(0), '')
            else:
                self.local_site_name = None

            super(RBRemoteSSHTransport, self).__init__(
                base.encode('ascii'), *args, **kwargs)

        def _build_medium(self):
            client_medium, auth = \
                super(RBRemoteSSHTransport, self)._build_medium()
            client_medium._vendor = RBSSHVendor(self.local_site_name)
            return client_medium, auth

    vendor = RBSSHVendor()
    register_ssh_vendor("rbssh", vendor)
    register_default_ssh_vendor(vendor)
    sshutils.register_rbssh('BZR_SSH')
    register_lazy_transport('bzr+ssh://', 'reviewboard.scmtools.bzr',
                            'RBRemoteSSHTransport')


class BZRTool(SCMTool):
    """An interface to the Bazaar SCM (http://bazaar-vcs.org/)"""
    name = "Bazaar"
    dependencies = {
        'modules': ['bzrlib'],
    }

    # Timestamp format in bzr diffs.
    # This isn't totally accurate: there should be a %z at the end.
    # Unfortunately, strptime() doesn't support %z.
    DIFF_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

    # "bzr diff" indicates that a file is new by setting the old
    # timestamp to the epoch time.
    PRE_CREATION_TIMESTAMP = '1970-01-01 00:00:00 +0000'

    def __init__(self, repository):
        SCMTool.__init__(self, repository)

    def get_file(self, path, revision, **kwargs):
        if revision == BZRTool.PRE_CREATION_TIMESTAMP:
            return ''

        revspec = self._revspec_from_revision(revision)
        filepath = self._get_full_path(path)

        branch = None
        try:
            try:
                branch, relpath = bzrdir.BzrDir.open_containing_tree_or_branch(
                    filepath.encode('ascii'))[1:]
                branch.lock_read()
                revtree = revisionspec.RevisionSpec.from_string(
                    revspec.encode('ascii')).as_tree(branch)
                fileid = revtree.path2id(relpath)
                if fileid:
                    # XXX: get_file_text returns str, which isn't Python 3
                    # safe. According to the internet they have no immediate
                    # plans to port to 3, so we may find it hard to support
                    # that combination.
                    contents = bytes(revtree.get_file_text(fileid))
                else:
                    contents = b''
            except BzrError as e:
                raise SCMError(e)
        finally:
            if branch:
                branch.unlock()

        return contents

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        if revision_str == BZRTool.PRE_CREATION_TIMESTAMP:
            return (file_str, PRE_CREATION)

        return file_str, revision_str

    def get_fields(self):
        return ['basedir', 'diff_path', 'parent_diff_path']

    def get_diffs_use_absolute_paths(self):
        return False

    def _get_full_path(self, path, basedir=None):
        """Returns the full path to a file."""
        parts = [self.repository.path.rstrip("/")]

        if basedir:
            parts.append(basedir.strip("/"))

        parts.append(path.strip("/"))

        final_path = "/".join(parts)

        if final_path.startswith("/"):
            final_path = "file://%s" % final_path

        if self.repository.local_site and sshutils.is_ssh_uri(final_path):
            final_path += '?rb-local-site-name=%s' % \
                          self.repository.local_site.name

        return final_path

    def _revspec_from_revision(self, revision):
        """Returns a revspec based on the revision found in the diff.

        In addition to the standard date format from "bzr diff", this function
        supports the revid: syntax provided by the bzr diff-revid plugin.
        """
        if revision == HEAD:
            revspec = 'last:1'
        elif revision.startswith('revid:'):
            revspec = revision
        else:
            revspec = 'date:' + six.text_type(
                self._revision_timestamp_to_local(revision))

        return revspec

    def _revision_timestamp_to_local(self, timestamp_str):
        """Convert a timestamp to local time.

        When using a date to ask bzr for a file revision, it expects the date
        to be in local time. So, this function converts a timestamp from a bzr
        diff file to local time.
        """

        timestamp = datetime(*time.strptime(
            timestamp_str[0:19], BZRTool.DIFF_TIMESTAMP_FORMAT)[0:6])

        # Now, parse the difference to GMT time (such as +0200). If only
        # strptime() supported %z, we wouldn't have to do this manually.
        delta = timedelta(hours=int(timestamp_str[21:23]),
                          minutes=int(timestamp_str[23:25]))
        if timestamp_str[20] == '+':
            timestamp -= delta
        else:
            timestamp += delta

        # convert to local time
        return datetime.utcfromtimestamp(
            calendar.timegm(timestamp.timetuple()))

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None):
        """
        Performs checks on a repository to test its validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        The result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception
        will be thrown.
        """
        super(BZRTool, cls).check_repository(path, username, password,
                                             local_site_name)

        if local_site_name and sshutils.is_ssh_uri(path):
            path += '?rb-local-site-name=%s' % local_site_name

        try:
            tree, branch, repository, relpath = \
                bzrdir.BzrDir.open_containing_tree_branch_or_repository(
                    path.encode('ascii'))
        except AttributeError:
            raise RepositoryNotFoundError()
        except NotBranchError:
            raise RepositoryNotFoundError()
        except Exception as e:
            raise SCMError(e)
