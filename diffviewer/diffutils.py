import difflib
import os
from popen2 import Popen3
import tempfile

def patch(diff, file, filename):
    """Apply a diff to a file.  Delegates out to `patch` because noone
       except Larry Wall knows how to patch."""
    (fd, oldfile) = tempfile.mkstemp()
    f = os.fdopen(fd, "w+b")
    f.write(file)
    f.close()

    newfile = '%s-new' % oldfile
    p = Popen3('patch -o %s %s' % (newfile, oldfile))
    p.tochild.write(diff)
    p.tochild.close()
    failure = p.wait()

    if failure:
        os.unlink(oldfile)
        os.unlink(newfile)

        try:
            os.unlink(newfile + ".rej")
        except:
            pass

        raise Exception(("The patch to '%s' didn't apply cleanly. " +
                         "`patch` returned: %s") %
                        (filename, p.fromchild.read()))

    f = open(newfile, "r")
    data = f.read()
    f.close()

    os.unlink(oldfile)
    os.unlink(newfile)

    return data


def get_line_changed_regions(oldline, newline):
    if oldline is None or newline is None:
        return [None, None]

    s = difflib.SequenceMatcher(None, oldline, newline)
    oldchanges = []
    newchanges = []
    back = (0, 0)

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            if (i2 - i1 < 10) or (j2 - j1 < 10):
                back = (j2 - j1, i2 - i1)
            continue

        oldchanges.append((i1 - back[0], i2))
        newchanges.append((j1 - back[1], j2))
        back = (0, 0)

    return [oldchanges, newchanges]
