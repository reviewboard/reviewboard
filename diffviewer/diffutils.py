import os
import subprocess
import tempfile

from difflib import SequenceMatcher
from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.smdiff import SMDiffer


DEFAULT_DIFF_COMPAT_VERSION = 1


def Differ(a, b, ignore_space=False,
           compat_version=DEFAULT_DIFF_COMPAT_VERSION):
    """
    Factory wrapper for returning a differ class based on the compat version
    and flags specified.
    """
    if compat_version == 0:
        return SMDiffer(a, b)
    elif compat_version == 1:
        return MyersDiffer(a, b, ignore_space)
    else:
        raise Exception("Invalid diff compat version (%s) passed to Differ" %
                        (compat_version))


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

    # XXX: catch exception if Popen fails?
    newfile = '%s-new' % oldfile
    p = subprocess.Popen(['patch', '-o', newfile, oldfile],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.stdin.write(diff)
    p.stdin.close()
    failure = p.wait()

    if failure:
        os.unlink(oldfile)
        os.unlink(newfile)

        try:
            os.unlink(newfile + ".rej")
        except:
            pass

        # FIXME: This doesn't provide any useful error report on why the patch
        # failed to apply, which makes it hard to debug.
        raise Exception(("The patch to '%s' didn't apply cleanly. " +
                         "`patch` returned: %s") %
                        (filename, p.stdout.read()))

    f = open(newfile, "r")
    data = f.read()
    f.close()

    os.unlink(oldfile)
    os.unlink(newfile)

    return data


def get_line_changed_regions(oldline, newline):
    if oldline is None or newline is None:
        return (None, None)

    # Use the SequenceMatcher directly. It seems to give us better results
    # for this. We should investigate steps to move to the new differ.
    differ = SequenceMatcher(None, oldline, newline)

    # This thresholds our results -- we don't want to show inter-line diffs if
    # most of the line has changed, unless those lines are very short.

    # FIXME: just a plain, linear threshold is pretty crummy here.  Short
    # changes in a short line get lost.  I haven't yet thought of a fancy
    # nonlinear test.
    if differ.ratio() < 0.6:
        return (None, None)

    oldchanges = []
    newchanges = []
    back = (0, 0)

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
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
