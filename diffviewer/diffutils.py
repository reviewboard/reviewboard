import difflib
import math
import os
import popen2
import tempfile

def diff(a, b):
    """
    Wrapper around SequenceMatcher that works around bugs in how it does
    its matching.
    """
    matcher = difflib.SequenceMatcher(None, a, b).get_opcodes()

    for tag, i1, i2, j1, j2 in matcher:
        if tag == 'replace':
            oldlines = a[i1:i2]
            newlines = b[j1:j2]

            i = 0
            j = 0
            i_start = 0
            j_start = 0

            while i < len(oldlines) and j < len(newlines):
                new_tag = None
                new_i = i
                new_j = j

                if oldlines[i] == "" and newlines[j] == "":
                    new_tag = "equal"
                    new_i += 1
                    new_j += 1
                elif oldlines[i] == "":
                    new_tag = "insert"
                    new_j += 1
                elif newlines[j] == "":
                    new_tag = "delete"
                    new_i += 1
                else:
                    new_tag = "replace"
                    new_i += 1
                    new_j += 1

                if new_tag != tag:
                    if i > i_start or j > j_start:
                        yield tag, i1 + i_start, i1 + i, j1 + j_start, j1 + j

                    tag = new_tag
                    i_start = i
                    j_start = j

                i = new_i
                j = new_j

            yield tag, i1 + i_start, i1 + i, j1 + j_start, j1 + j
            i_start = i
            j_start = j

            if i2 > i1 + i_start or j2 > j1 + j_start:
                tag = None

                if len(oldlines) > len(newlines):
                    tag = "delete"
                elif len(oldlines) < len(newlines):
                    tag = "insert"

                if tag != None:
                    yield tag, i1 + i_start, i2, j1 + j_start, j2
        else:
            yield tag, i1, i2, j1, j2


def patch(diff, file, filename):
    """Apply a diff to a file.  Delegates out to `patch` because noone
       except Larry Wall knows how to patch."""

    if diff == "":
        # Someone uploaded an unchanged file. Return the one we're patching.
        return file

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
            pass #os.unlink(newfile + ".rej")
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
