import re
import subprocess

from reviewboard.diffviewer.parser import DiffParser, DiffParserError
from reviewboard.scmtools.core import \
    FileNotFoundError, SCMError, SCMTool, HEAD, PRE_CREATION


class GitTool(SCMTool):
    """
    You can only use this tool with a locally available git repository.
    The repository path should be to the .git directory (important if
    you do not have a bare repositry).
    """
    def __init__(self, repository):
        SCMTool.__init__(self, repository)
        self.client = GitClient(repository.path)

    def _resolve_head(self, revision, path):
        if revision == HEAD:
            if path == "":
                raise SCMError("path must be supplied if revision is %s" % HEAD)
            return "HEAD:%s" % path
        else:
            return revision

    def get_file(self, path, revision=HEAD):
        if revision == PRE_CREATION:
            return ""

        return self.client.cat_file(self._resolve_head(revision, path))

    def file_exists(self, path, revision=HEAD):
        if revision == PRE_CREATION:
            return False

        try:
            type = self.client.cat_file(self._resolve_head(revision, path), option="-t")
            return type and type.strip() == "blob"
        except FileNotFoundError:
            return False

    def parse_diff_revision(self, file_str, revision_str):
        revision = revision_str
        if file_str == "/dev/null":
            revision = PRE_CREATION
        return file_str, revision

    def get_diffs_use_absolute_paths(self):
        return True

    def get_fields(self):
        return ['diff_path']

    def get_parser(self, data):
        return GitDiffParser(data)


class GitDiffParser(DiffParser):
    """
    This class is able to parse diffs created with Git
    """
    pre_creation_regexp = re.compile("^0+$")

    def parse_special_header(self, linenum, info):
        line = self.lines[linenum]

        # check for the special case where we only have a "new file mode"
        # with no actual diff content - we want to skip it
        # NOTE this will cause the empty header to go into the previous
        # changeset, but there's no way of avoiding that without changing
        # parser.py, and "patch" will just ignore it.
        if linenum + 3 < len(self.lines) and \
                self.lines[linenum].startswith("diff --git") and \
                self.lines[linenum + 1].startswith("new file mode") and \
                self.lines[linenum + 3].startswith("diff --git"):
            linenum += 2

        if self.lines[linenum].startswith("diff --git"):
            diffLine = self.lines[linenum].split()
            try:
                # need to remove the "a/" and "b/" prefix
                info['origFile'] = diffLine[-2][2:]
                info['newFile'] = diffLine[-1][2:]
            except ValueError:
                raise DiffParserError(
                    "The diff file is missing revision information",
                    linenum)
            linenum += 1

        if self.lines[linenum].startswith("new file mode") \
                or self.lines[linenum].startswith("deleted file mode"):
            linenum += 1

        if self.lines[linenum].startswith("index "):
            indexRange = self.lines[linenum].split(None, 2)[1]
            info['origInfo'], info['newInfo'] = indexRange.split("..")
            if self.pre_creation_regexp.match(info['origInfo']):
                info['origInfo'] = PRE_CREATION
            linenum += 1

        return linenum

    def parse_diff_header(self, linenum, info):
        if self.lines[linenum].startswith("Binary files") or \
           self.lines[linenum].startswith("GIT binary patch"):
            info['binary'] = True
            linenum += 1;

        if linenum + 1 < len(self.lines) and \
           (self.lines[linenum].startswith('--- ') and \
             self.lines[linenum + 1].startswith('+++ ')):
            # check if we're a new file
            if self.lines[linenum].split()[1] == "/dev/null":
                info['origInfo'] = PRE_CREATION
            linenum += 2;

        return linenum


class GitClient:
    def __init__(self, path):
        self.path = path

        # FIXME: it'd be nice to check the existence of the 'git' binary so we
        # can skip tests

    def cat_file(self, commit, option="blob"):
        """
        Call git-cat-file(1) to get content or type information for a
        repository object.

        If called with just "commit", gets the content of a blob (or
        raises an exception if the commit is not a blob).

        Otherwise, "option" can be used to pass a switch to git-cat-file,
        e.g. to test or existence or get the type of "commit".
        """
        p = subprocess.Popen(
            ['git', '--git-dir=%s' % self.path, 'cat-file',
                 '%s' % option, '%s' % commit],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE, close_fds=True
        )
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            if errmsg.startswith("fatal: Not a valid object name"):
                raise FileNotFoundError(commit)
            else:
                raise SCMError(errmsg)

        return contents
