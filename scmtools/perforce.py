import os
import re
import popen2

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

        self.uses_atomic_revisions = True

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
        return self.parse_change_desc(
            self.p4.run_describe('-s', str(changesetid)),
            changesetid)

    def get_diffs_use_absolute_paths(self):
        return True

    def get_file(self, path, revision=HEAD):
        self._connect()

        if revision == PRE_CREATION:
            return ''

        if revision == HEAD:
            file = path
        else:
            file = '%s#%s' % (path, revision)

        f = os.popen('p4 -p %s -u %s print -q %s' % (settings.P4_PORT,
                                                     settings.P4_USER, file))
        data = f.read()
        failure = f.close()

        if failure:
            raise Exception('unable to fetch %s from perforce' % file)

        return data

        return '\n'.join(self.p4.run_print(file)[1:])

    def parse_diff_revision(self, file_str, revision_str):
        # Perforce has this lovely idiosyncracy that diffs show revision #1 both
        # for pre-creation and when there's an actual revision.
        self._connect()

        filename, revision = revision_str.rsplit('#', 1)
        files = self.p4.run_files(revision_str)

        if len(files) == 0:
            revision = PRE_CREATION

        return filename, revision

    def get_filenames_in_revision(self, revision):
        return self.get_changeset(revision).files

    @staticmethod
    def parse_change_desc(changedesc, changenum):
        changeset = ChangeSet()
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
        # We start by chopping off the first line (which we don't care about
        # right now).  We then split everything around the 'Affected files ...'
        # line, and process the results.
        description = '\n'.join(changedesc[1:])
        file_header = re.search('Affected files ...', description)

        changeset.description = '\n'.join([x.strip() for x in
                description[:file_header.start()].split('\n')]).strip()
        changeset.summary = changeset.description.split('\n', 1)[0]
        changeset.files = filter(lambda x: len(x),
            [x.strip().split('#', 1)[0] for x in
                description[file_header.end():].split('\n')])

        return changeset
