import os
import random
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import time

from djblets.util.filesystem import is_exe_in_path
try:
    from P4 import P4Exception
except ImportError:
    pass

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.core import SCMTool, ChangeSet, \
                                      HEAD, PRE_CREATION
from reviewboard.scmtools.errors import SCMError, EmptyChangeSetError, \
                                        AuthenticationError, \
                                        RepositoryNotFoundError


STUNNEL_SERVER, STUNNEL_CLIENT = (0, 1)


class STunnelProxy(object):
    def __init__(self, mode, target):
        if not is_exe_in_path('stunnel'):
            raise OSError('stunnel was not found in the exec path')

        if mode not in (STUNNEL_SERVER, STUNNEL_CLIENT):
            raise AttributeError
        self.mode = mode
        self.target = target
        self.pid = None

    def start_server(self, certfile):
        self._start(['-p', certfile])

    def start_client(self):
        self._start(['-c'])

    def _start(self, additional_args):
        self.port = self._find_port()

        tempdir = tempfile.mkdtemp()
        filename = os.path.join(tempdir, 'stunnel.pid')
        args = ['stunnel', '-P', filename,
                '-d', '127.0.0.1:%d' % self.port,
                '-r', self.target] + additional_args

        subprocess.check_call(args)

        # It can sometimes be racy to immediately open the file. We therefore
        # have to wait a fraction of a second =/
        time.sleep(0.1)
        f = open(filename)
        self.pid = int(f.read())
        f.close()
        shutil.rmtree(tempdir)

    def shutdown(self):
        if self.pid:
            os.kill(self.pid, signal.SIGTERM)
            self.pid = None

    def _find_port(self):
        """Find an available port."""
        # This is slightly racy but shouldn't be too bad.
        while True:
            port = random.randint(30000, 60000)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(('127.0.0.1', port))
                s.listen(1)
                s.shutdown(socket.SHUT_RDWR)
                return port
            except:
                pass


class PerforceClient(object):
    def __init__(self, p4port, username, password, use_stunnel=False):
        self.p4port = p4port
        self.username = username
        self.password = password
        self.use_stunnel = use_stunnel
        self.proxy = None

        import P4
        self.p4 = P4.P4()

        if use_stunnel and not is_exe_in_path('stunnel'):
            raise AttributeError('stunnel proxy was requested, but stunnel '
                                 'binary is not in the exec path.')

    def _connect(self):
        """
        Connect to the perforce server.

        This connects p4python to the remote server, optionally using a stunnel
        proxy.
        """
        self.p4.user = self.username
        self.p4.password = self.password
        self.p4.exception_level = 1

        if self.use_stunnel:
            # Spin up an stunnel client and then redirect through that
            self.proxy = STunnelProxy(STUNNEL_CLIENT, self.p4port)
            self.proxy.start_client()
            self.p4.port = '127.0.0.1:%d' % self.proxy.port
        else:
            self.p4.port = self.p4port
        self.p4.connect()

    def _disconnect(self):
        """
        Disconnect from the perforce server, and also shut down the stunnel
        proxy (if it exists).
        """
        try:
            if self.p4.connected():
                self.p4.disconnect()
        except AttributeError:
            pass

        if self.proxy:
            try:
                self.proxy.shutdown()
            except:
                pass
            self.proxy = None

    @staticmethod
    def _convert_p4exception_to_scmexception(e):
        error = str(e)
        if 'Perforce password' in error or 'Password must be set' in error:
            raise AuthenticationError(msg=error)
        elif 'check $P4PORT' in error:
            raise RepositoryNotFoundError
        else:
            raise SCMError(error)

    def _run_worker(self, worker):
        result = None

        # TODO: Move to using with: when we require a minimum of Python 2.5.
        #       We should make it auto-disconnect.
        try:
            self._connect()
            result = worker()
            self._disconnect()
        except P4Exception, e:
            self._disconnect()
            self._convert_p4exception_to_scmexception(e)
        except:
            self._disconnect();
            raise

        return result

    def _get_changeset(self, changesetid):
        return self.p4.run_describe('-s', str(changesetid))

    def get_changeset(self, changesetid):
        """
        Get the contents of a changeset description.
        """
        return self._run_worker(lambda: self._get_changeset(changesetid))

    def _get_pending_changesets(self, userid):
        changesets = self.p4.run_changes('-s', 'pending', '-u', userid)
        return map(self._get_changeset, [x.split()[1] for x in changesets])

    def get_pending_changesets(self, userid):
        """
        Get a list of changeset descriptions for all pending changesets for a
        given user.
        """
        return self._run_worker(lambda: self._get_pending_changesets(userid))

    def _get_file(self, path, revision):
        if revision == PRE_CREATION:
            return ''
        elif revision == HEAD:
            depot_path = path
        else:
            depot_path = '%s#%s' % (path, revision)

        args = ['p4', '-p', self.p4.port]
        if self.p4.user:
            args.extend(['-u', self.p4.user])
        if self.p4.password:
            args.extend(['-P', self.p4.password])
        args.extend(['print', '-q', depot_path])

        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        result, errdata = p.communicate()
        failure = p.poll()

        if failure:
            error = errdata.splitlines()
            # The command-line output is the same as the contents of a
            # P4Exception except they're prefixed with a line that says
            # "Perforce client error:", and the lines of the error are indented
            # with tabs.
            if error[0].startswith('Perforce client error:'):
                error = error[1:]
            text = '\n'.join(line.lstrip('\t') for line in error)

            self._convert_p4exception_to_scmexception(Exception(text))
        else:
            return result

    def get_file(self, path, revision):
        """
        Get the contents of a file, at a specific revision.
        """
        return self._run_worker(lambda: self._get_file(path, revision))

    def _get_files_at_revision(self, revision_str):
        return self.p4.run_files(revision_str)

    def get_files_at_revision(self, revision_str):
        """
        Get a list of files at a specific revision. This is a simple interface
        to 'p4 files'
        """
        return self._run_worker(
            lambda: self._get_files_at_revision(revision_str))


