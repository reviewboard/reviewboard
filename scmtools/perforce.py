import re

from django.conf import settings

from reviewboard.scmtools.core import *

class PerforceTool(SCMTool):
    def __init__(self,
                 p4port = settings.P4_PORT,
                 p4user = settings.P4_USER,
                 p4password = settings.P4_PASSWORD):
        SCMTool.__init__(self, p4port)

        import p4
        self.p4 = p4.P4()
        self.p4.port = p4port
        self.p4.user = p4user
        self.p4.password = p4password

        # We defer actually connecting until just before we do some operation
        # that requires an active connection to the perforce depot.  This
        # connection is then left open as long as possible.
        self.connected = False

    def _connect(self):
        if not self.connected or self.p4.dropped():
            self.p4.connect()
            self.connected = True

    def get_pending_changesets(self, userid):
        self._connect()
        return map(self.get_changeset,
                   [x.split()[1] for x in
                       self.p4.run_changes('-s', 'pending', '-u', userid)])

    def get_changeset(self, changesetid):
        self._connect()
        return parse_change_desc(
            '\n'.join(self.p4.run_describe('-s', str(changesetid))),
            changesetid)

    def get_file(self, path, revision=None):
        self._connect()

        file = path
        if revision:
            if revision == PRE_CREATION:
                file = '%s@0' % path
            elif revision == HEAD:
                pass
            else:
                file = '%s@%s' % (path, revision)

        return '\n'.join(self.p4.run_print(path))

    @staticmethod
    def parse_change_desc(changedesc, changenum):
        changeset = ChangeSet()
        changeset.changenum = changenum

        # FIXME: parse what little perforce gives us

        return changeset
