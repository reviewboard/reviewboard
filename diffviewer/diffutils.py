import difflib
import math
import os
import popen2
import tempfile

def patch(diff, file, filename):
    """Apply a diff to a file.  Delegates out to `patch` because noone
       except Larry Wall knows how to patch."""
    (fd, oldfile) = tempfile.mkstemp()
    f = os.fdopen(fd, "w+b")
    f.write(file)
    f.close()

    newfile = '%s-new' % oldfile
    p = popen2.Popen3('patch -o %s %s' % (newfile, oldfile))
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
        return (None, None)

    s = difflib.SequenceMatcher(None, oldline, newline)
    oldchanges = []
    newchanges = []
    back = (0, 0)

    # This thresholds our results -- we don't want to show inter-line diffs if
    # most of the line has changed, unless those lines are very short.
    opcodes = s.get_opcodes()

    # FIXME: just a plain, linear threshold is pretty crummy here.  Short
    # changes in a short line get lost.  I haven't yet thought of a fancy
    # nonlinear test.
    if s.ratio() < 0.6:
        return (None, None)

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            if (i2 - i1 < 3) or (j2 - j1 < 3):
                back = (j2 - j1, i2 - i1)
            continue

        oldstart, oldend = i1 - back[0], i2
        newstart, newend = j1 - back[1], j2

        if oldchanges != [] and oldstart <= oldchanges[-1][1] < oldend:
            oldchanges[-1] = (oldchanges[-1][0], oldend)
        elif not oldline[oldstart:oldend].isspace():
            oldchanges.append((oldstart, oldend))

        if newchanges != [] and newstart <= newchanges[-1][1] < newend:
            newchanges[-1] = (newchanges[-1][0], newend)
        elif not newline[newstart:newend].isspace():
            newchanges.append((newstart, newend))

        back = (0, 0)

    return (oldchanges, newchanges)
