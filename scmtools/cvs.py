import os
import re
import subprocess
import tempfile

from reviewboard.scmtools.core import SCMError, FileNotFoundError, \
                                      SCMTool, HEAD, PRE_CREATION
from reviewboard.diffviewer.parser import DiffParser, DiffParserError


class CVSTool(SCMTool):
    regex_rev = re.compile(r'^.*?(\d+(\.\d+)+)\r?$')

    def __init__(self, repository):
        if ':' in repository.path:
            self.repopath = repository.path.split(':')[1]
            if repository.username:
                if repository.password:
                    auth = '%s:%s@' % (repository.username, repository.password)
                else:
                    auth = '%s@' % (repository.username)
            else:
                auth = ''
            self.CVSROOT = ":pserver:%s%s" % (auth, repository.path)
        else:
            self.repopath = self.CVSROOT = repository.path
        self.client = CVSClient(self.CVSROOT)

        SCMTool.__init__(self, repository)

    def get_file(self, path, revision=HEAD):
        if not path:
            raise FileNotFoundError(path, revision)

        return self.client.cat_file(path, revision)

    def parse_diff_revision(self, file_str, revision_str):
        if revision_str == "PRE-CREATION":
            return file_str, PRE_CREATION

        m = self.regex_rev.match(revision_str)
        if not m:
            raise SCMError("Unable to parse diff revision header '%s'" %
                           revision_str)
        return file_str, m.group(1)

    def get_diffs_use_absolute_paths(self):
        return True

    def get_fields(self):
        return ['diff_path']

    def get_parser(self, data):
        return CVSDiffParser(data, self.repopath)


class CVSDiffParser(DiffParser):
    """
        This class is able to parse diffs created with CVS.
    """

    regex_small = re.compile('^RCS file: (.+)$')

    def __init__(self, data, repo):
        DiffParser.__init__(self, data)
        self.regex_full = re.compile('^RCS file: %s/(.*),v$' % re.escape(repo))

    def parse_special_header(self, linenum, info):
        linenum = super(CVSDiffParser, self).parse_special_header(linenum, info)

        if 'index' not in info:
            # We didn't find an index, so the rest is probably bogus too.
            return linenum

        m = self.regex_full.match(self.lines[linenum])
        if not m:
            m = self.regex_small.match(self.lines[linenum])

        if m:
            info['filename'] = m.group(1)
            linenum += 1
        else:
            raise DiffParserError('Unable to find RCS line', linenum)

        while self.lines[linenum].startswith('retrieving '):
            linenum += 1

        if self.lines[linenum].startswith('diff '):
            linenum += 1

        return linenum

    def parse_diff_header(self, linenum, info):
        linenum = super(CVSDiffParser, self).parse_diff_header(linenum, info)

        if info.get('origFile') == '/dev/null':
            info['origFile'] = info['newFile']
            info['origInfo'] = 'PRE-CREATION'
        elif 'filename' in info:
            info['origFile'] = info['filename']

        return linenum


class CVSClient:
    def __init__(self, repository):
        self.tempdir = ""
        self.currentdir = os.getcwd()
        self.repository = repository

    def cleanup(self):
        if self.currentdir != os.getcwd():
            # Restore current working directory
            os.chdir(self.currentdir)
            # Remove temporary directory
            if self.tempdir != "":
                os.rmdir(self.tempdir)

    def cat_file(self, filename, revision):
        # Somehow CVS sometimes seems to write .cvsignore files to current
        # working directory even though we force stdout with -p.
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

        p = subprocess.Popen(['cvs', '-d', self.repository, 'checkout',
                              '-r', str(revision), '-p', filename],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=True)
        contents = p.stdout.read()
        errmsg = p.stderr.read()
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
        if not errmsg or \
           errmsg.startswith('cvs checkout: cannot find module') or \
           errmsg.startswith('cvs checkout: could not read RCS file'):
            self.cleanup()
            raise FileNotFoundError(filename, revision)

        # Otherwise, if there's an exit code, or errmsg doesn't look like
        # successful header, then call it a generic SCMError.
        if failure or not errmsg.startswith('=========='):
            self.cleanup()
            raise SCMError(errmsg)

        self.cleanup()
        return contents
