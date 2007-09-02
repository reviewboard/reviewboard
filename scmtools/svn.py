import re

try:
    from pysvn import ClientError, Revision, opt_revision_kind
except ImportError:
    pass

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.core import \
    SCMError, FileNotFoundError, SCMTool, HEAD, PRE_CREATION, UNKNOWN

class SVNTool(SCMTool):
    def __init__(self, repository):
        self.repopath = repository.path
        if self.repopath[-1] == '/':
            self.repopath = self.repopath[:-1]

        SCMTool.__init__(self, repository)

        import pysvn
        self.client = pysvn.Client()
        if repository.username:
            self.client.set_default_username(str(repository.username))
        if repository.password:
            self.client.set_default_password(str(repository.password))

        self.uses_atomic_revisions = True

        # svnlook uses 'rev 0', while svn diff uses 'revision 0'
        self.revision_re = re.compile("""
            ^(\(([^\)]+)\)\s)?           # creating diffs between two branches
                                         # of a remote repository will insert
                                         # extra "relocation information" into
                                         # the diff.

            (?:\d+-\d+-\d+\ +            # svnlook-style diffs contain a
               \d+:\d+:\d+\ +            # timestamp on each line before the
               [A-Z]+\ +)?               # revision number.  This here is
                                         # probably a really crappy way to
                                         # express that, but oh well.

            \(rev(?:ision)?\ (\d+)\)$    # svnlook uses 'rev 0' while svn diff
                                         # uses 'revision 0'
            """, re.VERBOSE)


    def get_file(self, path, revision=HEAD):
        if not path:
            raise FileNotFoundError(path, revision)

        try:
            return self.client.cat(self.__normalize_path(path),
                                   self.__normalize_revision(revision))
        except ClientError, e:
            stre = str(e)
            if stre.find('path not found'):
                raise FileNotFoundError(path, revision, str(e))
            elif stre.find('callback_ssl_server_trust_prompt required'):
                raise SCMError(
                    'HTTPS certificate not accepted.  Please ensure that ' +
                    'the proper certificate exists in ~/.subversion/auth ' +
                    'for the user that reviewboard is running as.')
            else:
                raise SCMError(e)


    def parse_diff_revision(self, file_str, revision_str):
        if revision_str == "(working copy)":
            return file_str, HEAD

        # Binary diffs don't provide revision information, so we set a fake
        # "(unknown)" in the SVNDiffParser. This will never actually appear
        # in SVN diffs.
        if revision_str == "(unknown)":
            return file_str, UNKNOWN

        m = self.revision_re.match(revision_str)
        if not m:
            raise SCMError("Unable to parse diff revision header '%s'" %
                           revision_str)

        relocated_file = m.group(2)
        revision = m.group(3)

        if revision == "0":
            revision = PRE_CREATION

        if relocated_file:
            if not relocated_file.startswith("..."):
                raise SCMError("Unable to parse SVN relocated path '%s'" %
                               relocated_file)

            file_str = "%s/%s" % (relocated_file[4:], file_str)

        return file_str, revision


    def get_filenames_in_revision(self, revision):
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
            r = Revision(opt_revision_kind.number, str(revision))

        return r

    def __normalize_path(self, path):
        if path.startswith(self.repopath):
            return path
        elif path[0] == '/':
            return self.repopath + path
        else:
            return self.repopath + "/" + path

    def get_fields(self):
        return ['basedir', 'diff_path']

    def get_parser(self, data):
        return SVNDiffParser(data)


class SVNDiffParser(DiffParser):
    BINARY_STRING = "Cannot display: file marked as a binary type."

    def __init__(self, data):
        DiffParser.__init__(self, data)

    def parse_special_header(self, linenum, info):
        linenum = super(SVNDiffParser, self).parse_special_header(linenum, info)

        if 'index' in info:
            if self.lines[linenum] == self.BINARY_STRING:
                # Skip this and the svn:mime-type line.
                linenum += 2
                info['binary'] = True
                info['origFile'] = info['index']
                info['newFile'] = info['index']

                # We can't get the revision info from this diff header.
                info['origInfo'] = '(unknown)'
                info['newInfo'] = '(working copy)'

        return linenum
