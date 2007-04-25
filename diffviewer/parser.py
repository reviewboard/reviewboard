from popen2 import Popen3

class File:
    def __init__(self):
        self.origFile = None
        self.newFile = None
        self.origInfo = None
        self.newInfo = None
        self.data = None


def parseFile(lines, linenum, lastline, filename):
    file = File()

    if (lines[linenum].startswith('--- ') and \
        lines[linenum + 1].startswith('+++ ')) or \
       (lines[linenum].startswith('*** ') and \
        lines[linenum + 1].startswith('--- ')):

        # Unified or Context diff
        file.origFile, file.origInfo = lines[linenum].split(None, 2)[1:]
        file.newFile,  file.newInfo  = lines[linenum + 1].split(None, 2)[1:]
    else:
        raise Exception('Unable to recognize diff format')

    file.data = ""

    for i in range(linenum, lastline):
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


def parse(data):
    p = Popen3('lsdiff -n')
    p.tochild.write(data)
    p.tochild.close()
    r = p.fromchild.read().strip()
    failure = p.wait()

    if failure:
        raise Exception('Error running lsdiff')

    lines = data.splitlines()
    files = []

    current_slice = r.splitlines()
    next_slice = current_slice[1:] + ['%d' % len(lines)]
    for current, next in zip(current_slice, next_slice):
        begin, file = current.split()
        end = next.split()[0]

        files.append(parseFile(lines, int(begin) - 1, int(end) - 1, file))

    return files
