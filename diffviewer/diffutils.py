import os
import subprocess
import tempfile
from difflib import SequenceMatcher

try:
    import pygments
    from pygments.lexers import get_lexer_for_filename
    # from pygments.lexers import guess_lexer_for_filename
    from pygments.formatters import HtmlFormatter
except ImportError:
    pass

from django.conf import settings
from django.utils.html import escape
from djblets.util.misc import cache_memoize

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.smdiff import SMDiffer
import reviewboard.scmtools as scmtools


DEFAULT_DIFF_COMPAT_VERSION = 1


class UserVisibleError(Exception):
    pass


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

    def convert_line_endings(data):
        temp = data.replace('\r\n', '\n')
        temp = temp.replace('\r', '\n')
        return temp

    if diff.strip() == "":
        # Someone uploaded an unchanged file. Return the one we're patching.
        return file

    # Prepare the temporary directory if none is available
    if not tempfile.tempdir:
        tempfile.tempdir = tempfile.mkdtemp(prefix='reviewboard.')

    (fd, oldfile) = tempfile.mkstemp()
    f = os.fdopen(fd, "w+b")
    f.write(convert_line_endings(file))
    f.close()

    # XXX: catch exception if Popen fails?
    newfile = '%s-new' % oldfile
    p = subprocess.Popen(['patch', '-o', newfile, oldfile],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.stdin.write(convert_line_endings(diff))
    p.stdin.close()
    failure = p.wait()

    if failure:
        # FIXME: This doesn't provide any useful error report on why the patch
        # failed to apply, which makes it hard to debug.
        raise Exception(("The patch to '%s' didn't apply cleanly. The temporary " +
                         "files have been left in '%s' for debugging purposes.\n" +
                         "`patch` returned: %s") %
                        (filename, tempfile.tempdir, p.stdout.read()))

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


def get_original_file(diffset, file, revision):
    """Get a file either from the cache or the SCM.  SCM exceptions are
       passed back to the caller."""
    tool = diffset.repository.get_scmtool()

    key = "%s:%s:%s" % (diffset.repository.path, file, revision)

    return cache_memoize(key, lambda: tool.get_file(file, revision))


def get_patched_file(buffer, filediff):
    return patch(filediff.diff, buffer, filediff.dest_file)


def get_chunks(diffset, filediff, interfilediff, enable_syntax_highlighting):
    def diff_line(linenum, oldline, newline, oldmarkup, newmarkup):
        if not oldline or not newline:
            return [linenum, oldmarkup or '', [], newmarkup or '', []]

        oldregion, newregion = get_line_changed_regions(oldline, newline)

        return [linenum, oldmarkup, oldregion, newmarkup, newregion]

    def new_chunk(lines, numlines, tag, collapsable=False):
        return {
            'lines': lines,
            'numlines': numlines,
            'change': tag,
            'collapsable': collapsable,
        }

    def add_ranged_chunks(lines, start, end, collapsable=False):
        numlines = end - start
        chunks.append(new_chunk(lines[start:end], end - start, 'equal',
                      collapsable))

    def apply_pygments(data, filename):
        # XXX Guessing is preferable but really slow, especially on XML
        #     files.
        #if filename.endswith(".xml"):
        lexer = get_lexer_for_filename(filename, stripnl=False)
        #else:
        #    lexer = guess_lexer_for_filename(filename, data, stripnl=False)

        try:
            # This is only available in 0.7 and higher
            lexer.add_filter('codetagify')
        except AttributeError:
            pass

        return pygments.highlight(data, lexer, HtmlFormatter()).splitlines()


    file = filediff.source_file
    revision = filediff.source_revision
    old = ""

    try:
        if revision != scmtools.PRE_CREATION:
            old = get_original_file(diffset, file, revision)

        new = get_patched_file(old, filediff)

        if interfilediff:
            old, new = new, get_patched_file(old, interfilediff)
    except Exception, e:
        raise UserVisibleError(str(e))

    a = (old or '').splitlines()
    b = (new or '').splitlines()
    a_num_lines = len(a)
    b_num_lines = len(b)

    markup_a = markup_b = None

    if enable_syntax_highlighting:
        try:
            # TODO: Try to figure out the right lexer for these files
            #       once instead of twice.
            markup_a = apply_pygments(old or '', filediff.source_file)
            markup_b = apply_pygments(new or '', filediff.dest_file)
        except ValueError:
            pass

    if not markup_a or not markup_b:
        markup_a = escape(old).splitlines()
        markup_b = escape(new).splitlines()

    chunks = []
    linenum = 1
    differ = Differ(a, b, ignore_space=True, compat_version=diffset.diffcompat)

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        oldlines = markup_a[i1:i2]
        newlines = markup_b[j1:j2]
        numlines = max(len(oldlines), len(newlines))
        lines = map(diff_line,
                    range(linenum, linenum + numlines),
                    a[i1:i2], b[j1:j2], oldlines, newlines)
        linenum += numlines

        if tag == 'equal' and \
           numlines > settings.DIFF_CONTEXT_COLLAPSE_THRESHOLD:
            last_range_start = numlines - settings.DIFF_CONTEXT_NUM_LINES

            if len(chunks) == 0:
                add_ranged_chunks(lines, 0, last_range_start, True)
                add_ranged_chunks(lines, last_range_start, numlines)
            else:
                add_ranged_chunks(lines, 0, settings.DIFF_CONTEXT_NUM_LINES)

                if i2 == a_num_lines and j2 == b_num_lines:
                    add_ranged_chunks(lines,
                                      settings.DIFF_CONTEXT_NUM_LINES,
                                      numlines, True)
                else:
                    add_ranged_chunks(lines,
                                      settings.DIFF_CONTEXT_NUM_LINES,
                                      last_range_start, True)
                    add_ranged_chunks(lines, last_range_start, numlines)
        else:
            chunks.append(new_chunk(lines, numlines, tag))

    return chunks


def add_navigation_cues(files):
    """Add index, nextid and previd data to a list of files/chunks"""
    # FIXME: this modifies in-place right now, which is kind of ugly
    interesting = []
    indices = []
    for i, file in enumerate(files):
        file['index'] = i
        k = 1
        for j, chunk in enumerate(file['chunks']):
            if chunk['change'] != 'equal':
                interesting.append(chunk)
                indices.append((i, k))
                k += 1

        file['num_changes'] = k - 1

    for chunk, previous, current, next in zip(interesting,
                                              [None] + indices[:-1],
                                              indices,
                                              indices[1:] + [None]):
        chunk['index'] = current[1]
        if previous:
            chunk['previd'] = '%d.%d' % previous
        if next:
            chunk['nextid'] = '%d.%d' % next


def generate_files(diffset, filediff, interdiffset, enable_syntax_highlighting):
    if filediff:
        filediffs = [filediff]
    else:
        filediffs = diffset.files.all()

    key_prefix = "diff-sidebyside-"

    if enable_syntax_highlighting:
        key_prefix += "hl-"

    files = []
    for filediff in filediffs:
        if filediff.binary:
            chunks = []
        else:
            interfilediff = None

            if interdiffset:
                # XXX This is slow. We should optimize this.
                for filediff2 in interdiffset.files.all():
                    if filediff2.source_file == filediff.source_file:
                        interfilediff = filediff2
                        break

            key = key_prefix

            if interfilediff:
                key += "interdiff-%s-%s" % (filediff.id, interfilediff.id)
            else:
                key += str(filediff.id)

            chunks = cache_memoize(key,
                lambda: get_chunks(diffset, filediff, interfilediff,
                                   enable_syntax_highlighting))

        revision = filediff.source_revision

        if revision == scmtools.HEAD:
            revision = "HEAD"
        elif revision == scmtools.PRE_CREATION:
            revision = "Pre-creation"
        else:
            revision = "Revision %s" % revision

        files.append({
            'depot_filename': filediff.source_file,
            'revision': revision,
            'chunks': chunks,
            'filediff': filediff,
            'binary': filediff.binary,
        })

    add_navigation_cues(files)

    return files


def get_diff_files(diffset, filediff=None, interdiffset=None,
                   enable_syntax_highlighting=True):
    return generate_files(diffset, filediff, interdiffset,
                          enable_syntax_highlighting)
