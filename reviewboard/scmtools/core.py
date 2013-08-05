import base64
import logging
import os
import subprocess
import sys
import urllib2
import urlparse

import reviewboard.diffviewer.parser as diffparser
from reviewboard.scmtools.errors import AuthenticationError, \
                                        FileNotFoundError, \
                                        SCMError
from reviewboard.ssh import utils as sshutils
from reviewboard.ssh.errors import SSHAuthenticationError


class ChangeSet:
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


class Revision(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == str(other)

    def __ne__(self, other):
        return self.name != str(other)

    def __repr__(self):
        return '<Revision: %s>' % self.name


HEAD = Revision("HEAD")
UNKNOWN = Revision('UNKNOWN')
PRE_CREATION = Revision("PRE-CREATION")


class SCMTool(object):
    name = None
    uses_atomic_revisions = False
    supports_authentication = False
    supports_raw_file_urls = False
    supports_ticket_auth = False
    field_help_text = {
        'path': 'The path to the repository. This will generally be the URL '
                'you would use to check out the repository.',
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

    def get_file(self, path, revision=None):
        raise NotImplementedError

    def file_exists(self, path, revision=HEAD):
        try:
            self.get_file(path, revision)
            return True
        except FileNotFoundError:
            return False

    def parse_diff_revision(self, file_str, revision_str, moved=False):
        raise NotImplementedError

    def get_diffs_use_absolute_paths(self):
        return False

    def get_changeset(self, changesetid, allow_empty=False):
        raise NotImplementedError

    def get_pending_changesets(self, userid):
        raise NotImplementedError

    def get_filenames_in_revision(self, revision):
        raise NotImplementedError

    def get_repository_info(self):
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
            env['RB_LOCAL_SITE'] = local_site_name

        env['PYTHONPATH'] = ':'.join(sys.path)

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
                "%s: Attempting ssh connection with host: %s, username: %s" % \
                (cls.__name__, hostname, username))

            try:
                sshutils.check_host(hostname, username, password,
                                    local_site_name)
            except SSHAuthenticationError, e:
                # Represent an SSHAuthenticationError as a standard
                # AuthenticationError.
                raise AuthenticationError(e.allowed_types, unicode(e),
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
        url = urlparse.urlparse(path)

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
    def accept_certificate(cls, path, local_site_name=None, certificate=None):
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
            request = urllib2.Request(url)

            if self.username:
                auth_string = base64.b64encode('%s:%s' % (self.username,
                                                          self.password))
                request.add_header('Authorization', 'Basic %s' % auth_string)

            return urllib2.urlopen(request).read()
        except urllib2.HTTPError, e:
            if e.code == 404:
                logging.error('404')
                raise FileNotFoundError(path, revision)
            else:
                msg = "HTTP error code %d when fetching file from %s: %s" % \
                      (e.code, url, e)
                logging.error(msg)
                raise SCMError(msg)
        except Exception, e:
            msg = "Unexpected error fetching file from %s: %s" % (url, e)
            logging.error(msg)
            raise SCMError(msg)
