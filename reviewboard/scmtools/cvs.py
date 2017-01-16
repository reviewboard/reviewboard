from __future__ import unicode_literals

import logging
import os
import re
import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.translation import ugettext as _
from djblets.util.filesystem import is_exe_in_path

from reviewboard.scmtools.core import SCMTool, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import (AuthenticationError,
                                         SCMError,
                                         FileNotFoundError,
                                         RepositoryNotFoundError)
from reviewboard.diffviewer.parser import DiffParser, DiffParserError
from reviewboard.ssh import utils as sshutils
from reviewboard.ssh.errors import SSHAuthenticationError, SSHError


sshutils.register_rbssh('CVS_RSH')


class CVSTool(SCMTool):
    name = "CVS"
    diffs_use_absolute_paths = True
    field_help_text = {
        'path': 'The CVSROOT used to access the repository.',
    }
    dependencies = {
        'executables': ['cvs'],
    }

    rev_re = re.compile(r'^.*?(\d+(\.\d+)+)\r?$')

    remote_cvsroot_re = re.compile(
        r'^(:(?P<protocol>[gkp]?server|ext|ssh|extssh):'
        r'((?P<username>[^:@]+)(:(?P<password>[^@]+))?@)?)?'
        r'(?P<hostname>[^:]+):(?P<port>\d+)?(?P<path>.*)')
    local_cvsroot_re = re.compile(r'^:(?P<protocol>local|fork):(?P<path>.+)')

    def __init__(self, repository):
        super(CVSTool, self).__init__(repository)

        credentials = repository.get_credentials()

        # Note that we're not validating the CVSROOT here, as the path may
        # contain a value that "worked" prior to us introducing validation.
        # In those cases, we'd have either parsed out the invalid data or
        # simply let CVS deal with it. We don't want to break those setups.
        self.cvsroot, self.repopath = \
            self.build_cvsroot(self.repository.path,
                               credentials['username'],
                               credentials['password'],
                               validate=False)

        local_site_name = None

        if repository.local_site:
            local_site_name = repository.local_site.name

        self.client = CVSClient(self.cvsroot, self.repopath, local_site_name)

    def get_file(self, path, revision=HEAD, **kwargs):
        if not path:
            raise FileNotFoundError(path, revision)

        return self.client.cat_file(path, revision)

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        if revision_str == "PRE-CREATION":
            return file_str, PRE_CREATION

        m = self.rev_re.match(revision_str)
        if m:
            return file_str, m.group(1)
        else:
            # Newer versions of CVS stick the file revision after the filename,
            # separated by a colon. Check for that format too.
            colon_idx = file_str.rfind(":")
            if colon_idx == -1:
                raise SCMError("Unable to parse diff revision header "
                               "(file_str='%s', revision_str='%s')"
                               % (file_str, revision_str))
            return file_str[:colon_idx], file_str[colon_idx + 1:]

    def get_parser(self, data):
        return CVSDiffParser(data, self.repopath)

    def normalize_path_for_display(self, filename):
        """Normalize a path from a diff for display to the user.

        This can take a path/filename found in a diff and normalize it,
        stripping away unwanted information, so that it displays in a better
        way in the diff viewer.

        For CVS, this strips trailing ",v" from filenames.

        Args:
            filename (unicode):
                The filename/path to normalize.

        Returns:
            unicode:
            The resulting filename/path.
        """
        return re.sub(',v$', '', filename)

    def normalize_patch(self, patch, filename, revision=HEAD):
        """Normalizes the content of a patch.

        This will collapse any keywords in the patch, ensuring that we can
        safely compare them against any files we cat from the repository,
        without the keyword values conflicting.
        """
        return self.client.collapse_keywords(patch)

    @classmethod
    def build_cvsroot(cls, cvsroot, username, password, validate=True):
        """Parse and construct a CVSROOT from the given arguments.

        This will take a repository path or CVSROOT provided by the caller,
        optionally validate it, and return both a new CVSROOT and the path
        within it.

        If a username/password are provided as arguments, but do not exist in
        ``cvsroot``, then the resulting CVSROOT will contain the
        username/password.

        If data is provided that is not supported by the type of protocol
        specified in ``cvsroot``, then it will raise a
        :py:class:`~django.core.exceptions.ValidationError` (if validating)
        or strip the data from the CVSROOT.

        Args:
            cvsroot (unicode):
                A CVSROOT string, or a bare repository path to turn into one.

            username (unicode):
                Optional username for the CVSROOT.

            password (unicode):
                Optional password for the CVSROOT (only supported for
                ``pserver`` types).

            validate (bool, optional):
                Whether to validate the provided CVSROOT and username/password.

                If set, and the resulting CVSROOT would be invalid, then an
                error is raised.

                If not set, the resulting CVSROOT will have the invalid data
                stripped.

                This will check for ports, usernames, and passwords, depending
                on the type of CVSROOT provided.

        Returns:
            unicode:
            The resulting validated CVSROOT.

        Raises:
            django.core.exceptions.ValidationError:
                The provided data had a validation error. This is only raised
                if ``validate`` is set.
        """
        # CVS supports two types of CVSROOTs: Remote and local.
        #
        # The remote repositories share the same CVSROOT format (defined by
        # CVSTool.remove_cvsroot_re), and the local repositories share their
        # own format (CVSTool.local_cvsroot_re), but the two formats differ
        # in many ways.
        #
        # We'll be testing both formats to see if the path matches, starting
        # with remote repositories (the most common).
        m = cls.remote_cvsroot_re.match(cvsroot)

        if m:
            # The user either specified a valid remote repository path, or
            # simply hostname:port/path. In either case, we'll want to
            # construct our own CVSROOT based on that information and the
            # provided username and password, favoring the credentials in the
            # CVSROOT and falling back on those provided in the repository
            # configuration.
            #
            # There are some restrictions, depending on the type of protocol:
            #
            # * Only "pserver" supports passwords.
            # * Only "pserver", "gserver", and "kserver" support ports.
            protocol = m.group('protocol') or 'pserver'
            username = m.group('username') or username
            password = m.group('password') or password
            port = m.group('port') or None
            path = m.group('path')

            # Apply the restrictions, validating if necessary.
            if password and protocol != 'pserver':
                if validate:
                    raise ValidationError(
                        _('"%s" CVSROOTs do not support passwords.')
                        % protocol)

                password = None

            if port and protocol not in ('pserver', 'gserver', 'kserver'):
                if validate:
                    raise ValidationError(
                        _('"%s" CVSROOTs do not support specifying ports.')
                        % protocol)

                port = None

            # Inject any credentials into the string.
            if username:
                if password:
                    credentials = '%s:%s@' % (username, password)
                else:
                    credentials = '%s@' % (username)
            else:
                credentials = ''

            cvsroot = ':%s:%s%s:%s%s' % (protocol,
                                         credentials,
                                         m.group('hostname'),
                                         port or '',
                                         path)
        else:
            m = cls.local_cvsroot_re.match(cvsroot)

            if m:
                # This is a local path (either :local: or :fork). It's much
                # easier to deal with. We're only dealing with a path.
                path = m.group('path')

                if validate:
                    if username:
                        raise ValidationError(
                            _('"%s" CVSROOTs do not support usernames.')
                            % m.group('protocol'))

                    if password:
                        raise ValidationError(
                            _('"%s" CVSROOTs do not support passwords.')
                            % m.group('protocol'))
            else:
                # We couldn't parse this as a standard CVSROOT. It might be
                # something a lot more specific. We'll treat it as-is, but
                # this might cause some small issues in the diff viewer (files
                # may show up as read-only, since we can't strip the path,
                # for example).
                #
                # We could in theory treat this as a validation error, but
                # we might break special cases with specialized protocols
                # (which do exist but are rare).
                path = cvsroot

        return cvsroot, path

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
        try:
            cvsroot, repopath = cls.build_cvsroot(path, username, password)
        except ValidationError as e:
            raise SCMError('; '.join(e.messages))

        # CVS paths are a bit strange, so we can't actually use the
        # SSH checking in SCMTool.check_repository. Do our own.
        m = cls.remote_cvsroot_re.match(path)

        if m and m.group('protocol') in ('ext', 'ssh', 'extssh'):
            try:
                sshutils.check_host(m.group('hostname'), username, password,
                                    local_site_name)
            except SSHAuthenticationError as e:
                # Represent an SSHAuthenticationError as a standard
                # AuthenticationError.
                raise AuthenticationError(e.allowed_types, six.text_type(e),
                                          e.user_key)
            except:
                # Re-raise anything else
                raise

        client = CVSClient(cvsroot, repopath, local_site_name)

        try:
            client.check_repository()
        except (AuthenticationError, SCMError):
            raise
        except (SSHError, FileNotFoundError):
            raise RepositoryNotFoundError()

    @classmethod
    def parse_hostname(cls, path):
        """Parses a hostname from a repository path."""
        return urlparse(path)[1]  # netloc


