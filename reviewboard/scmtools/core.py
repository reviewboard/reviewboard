from __future__ import unicode_literals

import base64
import inspect
import logging
import os
import subprocess
import sys
import warnings

from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.six.moves.urllib.request import (Request as URLRequest,
                                                   urlopen)
from django.utils.translation import ugettext_lazy as _

import reviewboard.diffviewer.parser as diffparser
from reviewboard.scmtools.errors import (AuthenticationError,
                                         FileNotFoundError,
                                         SCMError)
from reviewboard.ssh import utils as sshutils
from reviewboard.ssh.errors import SSHAuthenticationError


class ChangeSet(object):
    def __init__(self):
        self.changenum = None
        self.summary = ""
        self.description = ""
        self.testing_done = ""
        self.branch = ""
        self.bugs_closed = []
        self.files = []
        self.username = ""
        self.pending = False


@python_2_unicode_compatible
class Revision(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == six.text_type(other)

    def __ne__(self, other):
        return self.name != six.text_type(other)

    def __repr__(self):
        return '<Revision: %s>' % self.name


class Branch(object):
    def __init__(self, id, name=None, commit='', default=False):
        assert id

        self.id = id
        self.name = name or self.id
        self.commit = commit
        self.default = default

    def __eq__(self, other):
        return (self.id == other.id and
                self.name == other.name and
                self.commit == other.commit and
                self.default == other.default)

    def __repr__(self):
        return ('<Branch %s (name=%s; commit=%s: default=%r)>'
                % (self.id, self.name, self.commit, self.default))


class Commit(object):
    def __init__(self, author_name='', id='', date='', message='', parent='',
                 diff=None, base_commit_id=None):
        self.author_name = author_name
        self.id = id
        self.date = date
        self.message = message
        self.parent = parent
        self.base_commit_id = base_commit_id

        # This field is only used when we're actually fetching the commit from
        # the server to create a new review request, and isn't part of the
        # equality test.
        self.diff = diff

    def __eq__(self, other):
        return (self.author_name == other.author_name and
                self.id == other.id and
                self.date == other.date and
                self.message == other.message and
                self.parent == other.parent)

    def __repr__(self):
        return ('<Commit %r (author=%s; date=%s; parent=%r)>'
                % (self.id, self.author_name, self.date, self.parent))

    def split_message(self):
        """Get a split version of the commit message.

        This will return a tuple of (summary, message). If the commit message
        is only a single line, both will be that line.
        """
        message = self.message
        parts = message.split('\n', 1)
        summary = parts[0]
        try:
            message = parts[1]
        except IndexError:
            # If the description is only one line long, pass through--'message'
            # will still be set to what we got from get_change, and will show
            # up as being the same thing as the summary.
            pass

        return summary, message


HEAD = Revision("HEAD")
UNKNOWN = Revision('UNKNOWN')
PRE_CREATION = Revision("PRE-CREATION")


class SCMTool(object):
    name = None
    supports_pending_changesets = False
    supports_post_commit = False
    supports_raw_file_urls = False
    supports_ticket_auth = False
    field_help_text = {
        'path': _('The path to the repository. This will generally be the URL '
                  'you would use to check out the repository.'),
    }

    # A list of dependencies for this SCMTool. This should be overridden
    # by subclasses. Python module names go in dependencies['modules'] and
    # binary executables go in dependencies['executables'] (but without
    # a path or file extension, such as .exe).
    dependencies = {
        'executables': [],
        'modules': [],
    }

    def __init__(self, repository):
        self.repository = repository

    def get_file(self, path, revision=None, base_commit_id=None,
                 **kwargs):
        raise NotImplementedError

    def file_exists(self, path, revision=HEAD, base_commit_id=None,
                    **kwargs):
        argspec = inspect.getargspec(self.get_file)

        try:
            if argspec.keywords is None:
                warnings.warn('SCMTool.get_file() must take keyword '
                              'arguments, signature for %s is deprecated.'
                              % self.name, DeprecationWarning)
                self.get_file(path, revision)
            else:
                self.get_file(path, revision, base_commit_id=base_commit_id)

            return True
        except FileNotFoundError:
            return False

    def parse_diff_revision(self, file_str, revision_str, moved=False,
                            copied=False, **kwargs):
        raise NotImplementedError

    def get_diffs_use_absolute_paths(self):
        return False

    def get_changeset(self, changesetid, allow_empty=False):
        raise NotImplementedError

    def get_repository_info(self):
        raise NotImplementedError

    def get_branches(self):
        """Get a list of all branches in the repositories.

        This should be implemented by subclasses, and is expected to return a
        list of Branch objects. One (and only one) of those objects should have
        the "default" field set to True.
        """
        raise NotImplementedError

    def get_commits(self, branch=None, start=None):
        """Get a list of commits backward in history from a given point.

        This should be implemented by subclasses, and is expected to return a
        list of Commit objects (usually 30, but this is flexible depending on
        the limitations of the APIs provided.

        This can be called multiple times in succession using the "parent"
        field of the last entry as the start parameter in order to paginate
        through the history of commits in the repository.
        """
        raise NotImplementedError

    def get_change(self, revision):
        """Get an individual change.

        This should be implemented by subclasses, and is expected to return a
        Commit object containing the details of the commit.
        """
        raise NotImplementedError

    def get_fields(self):
        # This is kind of a crappy mess in terms of OO design.  Oh well.
        # Return a list of fields which are valid for this tool in the "new
        # review request" page.
        raise NotImplementedError

    def get_parser(self, data):
        return diffparser.DiffParser(data)

    def normalize_path_for_display(self, filename):
        return filename

    def normalize_patch(self, patch, filename, revision):
        """Adjust patch to apply in a given SCM.

        Some SCMs need adjustments in the patch, such as contraction of
        keywords for Subversion."""
        return patch

    @classmethod
    def popen(cls, command, local_site_name=None):
        """Launches an application, capturing output.

        This wraps subprocess.Popen to provide some common parameters and
        to pass environment variables that may be needed by rbssh, if
        indirectly invoked.
        """
        env = os.environ.copy()

        if local_site_name:
            env[b'RB_LOCAL_SITE'] = local_site_name.encode('utf-8')

        env[b'PYTHONPATH'] = (':'.join(sys.path)).encode('utf-8')

        return subprocess.Popen(command,
                                env=env,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                close_fds=(os.name != 'nt'))

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
        if sshutils.is_ssh_uri(path):
            username, hostname = SCMTool.get_auth_from_uri(path, username)
            logging.debug(
                "%s: Attempting ssh connection with host: %s, username: %s"
                % (cls.__name__, hostname, username))

            try:
                sshutils.check_host(hostname, username, password,
                                    local_site_name)
            except SSHAuthenticationError as e:
                # Represent an SSHAuthenticationError as a standard
                # AuthenticationError.
                raise AuthenticationError(e.allowed_types, six.text_type(e),
                                          e.user_key)
            except:
                # Re-raise anything else
                raise

    @classmethod
    def get_auth_from_uri(cls, path, username):
        """
        Returns a 2-tuple of the username and hostname, given the path.

        If a username is implicitly passed via the path (user@host), it
        takes precedence over a passed username.
        """
        url = urlparse(path)

        if '@' in url[1]:
            netloc_username, hostname = url[1].split('@', 1)
        else:
            hostname = url[1]
            netloc_username = None

        if netloc_username:
            return netloc_username, hostname
        else:
            return username, hostname

    @classmethod
    def accept_certificate(cls, path, username=None, password=None,
                           local_site_name=None, certificate=None):
        """Accepts the certificate for the given repository path."""
        raise NotImplementedError


class SCMClient(object):
    """Base class for client classes that interface with an SCM.

    Some SCMTools, rather than calling out to a third-party library, provide
    their own client class that interfaces with a command-line tool or
    HTTP-backed repository.

    While not required, this class contains functionality that may be useful to
    such client classes. In particular, it makes it easier to fetch files from
    an HTTP-backed repository, handling authentication and errors.
    """
    def __init__(self, path, username=None, password=None):
        self.path = path
        self.username = username
        self.password = password

    def get_file_http(self, url, path, revision):
        logging.info('Fetching file from %s' % url)

        try:
            request = URLRequest(url)

            if self.username:
                auth_string = base64.b64encode('%s:%s' % (self.username,
                                                          self.password))
                request.add_header('Authorization', 'Basic %s' % auth_string)

            return urlopen(request).read()
        except HTTPError as e:
            if e.code == 404:
                logging.error('404')
                raise FileNotFoundError(path, revision)
            else:
                msg = "HTTP error code %d when fetching file from %s: %s" % \
                      (e.code, url, e)
                logging.error(msg)
                raise SCMError(msg)
        except Exception as e:
            msg = "Unexpected error fetching file from %s: %s" % (url, e)
            logging.error(msg)
            raise SCMError(msg)
