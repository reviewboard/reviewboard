import re
import subprocess

try:
    from P4 import P4Error
except ImportError:
    pass

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.core import SCMTool, ChangeSet, \
                                      HEAD, PRE_CREATION
from reviewboard.scmtools.errors import SCMError, EmptyChangeSetError


class PerforceTool(SCMTool):
    name = "Perforce"
    uses_atomic_revisions = True
    supports_authentication = True

    def __init__(self, repository):
        SCMTool.__init__(self, repository)

        import P4
        self.p4 = P4.P4()
        self.p4.port = str(repository.mirror_path or repository.path)
        self.p4.user = str(repository.username)
        self.p4.password = str(repository.password)
        self.p4.exception_level = 1

        # We defer actually connecting until just before we do some operation
        # that requires an active connection to the perforce depot.  This
        # connection is then left open as long as possible.

    def __del__(self):
        try:
            self._disconnect()
        except P4Error:
            # Exceptions in __del__ get ignored but spew warnings.  If there's
            # no internet connection, we'll get a P4Error from disconnect().
            # This is totally safe to ignore.
            pass

    def _connect(self):
        if not self.p4.connected():
            self.p4.connect()

    def _disconnect(self):
        try:
            if self.p4.connected():
                self.p4.disconnect()
        except AttributeError:
            pass

    def get_pending_changesets(self, userid):
        self._connect()
        return map(self.get_changeset,
                   [x.split()[1] for x in
                       self.p4.run_changes('-s', 'pending', '-u', userid)])

    def get_changeset(self, changesetid):
        self._connect()
        changeset = self.p4.run_describe('-s', str(changesetid))
        self._disconnect()

        if changeset:
            return self.parse_change_desc(changeset[0], changesetid)
        return None

    def get_diffs_use_absolute_paths(self):
        return True

    def get_file(self, path, revision=HEAD):
        if revision == PRE_CREATION:
            return ''

        if revision == HEAD:
            file = path
        else:
            file = '%s#%s' % (path, revision)

        cmdline = ['p4', '-p', self.p4.port]
        if self.p4.user:
            cmdline.extend(['-u', self.p4.user])
        if self.p4.password:
            cmdline.extend(['-P', self.p4.password])
        cmdline.extend(['print', '-q', file])

        p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        (res, errdata) = p.communicate()
        failure = p.poll()

        if failure:
            error = errdata.splitlines()
            # The command-line output is the same as the contents of a P4Error
            # except they're prefixed with a line that says "Perforce client
            # error:", and the lines of the error are indented with tabs.
            if error[0].startswith("Perforce client error:"):
                error = error[1:]

            raise SCMError('\n'.join(line.lstrip("\t") for line in error))
        else:
            return res

    def parse_diff_revision(self, file_str, revision_str):
        # Perforce has this lovely idiosyncracy that diffs show revision #1 both
        # for pre-creation and when there's an actual revision.
        self._connect()

        filename, revision = revision_str.rsplit('#', 1)
        files = self.p4.run_files(revision_str)

        if len(files) == 0:
            revision = PRE_CREATION

        self._disconnect()

        return filename, revision

    def get_filenames_in_revision(self, revision):
        return self.get_changeset(revision).files

    @staticmethod
    def parse_change_desc(changedesc, changenum):
        if not changedesc:
            return None

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
        # We parse the username out of the first line to check that one user
        # isn't attempting to "claim" another's changelist.  We then split
        # everything around the 'Affected files ...' line, and process the
        # results.
        changeset.username = changedesc['user']
        changeset.description = changedesc['desc']

        try:
            changeset.files = changedesc['depotFile']
        except KeyError:
            raise EmptyChangeSetError(changenum)

        split = changeset.description.find('\n\n')
        if split >= 0 and split < 100:
            changeset.summary = \
                changeset.description.split('\n\n', 1)[0].replace('\n', ' ')
        else:
            changeset.summary = changeset.description.split('\n', 1)[0]

        return changeset

    def get_fields(self):
        return ['changenum', 'diff_path']

    def get_parser(self, data):
        return PerforceDiffParser(data)


class PerforceDiffParser(DiffParser):
    SPECIAL_REGEX = re.compile("^==== ([^#]+)#(\d+) ==([AMD])== (.*) ====$")

    def __init__(self, data):
        DiffParser.__init__(self, data)

    def parse_diff_header(self, linenum, info):
        m = self.SPECIAL_REGEX.match(self.lines[linenum])
        if m:
            info['origFile'] = m.group(1)
            info['origInfo'] = "%s#%s" % (m.group(1), m.group(2))
            info['newFile'] = m.group(4)
            info['newInfo'] = ""
            linenum += 1

            if linenum < len(self.lines) and \
               (self.lines[linenum].startswith("Binary files ") or
                self.lines[linenum].startswith("Files ")):
                info['binary'] = True
                linenum += 1

            # In this case, this *is* our diff header. We don't want to
            # let the next line's real diff header be a part of this one,
            # so return early and don't invoke the next.
            return linenum

        return super(PerforceDiffParser, self).parse_diff_header(linenum, info)