class PerforceTool(SCMTool):
    name = "Perforce"
    uses_atomic_revisions = True
    supports_authentication = True
    dependencies = {
        'modules': ['P4'],
    }

    def __init__(self, repository):
        SCMTool.__init__(self, repository)

        self.client = self._create_client(
            str(repository.mirror_path or repository.path),
            str(repository.username),
            str(repository.password))

    @staticmethod
    def _create_client(path, username, password):
        if path.startswith('stunnel:'):
            path = path[8:]
            use_stunnel = True
        else:
            use_stunnel = False
        return PerforceClient(path, username, password, use_stunnel)

    @staticmethod
    def _convert_p4exception_to_scmexception(e):
        error = str(e)
        if 'Perforce password' in error or 'Password must be set' in error:
            raise AuthenticationError(msg=error)
        elif 'check $P4PORT' in error:
            raise RepositoryNotFoundError
        else:
            raise SCMError(error)

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None):
        """
        Performs checks on a repository to test its validity.

        This should check if a repository exists and can be connected to.

        The result is returned as an exception. The exception may contain extra
        information, such as a human-readable description of the problem. If the
        repository is valid and can be connected to, no exception will be
        thrown.
        """
        super(PerforceTool, cls).check_repository(path, username, password,
                                                  local_site_name)

        client = cls._create_client(str(path), str(username), str(password))
        client.get_changeset(1)

    def get_pending_changesets(self, userid):
        return self.client.get_pending_changesets(userid)

    def get_changeset(self, changesetid):
        changeset = self.client.get_changeset(changesetid)
        if changeset:
            return self.parse_change_desc(changeset[0], changesetid)
        else:
            return None

    def get_diffs_use_absolute_paths(self):
        return True

    def get_file(self, path, revision=HEAD):
        return self.client.get_file(path, revision)

    def parse_diff_revision(self, file_str, revision_str):
        # Perforce has this lovely idiosyncracy that diffs show revision #1 both
        # for pre-creation and when there's an actual revision.
        filename, revision = revision_str.rsplit('#', 1)
        if len(self.client.get_files_at_revision(revision_str)) == 0:
            revision = PRE_CREATION
        return filename, revision

    def get_filenames_in_revision(self, revision):
        return self.get_changeset(revision).files

    @staticmethod
    def parse_change_desc(changedesc, changenum):
        if not changedesc:
            return None

        changeset = ChangeSet()
        changeset.changenum = changenum

        # At it's most basic, a perforce changeset description has three
        # sections.
        #
        # ---------------------------------------------------------
        # Change <num> by <user>@<client> on <timestamp> *pending*
        #
        #         description...
        #         this can be any number of lines
        #
        # Affected files ...
        #
        # //depot/branch/etc/file.cc#<revision> branch
        # //depot/branch/etc/file.hh#<revision> delete
        # ---------------------------------------------------------
        #
        # At the moment, we only care about the description and the list of
        # files.  We take the first line of the description as the summary.
        #
        # We parse the username out of the first line to check that one user
        # isn't attempting to "claim" another's changelist.  We then split
        # everything around the 'Affected files ...' line, and process the
        # results.
        changeset.username = changedesc['user']
        changeset.description = changedesc['desc']
        if changedesc['status'] == "pending":
            changeset.pending = True
        try:
            changeset.files = changedesc['depotFile']
        except KeyError:
            raise EmptyChangeSetError(changenum)

        split = changeset.description.find('\n\n')
        if split >= 0 and split < 100:
            changeset.summary = \
                changeset.description.split('\n\n', 1)[0].replace('\n', ' ')
        else:
            changeset.summary = changeset.description.split('\n', 1)[0]

        return changeset

    def get_fields(self):
        return ['changenum', 'diff_path']

    def get_parser(self, data):
        return PerforceDiffParser(data)


class PerforceDiffParser(DiffParser):
    SPECIAL_REGEX = re.compile("^==== ([^#]+)#(\d+) ==([AMD])== (.*) ====$")

    def __init__(self, data):
        DiffParser.__init__(self, data)

    def parse_diff_header(self, linenum, info):
        m = self.SPECIAL_REGEX.match(self.lines[linenum])
        if m:
            info['origFile'] = m.group(1)
            info['origInfo'] = "%s#%s" % (m.group(1), m.group(2))
            info['newFile'] = m.group(4)
            info['newInfo'] = ""
            linenum += 1

            if linenum < len(self.lines) and \
               (self.lines[linenum].startswith("Binary files ") or
                self.lines[linenum].startswith("Files ")):
                info['binary'] = True
                linenum += 1

            if m.group(3) == 'D':
                info['deleted'] = True

            # In this case, this *is* our diff header. We don't want to
            # let the next line's real diff header be a part of this one,
            # so return early and don't invoke the next.
            return linenum

        return super(PerforceDiffParser, self).parse_diff_header(linenum, info)
