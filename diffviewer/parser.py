import re

class File:
    def __init__(self):
        self.origFile = None
        self.newFile = None
        self.origInfo = None
        self.newInfo = None
        self.data = None


def parseFile(lines, linenum, lastline, filename):
    file = File()
    file.origFile

    if lines[linenum].startswith('--- '):
        junk, file.origFile, file.origInfo = lines[linenum].split(' ', 3)
        junk, file.newFile,  file.newInfo  = lines[linenum + 1].split(' ', 3)
    else:
        raise "WTF is this diff file format?"

    file.data = '\n'.join(lines[linenum:lastline])

    return file


def parse(data):
    p = Popen3('lsdiff -n')
    p.tochild.write(data)
    p.tochild.close()
    r = p.fromchild.read()
    ret = p.wait()

    lines = data.splitlines()
    files = []

    if ret != 0:
        info = [(linenum, filename) for linenum, filename in
                map(str.split, r.splitlines())]

        numFiles = len(info)

        for i in range(0, numFiles):
            (linenum, filename) = info[i]

            if i == numFiles - 1:
                lastline = len(lines)
            else:
                lastline = info[i + 1][0]

            files.append(parseFile(lines, linenum, lastline, filename))

    return files
