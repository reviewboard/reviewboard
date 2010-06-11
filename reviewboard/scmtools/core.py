import logging
import os
import urlparse

import reviewboard.diffviewer.parser as diffparser
from reviewboard.scmtools import sshutils
from reviewboard.scmtools.errors import FileNotFoundError


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
    diff_uses_changeset_ids = False
    supports_authentication = False
    supports_raw_file_urls = False

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
        except FileNotFoundError, e:
            return False

    def parse_diff_revision(self, file_str, revision_str):
        raise NotImplementedError

    def get_diffs_use_absolute_paths(self):
        return False

    def get_changeset(self, changesetid):
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

    @classmethod
    def check_repository(cls, path, username=None, password=None):
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
            sshutils.check_host(hostname, username, password)

    @classmethod
    def get_auth_from_uri(cls, path, username):
        """
        Returns a 2-tuple of the username and hostname, given the path.

        If a username is implicitly passed via the path (user@host), and no
        explicit username was defined, we use the implied username.
        """
        url = urlparse.urlparse(path)

        if '@' in url[1]:
            netloc_username, hostname = url[1].split('@', 1)
        else:
            hostname = url[1]

        if not username and not netloc_username:
            return netloc_username, hostname
        else:
            return username, hostname

    @classmethod
    def accept_certificate(cls, path):
        """Accepts the certificate for the given repository path."""
        raise NotImplemented
