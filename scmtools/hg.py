import re
import os

from reviewboard.diffviewer.parser import \
    DiffParser, DiffParserError, File
from reviewboard.scmtools.core import \
    FileNotFoundError, SCMError, SCMTool, HEAD, PRE_CREATION

class HgTool(SCMTool):
    def __init__(self, repository):
        SCMTool.__init__(self, repository)
        self.client = HgClient(repository.path)

    def get_file(self, path, revision=HEAD):
        return self.client.cat_file(path, str(revision))

    def parse_diff_revision(self, file_str, revision_str):
        revision = revision_str
        if file_str == "/dev/null":
            revision = PRE_CREATION
        return file_str, revision

    def get_fields(self):
        return ['diff_path']

    def get_parser(self, data):
        return HgDiffParser(data)


class HgDiffParser(DiffParser):
    """
    This class is able to extract Mercurial changeset ids, and
    replaces /dev/null with a useful name
    """

    def parse_special_header(self, linenum, info):
        if self.lines[linenum].startswith("diff -r"):
            # should contain "diff -r aaa [-r bbb] filename"
            diffLine = self.lines[linenum].split()
            try:
                # hg is file based, so new file always == old file
                info['newFile'] = info['origFile'] = diffLine[-1]
                info['origInfo'] = diffLine[2]
                if len(diffLine) <= 4:
                    info['newInfo'] = "Uncommitted"
                else:
                    info['newInfo'] = diffLine[4]
            except ValueError:
                raise DiffParserError("The diff file is missing revision information",
                                      linenum)
            linenum += 1;

        return linenum

    def parse_diff_header(self, linenum, info):
        if linenum + 1 < len(self.lines) and \
           (self.lines[linenum].startswith('--- ') and \
             self.lines[linenum + 1].startswith('+++ ')):
            # check if we're a new file
            if self.lines[linenum].split()[1] == "/dev/null":
                info['origInfo'] = PRE_CREATION
            linenum += 2;
        return linenum


class HgClient:
    def __init__(self, repoPath):
        from mercurial import hg, ui
        self.repo = hg.repository(ui.ui(interactive=False), path=repoPath)

    def cat_file(self, path, rev="tip"):
        if rev == HEAD:
            rev = "tip"
        elif rev == PRE_CREATION:
            rev = ""
        try:
            return self.repo.changectx(rev).filectx(path).data()
        except Exception:
            # LookupError moves from repo to revlog in hg v0.9.4, so we
            # catch the more general Exception to avoid the dependency.
            raise FileNotFoundError(path)

    def get_filenames(self, rev):
        return self.repo.changectx(rev).TODO
