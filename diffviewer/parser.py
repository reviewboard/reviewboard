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
        raise Exception('Unable to parse file.  Is this a diff?')

    if lines[lastline].startswith("diff "):
        lastline -= 1
    elif lines[lastline].startswith("====================") and \
         lines[lastline - 1].startswith("Index: "):
        lastline -= 2

    file.data = '\n'.join(lines[linenum:lastline])

    return file


def parse(data):
    p = Popen3('lsdiff -n')
    p.tochild.write(data)
    p.tochild.close()
    r = p.fromchild.read().strip()
    ret = p.wait()

    if ret:
        raise Exception('Error running lsdiff')

    lines = data.splitlines()
    files = []

    info = [line.split() for line in r.splitlines()]
    for current, next in zip(info, info[1:] + [[len(lines), '']]):
        begin = int(current[0]) - 1
        end = int(next[0]) - 1
        file = current[1]

        files.append(parseFile(lines, begin, end, file))

    return files
