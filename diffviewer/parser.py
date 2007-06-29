import re
import subprocess

class File:
    def __init__(self):
        self.origFile = None
        self.newFile = None
        self.origInfo = None
        self.newInfo = None
        self.data = None
        self.binary = False

class DiffParserError(Exception):
    pass

class DiffParser:
    binregexp = re.compile("^==== ([^#]+)#(\d+) ==([AMD])== (.*) ====$")

    def __init__(self, data):
        self.data = data
        self.lines = data.splitlines()

    def parse(self):
        self.files = []
        p = subprocess.Popen(['lsdiff', '-n'], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)
        p.stdin.write(self.data)
        p.stdin.close()
        r = p.stdout.read().strip()
        failure = p.wait()
        if failure:
            raise DiffParserError('Error running lsdiff')
        current_slice = r.splitlines()
        next_slice = current_slice[1:] + ['%d' % len(self.lines)]
        for current, next in zip(current_slice, next_slice):
            # Get the part lsdiff reported
            begin, file = current.split()[:2]
            end = next.split()[0]

            # lsdiff's line numbers are 1-based. We want 0-based.
            begin = int(begin) - 1
            end = int(end) - 1

            fileinfo = self._parseFile(begin, end, file)
            self._checkSpecialHeaders(begin, fileinfo)
            self.files.append(fileinfo)

        self._checkSpecialHeaders(len(self.lines))

        return self.files

    def _parseFile(self, linenum, lastline, filename):
        # this usually scm/diff type specific
        file = self._extractRevisionInfo(linenum)

        file.data = ""

        for i in range(linenum, lastline + 1):
            line = self.lines[i]
            if line.startswith("diff ") or \
               (line.startswith("Index: ") and \
                self.lines[i + 1].startswith("====================")) or \
               (line.startswith("Property changes on: ") and \
                self.lines[i + 1].startswith("____________________")):
                break
            else:
                file.data += line + "\n"

        return file

    def _extractRevisionInfo(self, linenum):
        file = File()
        # check if we find a change
        if self._isChange(linenum):
            # Unified or Context diff
            self._parseRevisionInfo(linenum, file)
        else:
            raise DiffParserError('Unable to recognize diff format')
        return file

    def _isChange(self, linenum):
        return (self.lines[linenum].startswith('--- ') and \
                self.lines[linenum + 1].startswith('+++ ')) or \
               (self.lines[linenum].startswith('*** ') and \
                self.lines[linenum + 1].startswith('--- '))

    def _parseRevisionInfo(self, linenum, file):
        try:
            file.origFile, file.origInfo = self.lines[linenum].split(None, 2)[1:]
            file.newFile,  file.newInfo  = self.lines[linenum + 1].split(None, 2)[1:]
        except ValueError:
            raise DiffParserError("The diff file is missing revision information")

    def _checkSpecialHeaders(self, begin, fileinfo=None):
        # Try to see if we have special "====" markers before this.
        if begin >= 2 and self.lines[begin - 2].startswith("==== ") and \
           self.lines[begin - 1].startswith("Binary files "):
            print "Found binary"
            # Okay, binary files. Let's flag it.
            # We know this isn't related to the next file lsdiff gave us,
            # because we wouldn't get this message *and* content.
            newfileinfo = self._parseSpecialHeader(lines[begin - 2])

            if newfileinfo:
                newfileinfo.binary = True
                self.files.append(newfileinfo)
        elif begin >= 1 and self.lines[begin - 1].startswith("==== "):
            # Is this different than the file lsdiff reported around here?
            newfileinfo = self._parseSpecialHeader(lines[begin - 1])

            if newfileinfo and \
               newfileinfo.origFile != fileinfo.origFile and \
               newfileinfo.newFile != fileinfo.newFile:
                # Okay, it's a new file with no content.
                self.files.append(newfileinfo)

    def _parseSpecialHeader(self, line):
        file = None

        m = self.__class__.binregexp.match(line)
        if m:
            file = File()
            file.origFile = m.group(4)
            file.origInfo = "%s#%s" % (m.group(1), m.group(2))
            file.newFile = m.group(4)
            file.newInfo = ""
            file.data = ""

        return file
