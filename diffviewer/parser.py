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
        junk, file.origFile, file.origInfo = lines[linenum].split(None, 2)
        junk, file.newFile,  file.newInfo  = lines[linenum + 1].split(None, 2)
    else:
        raise "WTF is this diff file format?"

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

    lines = data.splitlines()
    files = []

    if ret == 0:
        info = []

        for line in r.splitlines():
            info.append(line.split())

        numFiles = len(info)

        for i in range(numFiles):
            [linenum, filename] = info[i]

            if i == numFiles - 1:
                lastline = len(lines)
            else:
                lastline = info[i + 1][0]

            files.append(parseFile(lines, int(linenum) - 1,
                                   int(lastline) - 1, filename))

    return files
