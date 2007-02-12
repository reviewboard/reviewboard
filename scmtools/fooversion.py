from reviewboard.scmtools.core import SCMException, FileNotFoundException, HEAD
from reviewboard.scmtools.core import SCMTool, ChangeSet
from reviewboard.scmtools.svn import SVNTool
import os

class FooVersionTool(SVNTool):
    """
    Hacky testing version control tool that subclasses the SVN tool in
    order to get files and fills the rest with rubbish.
    """
    def __init__(self, repopath):
        SVNTool.__init__(self, repopath)

    def get_changeset(self, changesetid):
        changedesc = ChangeSet()
        changedesc.bugs_closed = ['456123', '12873', '1298371']

        if not os.popen('fortune').close():
            changedesc.summary = os.popen('fortune -s').readline()
            changedesc.description = os.popen('fortune').read()
            changedesc.testing_done = os.popen('fortune').read()
        else:
            changedesc.summary = 'This is my summary.'
            changedesc.description = 'Blah blah blah.'
            changedesc.testing_done = \
                'I ate a hamburger and thought, \"Wow, that was rad.\"'
        return changedesc

    def get_pending_changesets(self, userid):
        # XXX: this is broken
        return [parse_change_desc("12345"),
                parse_change_desc("314150"),
                parse_change_desc("202020")]
