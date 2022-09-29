import logging
import os
import re
import subprocess
from tempfile import mkstemp

from django.utils.translation import gettext_lazy as _
from djblets.util.filesystem import is_exe_in_path

from reviewboard.scmtools.core import (SCMTool, ChangeSet,
                                       HEAD, PRE_CREATION)
from reviewboard.scmtools.errors import (SCMError, FileNotFoundError,
                                         RepositoryNotFoundError)
from reviewboard.diffviewer.parser import DiffParser


logger = logging.getLogger(__name__)


class PlasticTool(SCMTool):
    scmtool_id = 'plastic'
    name = "Plastic SCM"
    diffs_use_absolute_paths = True
    supports_pending_changesets = True
    field_help_text = {
        'path': _('The Plastic repository spec in the form of '
                  '[repo]@[hostname]:[port].'),
    }
    dependencies = {
        'executables': ['cm'],
    }

    REP_RE = re.compile(br'^(?P<reponame>.*)@(?P<hostname>.*):(?P<port>\d+)$')
    CS_RE = re.compile(br'^(?P<csid>\d+) (?P<user>[^\s]+) (?P<revid>\d+) '
                       br'(?P<file>.*)$')
    REPOLIST_RE = re.compile(br'^\s*\d+\s*(?P<reponame>[^\s]+)\s*.*:.*$')
    UNKNOWN_REV = "rev:revid:-1"

    def __init__(self, repository):
        super(PlasticTool, self).__init__(repository)

        self.reponame, self.hostname, self.port = \
            self.parse_repository(repository.path)
        self.client = PlasticClient(repository.path, self.reponame,
                                    self.hostname, self.port)

    def get_changeset(self, changesetid, allow_empty=False):
        logger.debug('Plastic: get_changeset %s', changesetid)

        changesetdata = self.client.get_changeset(changesetid)
        logger.debug('Plastic: changesetdata %s', changesetdata)

        # Changeset data is in the form of multiple lines of:
        # <changesetid> <user> <revid> <file spec>
        #
        # We assume the user and comment will be the same for each item, so
        # read it out of the first.
        #

        changeset = ChangeSet()
        changeset.changenum = changesetid

        split = changesetdata.split(b'\n')
        m = self.CS_RE.match(split[0])
        revid = m.group("revid")
        changeset.username = m.group("user")
        changeset.summary = self.client.get_changeset_comment(changesetid,
                                                              revid)
        logger.debug('Plastic: changeset user %s summary %s',
                     changeset.username, changeset.summary)

        for line in split:
            if line:
                m = self.CS_RE.match(line)

                if not m:
                    logger.debug('Plastic: bad re %s failed to match %s',
                                 self.CS_RE, line)
                    raise SCMError("Error looking up changeset")

                if m.group('csid') != str(changesetid):
                    logger.debug('Plastic: csid %s != %s',
                                 m.group('csid'), changesetid)
                    raise SCMError('The server returned a changeset ID that '
                                   'was not requested')

                logger.debug('Plastic: adding file %s',
                             m.group('file'))
                changeset.files += m.group('file')

        return changeset

    def get_file(self, path, revision=HEAD, **kwargs):
        logger.debug('Plastic: get_file %s revision %s', path, revision)

        if revision == PRE_CREATION:
            return b''

        # Check for new files
        if revision == self.UNKNOWN_REV:
            return b''

        return self.client.get_file(path, revision)

    def file_exists(self, path, revision=HEAD, **kwargs):
        logger.debug('Plastic: file_exists %s revision %s', path, revision)

        if revision == PRE_CREATION:
            return True

        # Check for new files
        if revision == self.UNKNOWN_REV:
            return True

        try:
            return self.client.get_file(path, revision)
        except FileNotFoundError:
            return False

    def parse_diff_revision(self, filename, revision, *args, **kwargs):
        """Parse and return a filename and revision from a diff.

        Args:
            filename (bytes):
                The filename as represented in the diff.

            revision (bytes):
                The revision as represented in the diff.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            tuple:
            A tuple containing two items:

            1. The normalized filename as a byte string.
            2. The normalized revision as a byte string or a
               :py:class:`~reviewboard.scmtools.core.Revision`.
        """
        assert isinstance(filename, bytes), (
            'filename must be a byte string, not %s' % type(filename))
        assert isinstance(revision, bytes), (
            'revision must be a byte string, not %s' % type(revision))

        logger.debug('Plastic: parse_diff_revision file %s revision %s',
                     filename.decode('utf-8'),
                     revision.decode('utf-8'))

        if revision == b'PRE-CREATION':
            revision = PRE_CREATION

        return filename, revision

    def get_parser(self, data):
        return PlasticDiffParser(data)

    @classmethod
    def parse_repository(cls, path):
        m = cls.REP_RE.match(path)

        if m:
            repopath = m.group("reponame")
            hostname = m.group("hostname")
            port = m.group("port")

            return repopath, hostname, port
        else:
            raise RepositoryNotFoundError()

    @classmethod
    def check_repository(cls, path, **kwargs):
        """Perform checks on a repository to test its validity.

        This checks if a repository exists and can be connected to.

        A failed result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception will
        be thrown.

        Args:
            path (unicode):
                The repository path.

            **kwargs (dict, unused):
                Additional settings for the repository.

        Raises:
            reviewboard.scmtools.errors.RepositoryNotFoundError:
                The repository at the given path could not be found.

            reviewboard.scmtools.errors.SCMError:
                There was a general error communicating with Perforce.
        """
        m = cls.REP_RE.match(path)

        if not m:
            raise RepositoryNotFoundError()

        # Can't use 'cm checkconnection' here as it only checks the
        # pre-configured server

        server = "%s:%s" % (m.group("hostname"), m.group("port"))
        reponame = m.group("reponame")

        logger.debug('Plastic: Checking repository %s@%s',
                     reponame, server)

        repositories = PlasticClient.get_repositories(server)
        split = repositories.splitlines()

        for rep in split:
            m = cls.REPOLIST_RE.match(rep)
            if m and m.group("reponame") == reponame:
                break
        else:
            raise RepositoryNotFoundError()


