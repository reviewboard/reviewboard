from __future__ import unicode_literals

import logging
import os
import random
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager

from django.utils import six
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djblets.util.filesystem import is_exe_in_path

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.certs import Certificate
from reviewboard.scmtools.core import (SCMTool, ChangeSet,
                                       HEAD, PRE_CREATION)
from reviewboard.scmtools.errors import (SCMError, EmptyChangeSetError,
                                         AuthenticationError,
                                         RepositoryNotFoundError,
                                         UnverifiedCertificateError)


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

    @cached_property
    def stunnel_use_config(self):
        """Whether stunnel uses a config-based model.

        stunnel 4+ switched to a config-based model, instead of passing
        arguments on the command line. This property returns whether that
        mode should be used.
        """
        # Try to run with stunnel -version, which is available in stunnel 4+.
        # If this succeeds, we're using a config-based version of stunnel.
        try:
            subprocess.check_call(['stunnel', '-version'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False

    def start_server(self, certfile):
        self._start(server=True, certfile=certfile)

    def start_client(self):
        self._start(server=False)

    def _start(self, server, certfile=None):
        self.port = self._find_port()

        tempdir = tempfile.mkdtemp()
        pid_filename = os.path.join(tempdir, 'stunnel.pid')

        # There are two major versions of stunnel we're supporting today:
        # stunnel 3, and stunnel 4+.
        #
        # stunnel 3 used command line arguments instead of a config file, and
        # stunnel 4 (released in 2002) completely changed to a config-based
        # model.
        #
        # It's probably not worth continuing to support version 3 at this
        # point, given that any modern install supporting Review Board's other
        # dependencies will also have a newer version of stunnel. However,
        # we'll continue to keep this code for those rare cases where an older
        # version is still needed.
        if self.stunnel_use_config:
            conf_filename = os.path.join(tempdir, 'stunnel.conf')

            with open(conf_filename, 'w') as fp:
                fp.write('pid = %s\n' % pid_filename)

                if server:
                    fp.write('[p4d]\n')

                    if certfile:
                        fp.write('cert = %s\n' % certfile)

                    fp.write('accept = %s\n' % self.port)
                    fp.write('connect = %s\n' % self.target)
                else:
                    fp.write('[p4]\n')
                    fp.write('client = yes\n')
                    fp.write('accept = 127.0.0.1:%s\n' % self.port)
                    fp.write('connect = %s\n' % self.target)

            args = [conf_filename]
        else:
            args = [
                '-P', pid_filename,
                '-d', '127.0.0.1:%d' % self.port,
                '-r', self.target,
            ]

            if server:
                args += ['-p', certfile]
            else:
                args.append('-c')

        try:
            subprocess.check_call(['stunnel'] + args)
        except subprocess.CalledProcessError:
            if self.stunnel_use_config:
                with open(conf_filename, 'r') as fp:
                    logging.error('Unable to create an stunnel using '
                                  'config:\n%s\n'
                                  % fp.read())
            else:
                logging.error('Unable to create an stunnel with args: %s\n'
                              % ' '.join(args))
        else:
            # It can sometimes be racy to immediately open the file. We
            # therefore have to wait a fraction of a second =/
            time.sleep(0.1)

            try:
                with open(pid_filename) as f:
                    self.pid = int(f.read())
                    f.close()
            except IOError as e:
                logging.exception('Unable to open stunnel PID file %s: %s\n'
                                  % (pid_filename, e))

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
                return port
            finally:
                try:
                    s.close()
                except:
                    pass


class PerforceClient(object):
    def __init__(self, p4port, username, password, encoding, p4host=None,
                 use_stunnel=False, use_ticket_auth=False):
        self.p4port = p4port
        self.username = username
        self.password = password
        self.encoding = encoding
        self.p4host = p4host
        self.use_stunnel = use_stunnel
        self.use_ticket_auth = use_ticket_auth
        self.proxy = None

        import P4
        self.p4 = P4.P4()

        if use_stunnel and not is_exe_in_path('stunnel'):
            raise AttributeError('stunnel proxy was requested, but stunnel '
                                 'binary is not in the exec path.')

    @contextmanager
    def _connect(self):
        """
        Connect to the perforce server.

        This connects p4python to the remote server, optionally using a stunnel
        proxy.
        """
        self.p4.user = self.username.encode('utf-8')
        self.p4.password = self.password.encode('utf-8')

        if self.encoding:
            self.p4.charset = self.encoding.encode('utf-8')

        self.p4.exception_level = 1

        if self.use_stunnel:
            # Spin up an stunnel client and then redirect through that
            self.proxy = STunnelProxy(STUNNEL_CLIENT, self.p4port)
            self.proxy.start_client()
            p4_port = '127.0.0.1:%d' % self.proxy.port
        else:
            p4_port = self.p4port

        self.p4.port = p4_port.encode('utf-8')

        if self.p4host:
            self.p4.host = self.p4host.encode('utf-8')

        self.p4.connect()

        if self.use_ticket_auth:
            self.p4.run_login()

        yield

        self._disconnect()

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
        error = six.text_type(e)

        if 'Perforce password' in error or 'Password must be set' in error:
            raise AuthenticationError(msg=error)
        elif 'SSL library must be at least version' in error:
            raise SCMError(_('The specified Perforce port includes ssl:, but '
                             'the p4python library was built without SSL '
                             'support or the system library path is '
                             'incorrect.'))
        elif ('check $P4PORT' in error or
              (error.startswith('[P4.connect()] TCP connect to') and
               'failed.' in error)):
            raise RepositoryNotFoundError
        elif "To allow connection use the 'p4 trust' command" in error:
            fingerprint = error.split('\\n')[3]
            raise UnverifiedCertificateError(
                Certificate(fingerprint=fingerprint))
        else:
            raise SCMError(error)

    def _run_worker(self, worker):
        from P4 import P4Exception
        try:
            with self._connect():
                return worker()
        except P4Exception as e:
            self._convert_p4exception_to_scmexception(e)

    def _get_changeset(self, changesetid):
        changesetid = six.text_type(changesetid)

        try:
            change = self.p4.run_change('-o', '-O', changesetid)
            changesetid = change[0]['Change']
        except Exception as e:
            logging.warning('Failed to get updated changeset information for '
                            'CLN %s (%s): %s',
                            changesetid, self.p4port, e, exc_info=True)

        return self.p4.run_describe('-s', changesetid)

    def get_changeset(self, changesetid):
        """
        Get the contents of a changeset description.
        """
        return self._run_worker(lambda: self._get_changeset(changesetid))

    def get_info(self):
        return self._run_worker(self.p4.run_info)

    def _get_file(self, path, revision):
        if revision == PRE_CREATION:
            return ''
        elif revision == HEAD:
            depot_path = path
        else:
            depot_path = '%s#%s' % (path, revision)

        res = self.p4.run_print('-q', depot_path)
        if res:
            return res[-1]

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
    supports_ticket_auth = True
    supports_pending_changesets = True
    field_help_text = {
        'path': _('The Perforce port identifier (P4PORT) for the repository. '
                  'If your server is set up to use SSL (2012.1+), prefix the '
                  'port with "ssl:". If your server connection is secured '
                  'with stunnel (2011.x or older), prefix the port with '
                  '"stunnel:".'),
    }
    dependencies = {
        'modules': ['P4'],
    }

    def __init__(self, repository):
        SCMTool.__init__(self, repository)

        credentials = repository.get_credentials()

        self.client = self._create_client(
            path=six.text_type(repository.mirror_path or repository.path),
            username=six.text_type(credentials['username']),
            password=six.text_type(credentials['password'] or ''),
            encoding=six.text_type(repository.encoding),
            host=six.text_type(repository.extra_data.get('p4_host', '')),
            use_ticket_auth=repository.extra_data.get('use_ticket_auth',
                                                      False))

    @staticmethod
    def _create_client(path, username, password, encoding='', host=None,
                       use_ticket_auth=False):
        if path.startswith('stunnel:'):
            path = path[8:]
            use_stunnel = True
        else:
            use_stunnel = False

        return PerforceClient(path, username, password, encoding, host,
                              use_stunnel, use_ticket_auth)

    @staticmethod
    def _convert_p4exception_to_scmexception(e):
        error = six.text_type(e)
        if 'Perforce password' in error or 'Password must be set' in error:
            raise AuthenticationError(msg=error)
        elif 'check $P4PORT' in error:
            raise RepositoryNotFoundError
        else:
            raise SCMError(error)

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         p4_host=None, local_site_name=None):
        """Perform checks on a repository to test its validity.

        This checks if a repository exists and can be connected to.

        A failed result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception will
        be thrown.

        Args:
            path (unicode):
                The Perforce repository path (equivalent to :env:`P4PORT`).

            username (unicode):
                The username used to authenticate.

            password (unicode):
                The password used to authenticate.

            p4_host (unicode):
                The optional Perforce host name (equivalent to
                :env:`P4HOST`).

            local_site_name (unicode):
                The optional Local Site name.

        Raises:
            reviewboard.scmtools.errors.AuthenticationError:
                There was an error authenticating with Perforce.

            reviewboard.scmtools.errors.RepositoryNotFoundError:
                The repository at the given path could not be found.

            reviewboard.scmtools.errors.SCMError:
                There was a general error communicating with Perforce.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The Perforce SSL certificate could not be verified.
        """
        super(PerforceTool, cls).check_repository(path, username, password,
                                                  local_site_name)

        # 'p4 info' will succeed even if the server requires ticket auth and we
        # don't run 'p4 login' first. We therefore don't go through all the
        # trouble of handling tickets here.
        client = cls._create_client(six.text_type(path),
                                    six.text_type(username),
                                    six.text_type(password),
                                    host=six.text_type(p4_host or ''))
        client.get_info()

    def get_changeset(self, changesetid, allow_empty=False):
        changeset = self.client.get_changeset(changesetid)
        if changeset:
            return self.parse_change_desc(changeset[0], changesetid,
                                          allow_empty)
        else:
            return None

    def get_diffs_use_absolute_paths(self):
        return True

    def get_file(self, path, revision=HEAD, **kwargs):
        return self.client.get_file(path, revision)

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        # Perforce has this lovely idiosyncracy that diffs show revision #1
        # both for pre-creation and when there's an actual revision.
        filename, revision = revision_str.rsplit('#', 1)
        if len(self.client.get_files_at_revision(revision_str)) == 0:
            revision = PRE_CREATION
        return filename, revision

    @staticmethod
    def parse_change_desc(changedesc, changenum, allow_empty=False):
        if not changedesc:
            return None

        changeset = ChangeSet()
        try:
            changeset.changenum = int(changedesc['change'])
        except ValueError:
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

        try:
            changeset.description = changedesc['desc'].decode('utf-8')
        except UnicodeDecodeError:
            changeset.description = changedesc['desc'].decode('utf-8',
                                                              'replace')

        if changedesc['status'] == "pending":
            changeset.pending = True
        try:
            changeset.files = changedesc['depotFile']
        except KeyError:
            if not allow_empty:
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

    @classmethod
    def accept_certificate(cls, path, username=None, password=None,
                           local_site_name=None, certificate=None):
        """Accepts the certificate for the given repository path."""
        args = ['p4', '-p', path, 'trust', '-i', certificate.fingerprint]
        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        _, errdata = p.communicate()
        failure = p.poll()

        if failure:
            raise IOError(errdata)

        return certificate.fingerprint

    def normalize_patch(self, patch, filename, revision):
        # The patch contents may represent an unchanged, moved file, which
        # isn't technically a valid diff, and will make patch mad. So, look
        # for this and return a blank diff instead.
        m = PerforceDiffParser.SPECIAL_REGEX.match(patch.strip())

        if m and m.group(3) == 'MV':
            return ''

        return patch


class PerforceDiffParser(DiffParser):
    SPECIAL_REGEX = re.compile("^==== ([^#]+)#(\d+) ==([AMD]|MV)== (.*) ====$")

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
               (self.lines[linenum].startswith(b"Binary files ") or
                self.lines[linenum].startswith(b"Files ")):
                info['binary'] = True
                linenum += 1

            change_type = m.group(3)

            if change_type == 'D':
                info['deleted'] = True
            elif change_type == 'MV':
                info['moved'] = True

            # In this case, this *is* our diff header. We don't want to
            # let the next line's real diff header be a part of this one,
            # so return early and don't invoke the next.
            return linenum

        return super(PerforceDiffParser, self).parse_diff_header(linenum, info)

    def parse_special_header(self, linenum, info):
        linenum = super(PerforceDiffParser, self).parse_special_header(
            linenum, info)

        if (linenum + 2 < len(self.lines) and
            self.lines[linenum].startswith(b'Moved from:') and
            self.lines[linenum + 1].startswith(b'Moved to:')):
            info['moved'] = True
            linenum += 2

        return linenum

    def normalize_diff_filename(self, filename):
        """Normalize filenames in diffs.

        The default behavior of stripping off leading slashes doesn't work for
        Perforce (because depot paths start with //), so this overrides it to
        just return the filename un-molested.
        """
        return filename