class CVSDiffParser(DiffParser):
    """Diff parser for CVS diff files.

    This handles parsing diffs generated by :command:`cvs diff`, extracting
    the diff content and normalizing filenames for proper display in the
    diff viewer.
    """

    def __init__(self, data, rel_repo_path):
        super(CVSDiffParser, self).__init__(data)

        self.rcs_file_re = re.compile('^RCS file: (%s/)?(?P<path>.+?)(,v)?$'
                                      % re.escape(rel_repo_path))
        self.binary_re = re.compile(
            r'^Binary files (?P<origFile>.+) and (?P<newFile>.+) differ$')

    def parse_special_header(self, linenum, info):
        linenum = super(CVSDiffParser, self).parse_special_header(
            linenum, info)

        if 'index' not in info:
            # We didn't find an index, so the rest is probably bogus too.
            return linenum

        m = self.rcs_file_re.match(self.lines[linenum])

        if m:
            info['filename'] = m.group('path')
            linenum += 1
        else:
            raise DiffParserError('Unable to find RCS line', linenum)

        while self.lines[linenum].startswith(b'retrieving '):
            linenum += 1

        if self.lines[linenum].startswith(b'diff '):
            linenum += 1

        return linenum

    def parse_diff_header(self, linenum, info):
        linenum = super(CVSDiffParser, self).parse_diff_header(linenum, info)

        if 'origFile' not in info:
            # Check if this is a binary diff.
            m = self.binary_re.match(self.lines[linenum])

            if m:
                info['binary'] = True

                # The only file information we're going to have will come from
                # the binary string or the Index header. The Index header only
                # contains the new filename, not the original, so we're going
                # to trust the original value in the binary string message and
                # attempt to use the Index header value for the new filename.
                #
                # Later, we may change these up, depending on values, but they
                # work as reasonable defaults.
                info['origFile'] = m.group('origFile')
                info['newFile'] = info.get('filename') or m.group('newFile')

                # We can't get any revision information for this file.
                info['origInfo'] = ''
                info['newInfo'] = ''

                linenum += 1

        if info.get('origFile') in (b'/dev/null', b'nul:'):
            # If 'origFile' exists, then 'newFile' will also exist.
            info['origFile'] = info['newFile']
            info['origInfo'] = PRE_CREATION
        elif 'filename' in info:
            if info.get('newFile') == info.get('origFile'):
                # Both the old and new filenames referenced are identical, so
                # we'll want to update both to include the filename.
                #
                # In practice, both of these should be consistent for any
                # normal file changes (as CVS does not have
                # moves/renames/copies), but we're just covering bases by
                # checking for equality.
                info['newFile'] = info['filename']

            info['origFile'] = info['filename']

        if info.get('newFile') == b'/dev/null':
            info['deleted'] = True

        return linenum

    def normalize_diff_filename(self, filename):
        """Normalize filenames in diffs.

        The default behavior of stripping off leading slashes doesn't work for
        CVS, so this overrides it to just return the filename un-molested.
        """
        return filename