class PlasticDiffParser(DiffParser):
    """
    This class is able to parse diffs created with the plastic client
    support in post-review.
    """

    # As the diff creation is based on the Perforce code, so this is based
    # on the PerforceDiffParser (specifically, the binary file markers)
    BINARY_RE = re.compile(br'^==== ([^\s]+) \(([^\)]+)\) ==([ACIMR])==$')

    def __init__(self, data):
        super(PlasticDiffParser, self).__init__(data)

    def parse_diff_header(self, linenum, info):
        m = self.BINARY_RE.match(self.lines[linenum])

        if m:
            info['origFile'] = m.group(1)
            info['origInfo'] = m.group(2)
            info['newFile'] = m.group(1)
            info['newInfo'] = ""
            linenum += 1

            if (linenum < len(self.lines) and
                (self.lines[linenum].startswith(b"Binary files ") or
                 self.lines[linenum].startswith(b"Files "))):
                info['binary'] = True
                linenum += 1

            # In this case, this *is* our diff header.  We don't want to
            # let the next line's real diff header be a part of this one,
            # so return now
            return linenum

        return super(PlasticDiffParser, self).parse_diff_header(linenum, info)


class PlasticClient(object):
    def __init__(self, repository, reponame, hostname, port):
        if not is_exe_in_path('cm'):
            # This is technically not the right kind of error, but it's the
            # pattern we use with all the other tools.
            raise ImportError

        self.reponame = reponame
        self.hostname = hostname
        self.port = port

    def get_file(self, path, revision):
        logger.debug('Plastic: get_file %s rev %s', path, revision)

        repo = "rep:%s@repserver:%s:%s" % (self.reponame, self.hostname,
                                           self.port)

        # Work around a plastic bug, where 'cm cat --file=blah' gets an
        # extra newline, but plain 'cm cat' doesn't
        fd, tmpfile = mkstemp()
        os.close(fd)

        p = subprocess.Popen(
            ['cm', 'cat', revision + '@' + repo, '--file=' + tmpfile],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            close_fds=(os.name != 'nt'))
        errmsg = str(p.stderr.read())
        failure = p.wait()

        if failure:
            if not errmsg:
                errmsg = p.stdout.read()

            raise SCMError(errmsg)

        with open(tmpfile, 'rb') as readtmp:
            contents = readtmp.read()
        os.unlink(tmpfile)

        return contents

    def get_changeset(self, changesetid):
        logger.debug('Plastic: get_changeset %s', changesetid)

        repo = "rep:%s@repserver:%s:%s" % (self.reponame, self.hostname,
                                           self.port)

        p = subprocess.Popen(['cm', 'find', 'revs', 'where',
                              'changeset=' + str(changesetid), 'on',
                              'repository', '\'' + repo + '\'',
                              '--format={changeset} {owner} {id} {item}',
                              '--nototal'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=(os.name != 'nt'))
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            raise SCMError(errmsg)

        return contents

    def get_changeset_comment(self, changesetid, revid):
        logger.debug('Plastic: get_changeset_comment %s', changesetid)

        repo = "rep:%s@repserver:%s:%s" % (self.reponame, self.hostname,
                                           self.port)

        p = subprocess.Popen(['cm', 'find', 'changesets', 'where',
                              'changesetid=' + str(changesetid),
                              'on', 'repository', '\'' + repo + '\'',
                              '--format={comment}', '--nototal'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=(os.name != 'nt'))
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            raise SCMError(errmsg)

        return contents

    @classmethod
    def get_repositories(cls, server):
        logger.debug('Plastic: get_repositories %s', server)

        p = subprocess.Popen(['cm', 'listrepositories', server],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=(os.name != 'nt'))
        repositories = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            if not errmsg and repositories.startswith('Error:'):
                error = repositories
            else:
                error = errmsg

            raise SCMError(error)

        return repositories
