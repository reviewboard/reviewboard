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


def parseFile(lines, linenum, lastline, filename):
    file = File()

    if (lines[linenum].startswith('--- ') and \
        lines[linenum + 1].startswith('+++ ')) or \
       (lines[linenum].startswith('*** ') and \
        lines[linenum + 1].startswith('--- ')):

        # Unified or Context diff
        try:
            file.origFile, file.origInfo = lines[linenum].split(None, 2)[1:]
            file.newFile,  file.newInfo  = lines[linenum + 1].split(None, 2)[1:]
        except ValueError:
            raise Exception("The diff file is missing revision information")
    else:
        raise Exception('Unable to recognize diff format')

    file.data = ""

    for i in range(linenum, lastline + 1):
        line = lines[i]
        if line.startswith("diff ") or \
           (line.startswith("Index: ") and \
            lines[i + 1].startswith("====================")) or \
           (line.startswith("Property changes on: ") and \
            lines[i + 1].startswith("____________________")):
            break
        else:
            file.data += line + "\n"

    return file


def parseSpecialHeader(line):
    file = None

    m = re.match("^==== ([^#]+)#(\d+) ==([AMD])== (.*) ====$", line)
    if m:
        file = File()
        file.origFile = m.group(4)
        file.origInfo = "%s#%s" % (m.group(1), m.group(2))
        file.newFile = m.group(4)
        file.newInfo = ""
        file.data = ""

    return file


def parse(data):
    def checkSpecialHeaders(begin):
        # Try to see if we have special "====" markers before this.
        if begin >= 2 and lines[begin - 2].startswith("==== ") and \
           lines[begin - 1].startswith("Binary files "):
            print "Found binary"
            # Okay, binary files. Let's flag it.
            # We know this isn't related to the next file lsdiff gave us,
            # because we wouldn't get this message *and* content.
            newfileinfo = parseSpecialHeader(lines[begin - 2])

            if newfileinfo:
                newfileinfo.binary = True
                files.append(newfileinfo)
        elif begin >= 1 and lines[begin - 1].startswith("==== "):
            # Is this different than the file lsdiff reported around here?
            newfileinfo = parseSpecialHeader(lines[begin - 1])

            if newfileinfo and \
               newfileinfo.origFile != fileinfo.origFile and \
               newfileinfo.newFile != fileinfo.newFile:
                # Okay, it's a new file with no content.
                files.append(newfileinfo)


    p = subprocess.Popen(['lsdiff', '-n'], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, close_fds=True)
    p.stdin.write(data)
    p.stdin.close()
    r = p.stdout.read().strip()
    failure = p.wait()

    if failure:
        raise Exception('Error running lsdiff')

    lines = data.splitlines()
    files = []

    current_slice = r.splitlines()
    next_slice = current_slice[1:] + ['%d' % len(lines)]
    for current, next in zip(current_slice, next_slice):
        # Get the part lsdiff reported
        begin, file = current.split()
        end = next.split()[0]

        # lsdiff's line numbers are 1-based. We want 0-based.
        begin = int(begin) - 1
        end = int(end) - 1

        fileinfo = parseFile(lines, begin, end, file)
        checkSpecialHeaders(begin)
        files.append(fileinfo)

    checkSpecialHeaders(len(lines))

    return files