class CVSClient(object):
    keywords = [
        'Author',
        'Date',
        'Header',
        'Id',
        'Locker',
        'Name',
        'RCSfile',
        'Revision',
        'Source',
        'State',
    ]

    def __init__(self, cvsroot, path, local_site_name):
        self.tempdir = None
        self.currentdir = os.getcwd()
        self.cvsroot = cvsroot
        self.path = path
        self.local_site_name = local_site_name

        if not is_exe_in_path('cvs'):
            # This is technically not the right kind of error, but it's the
            # pattern we use with all the other tools.
            raise ImportError

    def cleanup(self):
        if self.currentdir != os.getcwd():
            # Restore current working directory
            os.chdir(self.currentdir)
            # Remove temporary directory
            if self.tempdir:
                shutil.rmtree(self.tempdir)

    def cat_file(self, filename, revision):
        # We strip the repo off of the fully qualified path as CVS does
        # not like to be given absolute paths.
        repos_path = self.path.split(":")[-1]

        if '@' in repos_path:
            repos_path = '/' + repos_path.split('@')[-1].split('/', 1)[-1]

        if filename.startswith(repos_path + "/"):
            filename = filename[len(repos_path) + 1:]

        # Strip off the ",v" we sometimes get for CVS paths. This is mostly
        # going to be an issue for older diffs, as newly-uploaded diffs should
        # strip these.
        if filename.endswith(",v"):
            filename = filename[:-2]

        # We want to try to fetch the files with different permutations of
        # "Attic" and no "Attic". This means there are 4 various permutations
        # that we have to check, based on whether we're using windows- or
        # unix-type paths

        filenameAttic = filename

        if '/Attic/' in filename:
            filename = '/'.join(filename.rsplit('/Attic/', 1))
        elif '\\Attic\\' in filename:
            filename = '\\'.join(filename.rsplit('\\Attic\\', 1))
        elif '\\' in filename:
            pos = filename.rfind('\\')
            filenameAttic = filename[0:pos] + "\\Attic" + filename[pos:]
        elif '/' in filename:
            pos = filename.rfind('/')
            filenameAttic = filename[0:pos] + "/Attic" + filename[pos:]
        else:
            # There isn't any path information, so we can't provide an
            # Attic path that makes any kind of sense.
            filenameAttic = None

        try:
            return self._cat_specific_file(filename, revision)
        except FileNotFoundError:
            if filenameAttic:
                return self._cat_specific_file(filenameAttic, revision)
            else:
                raise

    def _cat_specific_file(self, filename, revision):
        # Somehow CVS sometimes seems to write .cvsignore files to current
        # working directory even though we force stdout with -p.
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

        p = SCMTool.popen(['cvs', '-f', '-d', self.cvsroot, 'checkout', '-kk',
                           '-r', six.text_type(revision), '-p', filename],
                          self.local_site_name)
        contents = p.stdout.read()
        errmsg = six.text_type(p.stderr.read())
        failure = p.wait()

        # Unfortunately, CVS is not consistent about exiting non-zero on
        # errors.  If the file is not found at all, then CVS will print an
        # error message on stderr, but it doesn't set an exit code with
        # pservers.  If the file is found but an invalid revision is requested,
        # then cvs exits zero and nothing is printed at all. (!)
        #
        # But, when it is successful, cvs will print a header on stderr like
        # so:
        #
        # ===================================================================
        # Checking out foobar
        # RCS: /path/to/repo/foobar,v
        # VERS: 1.1
        # ***************

        # So, if nothing is in errmsg, or errmsg has a specific recognized
        # message, call it FileNotFound.
        if (not errmsg or
                errmsg.startswith('cvs checkout: cannot find module') or
                errmsg.startswith('cvs checkout: could not read RCS file')):
            self.cleanup()
            raise FileNotFoundError(filename, revision)

        # Otherwise, if there's an exit code, or errmsg doesn't look like
        # successful header, then call it a generic SCMError.
        #
        # If the .cvspass file doesn't exist, CVS will return an error message
        # stating this. This is safe to ignore.
        if ((failure and not errmsg.startswith('==========')) and
            '.cvspass does not exist - creating new file' not in errmsg):
            self.cleanup()
            raise SCMError(errmsg)

        self.cleanup()
        return contents

    def check_repository(self):
        # Running 'cvs version' and specifying a CVSROOT will bail out if said
        # CVSROOT is invalid, which is perfect for us. This used to use
        # 'cvs rls' which is maybe slightly more correct, but rls is only
        # available in CVS 1.12+
        p = SCMTool.popen(['cvs', '-f', '-d', self.cvsroot, 'version'],
                          self.local_site_name)
        errmsg = six.text_type(p.stderr.read())

        if p.wait() != 0:
            logging.error('CVS repository validation failed for '
                          'CVSROOT %s: %s',
                          self.cvsroot, errmsg)

            auth_failed_prefix = 'cvs version: authorization failed: '

            # See if there's an "authorization failed" anywhere in here. If so,
            # we want to raise AuthenticationError with that error message.
            for line in errmsg.splitlines():
                if line.startswith(auth_failed_prefix):
                    raise AuthenticationError(
                        msg=line[len(auth_failed_prefix):].strip())

            raise SCMError(errmsg)

    def collapse_keywords(self, data):
        """Collapse CVS/RCS keywords in string.

        CVS allows for several keywords (such as $Id$ and $Revision$) to
        be expanded, though these keywords are limited to a fixed set
        (and associated aliases) and must be enabled per-file.

        When we cat a file on CVS, the keywords come back collapsed, but
        the diffs uploaded may have expanded keywords. We use this function
        to collapse them back down in order to be able to apply the patch.
        """
        regex = re.compile(br'\$(%s):([^\$\n\r]*)\$' % '|'.join(self.keywords),
                           re.IGNORECASE)
        return regex.sub(br'$\1$', data)
