import re
import subprocess

from reviewboard.diffviewer.parser import DiffParser

try:
    from p4 import P4Error
except ImportError:
    pass

from reviewboard.scmtools.core import SCMTool, ChangeSet, HEAD, PRE_CREATION

class PerforceTool(SCMTool):
    def __init__(self, repository):
        SCMTool.__init__(self, repository)

        import p4
        self.p4 = p4.P4()
        self.p4.port = str(repository.mirror_path or repository.path)
        self.p4.user = str(repository.username)
        self.p4.password = str(repository.password)

        # We defer actually connecting until just before we do some operation
        # that requires an active connection to the perforce depot.  This
        # connection is then left open as long as possible.

        self.uses_atomic_revisions = True

    def __del__(self):
        try:
            self._disconnect()
        except P4Error:
            # Exceptions in __del__ get ignored but spew warnings.  If there's
            # no internet connection, we'll get a P4Error from disconnect().
            # This is totally safe to ignore.
            pass

    def _connect(self):
        if not self.p4.connected:
            self.p4.connect()

    def _disconnect(self):
        try:
            if self.p4.connected:
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
        return self.parse_change_desc(changeset, changesetid)

    def get_diffs_use_absolute_paths(self):
        return True

    def get_file(self, path, revision=HEAD):
        if revision == PRE_CREATION:
            return ''

        if revision == HEAD:
            file = path
        else:
            file = '%s#%s' % (path, revision)

        p = subprocess.Popen(
            ['p4', '-p', self.p4.port, '-u', self.p4.user, 'print', '-q', file],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        (res, errdata) = p.communicate()
        failure = p.poll()

        if failure:
            error = errdata.splitlines()
            # The command-line output is the same as the contents of a P4Error
            # except they're prefixed with a line that says "Perforce client
            # error:", and the lines of the error are indented with tabs.
            raise P4Error('\n'.join(line[1:] for line in error[1:]))
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
        changeset.username = changedesc[0].split(' ')[3].split('@')[0]

        description = '\n'.join(changedesc[1:])
        file_header = re.search('Affected files ...', description)

        desc = None
        for line in description[:file_header.start()].split('\n'):
            if line.startswith('\t'):
                line = line[1:]
            if desc:
                desc += '\n' + line.rstrip()
            else:
                desc = line.rstrip()
        changeset.description = desc.rstrip()
        changeset.files = filter(lambda x: len(x),
            [x.strip().split('#', 1)[0] for x in
                description[file_header.end():].split('\n')])

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
