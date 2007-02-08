from reviewboard.scmtools.core import SCMException, FileNotFoundException, HEAD, SCMTool
from reviewboard.scmtools.svn import SVNTool
from reviewboard.scmtools.perforce import PerforceTool
import os

class FooVersionTool(SVNTool):
    """
    Hacky testing version control tool that subclasses the SVN tool in
    order to get files and calls out to the PerforceTool to parse fake
    changesets.
    """
    def __init__(self, repopath):
        SVNTool.__init__(self, repopath)

    def get_changeset(self, changesetid):
        changedesc = "\
Description:\n\
    This is my summary.\n\
    \n\
    This is a body of text, which can\n\
    wrap to the next line.\n\
\n\
    And skip lines.\n\
    \n\
\n\
    QA Notes:\n\
    Testing Done: I ate a hamburger and thought, \"Wow, that was rad.\"\n\
    Note how it carries to the next line, since some people do that.\n\
    Bug Number: 456123, 12873  1298371\n\
\n\
Files:\n\
    //depot/bora/foo/apps/lib/foo.c\n\
    //depot/bora/foo/apps/lib/bar.c\n\
"
        changedesc = PerforceTool.parse_change_desc(changesetid, changedesc)

        if not os.popen('fortune').close():
            changedesc.summary = os.popen('fortune -s').readline()
            changedesc.description = os.popen('fortune').read()
            changedesc.testing_done = os.popen('fortune').read()
        return changedesc

    def get_pending_changesets(self, userid):
        return [parse_change_desc("12345"),
                parse_change_desc("314150"),
                parse_change_desc("202020")]
