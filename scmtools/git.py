import os
import re
import subprocess

from reviewboard.diffviewer.parser import DiffParser, DiffParserError, File
from reviewboard.scmtools.core import SCMTool, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import FileNotFoundError, SCMError


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

    def parse(self):
        """
        Parses the diff, returning a list of File objects representing each
        file in the diff.
        """
        self.files = []
        i = 0
        while i < len(self.lines):
            (i, file) = self._parse_diff(i)
            if file:
                self.files.append(file)
        return self.files

    def _parse_diff(self, i):
        """
        Parses out one file from a Git diff
        """
        if self.lines[i].startswith("diff --git"):
            # First check if it is a new file with no content or
            # a file mode change with no content or
            # a deleted file with no content
            # then skip
            try:
                if ((self.lines[i + 1].startswith("new file mode") or
                     self.lines[i + 1].startswith("old mode") or
                     self.lines[i + 1].startswith("deleted file mode")) and
                    self.lines[i + 3].startswith("diff --git")):
                    i += 3
                    return i, None
            except IndexError, x:
                # This means this is the only bit left in the file
                i += 3
                return i, None

            # Now we have a diff we are going to use so get the filenames + commits
            file = File()
            file.data = self.lines[i] + "\n"
            file.binary = False
            diffLine = self.lines[i].split()
            try:
                # Need to remove the "a/" and "b/" prefix
                remPrefix = re.compile("^[a|b]/");
                file.origFile = remPrefix.sub("", diffLine[-2])
                file.newFile = remPrefix.sub("", diffLine[-1])
            except ValueError:
                raise DiffParserError(
                    "The diff file is missing revision information",
                    i)
            i += 1

            # We have no use for recording this info so skip it
            if self.lines[i].startswith("new file mode") \
               or self.lines[i].startswith("deleted file mode"):
                i += 1
            elif self.lines[i].startswith("old mode") \
                 and self.lines[i + 1].startswith("new mode"):
                i += 2

            # Get the revision info
            if i < len(self.lines) and self.lines[i].startswith("index "):
                indexRange = self.lines[i].split(None, 2)[1]
                file.origInfo, file.newInfo = indexRange.split("..")
                if self.pre_creation_regexp.match(file.origInfo):
                    file.origInfo = PRE_CREATION
                i += 1

            # Get the changes
            while i < len(self.lines):
                if self.lines[i].startswith("diff --git"):
                    return i, file

                if self.lines[i].startswith("Binary files") or \
                   self.lines[i].startswith("GIT binary patch"):
                    file.binary = True
                    return i + 1, file

                if i + 1 < len(self.lines) and \
                   (self.lines[i].startswith('--- ') and \
                     self.lines[i + 1].startswith('+++ ')):
                    if self.lines[i].split()[1] == "/dev/null":
                        file.origInfo = PRE_CREATION

                file.data += self.lines[i] + "\n"
                i += 1

            return i, file
        return i + 1, None


class GitClient:
    def __init__(self, path):
        self.path = path
        p = subprocess.Popen(
            ['git', '--git-dir=%s' % self.path, 'config',
                 'core.repositoryformatversion'],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            close_fds=(os.name != 'nt')
        )
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            raise ImportError

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
            stdout=subprocess.PIPE,
            close_fds=(os.name != 'nt')
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
