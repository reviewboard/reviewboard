import fnmatch
import logging
import os
import re
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

from django.utils.html import escape
from django.utils.http import urlquote
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from djblets.log import log_timed
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.misc import cache_memoize

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.smdiff import SMDiffer
from reviewboard.scmtools.core import PRE_CREATION, HEAD


DEFAULT_DIFF_COMPAT_VERSION = 1


class UserVisibleError(Exception):
    pass


class DiffCompatError(Exception):
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
        raise DiffCompatError(
            "Invalid diff compatibility version (%s) passed to Differ" %
                (compat_version))


def patch(diff, file, filename):
    """Apply a diff to a file.  Delegates out to `patch` because noone
       except Larry Wall knows how to patch."""

    log_timer = log_timed("Patching file %s" % filename)

    def convert_line_endings(data):
        # Files without a trailing newline come out of Perforce (and possibly
        # other systems) with a trailing \r. Diff will see the \r and
        # add a "\ No newline at end of file" marker at the end of the file's
        # contents, which patch understands and will happily apply this to
        # a file with a trailing \r.
        #
        # The problem is that we normalize \r's to \n's, which breaks patch.
        # Our solution to this is to just remove that last \r and not turn
        # it into a \n.
        #
        # See http://code.google.com/p/reviewboard/issues/detail?id=386
        # and http://reviews.review-board.org/r/286/
        if data == "":
            return ""

        if data[-1] == "\r":
            data = data[:-1]

        temp = data.replace('\r\n', '\n')
        temp = temp.replace('\r', '\n')
        return temp

    if diff.strip() == "":
        # Someone uploaded an unchanged file. Return the one we're patching.
        return file

    # Prepare the temporary directory if none is available
    tempdir = tempfile.mkdtemp(prefix='reviewboard.')

    (fd, oldfile) = tempfile.mkstemp(dir=tempdir)
    f = os.fdopen(fd, "w+b")
    f.write(convert_line_endings(file))
    f.close()

    diff = convert_line_endings(diff)

    # XXX: catch exception if Popen fails?
    newfile = '%s-new' % oldfile
    p = subprocess.Popen(['patch', '-o', newfile, oldfile],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    p.stdin.write(diff)
    p.stdin.close()
    patch_output = p.stdout.read()
    failure = p.wait()

    if failure:
        f = open("%s.diff" %
                 (os.path.join(tempdir, os.path.basename(filename))), "w")
        f.write(diff)
        f.close()

        log_timer.done()

        # FIXME: This doesn't provide any useful error report on why the patch
        # failed to apply, which makes it hard to debug.  We might also want to
        # have it clean up if DEBUG=False
        raise Exception(_("The patch to '%s' didn't apply cleanly. The temporary " +
                          "files have been left in '%s' for debugging purposes.\n" +
                          "`patch` returned: %s") %
                        (filename, tempdir, patch_output))

    f = open(newfile, "r")
    data = f.read()
    f.close()

    os.unlink(oldfile)
    os.unlink(newfile)
    os.rmdir(tempdir)

    log_timer.done()

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


def convert_to_utf8(s, enc):
    """
    Returns the passed string as a unicode string. If conversion to UTF-8
    fails, we try the user-specified encoding, which defaults to ISO 8859-15.
    This can be overridden by users inside the repository configuration, which
    gives users repository-level control over file encodings (file-level control
    is really, really hard).
    """
    if isinstance(s, unicode):
        return s
    elif isinstance(s, basestring):
        try:
            u = unicode(s, 'utf-8')
            return u
        except UnicodeError:
            for e in enc.split(','):
                try:
                    u = unicode(s, e)
                    break
                except UnicodeError:
                    pass
            return u.encode('utf-8')
    else:
        raise TypeError("Value to convert is unexpected type %s", type(s))


def get_original_file(filediff):
    """
    Get a file either from the cache or the SCM, applying the parent diff if
    it exists.

    SCM exceptions are passed back to the caller.
    """
    data = ""

    if filediff.source_revision != PRE_CREATION:
        def fetch_file(file, revision):
            log_timer = log_timed("Fetching file '%s' r%s from %s" %
                                  (file, revision, repository))
            data = tool.get_file(file, revision)
            log_timer.done()
            return data

        repository = filediff.diffset.repository
        tool = repository.get_scmtool()
        file = filediff.source_file
        revision = filediff.source_revision

        key = "%s:%s:%s" % (filediff.diffset.repository.path, urlquote(file),
                            revision)

        # We wrap the result of get_file in a list and then return the first
        # element after getting the result from the cache. This prevents the
        # cache backend from converting to unicode, since we're no longer
        # passing in a string and the cache backend doesn't recursively look
        # through the list in order to convert the elements inside.
        #
        # Basically, this fixes the massive regressions introduced by the
        # Django unicode changes.
        data = cache_memoize(key, lambda: [fetch_file(file, revision)])[0]

    # If there's a parent diff set, apply it to the buffer.
    if filediff.parent_diff:
        data = patch(filediff.parent_diff, data, filediff.source_file)

    return data


def get_patched_file(buffer, filediff):
    return patch(filediff.diff, buffer, filediff.dest_file)


def get_chunks(diffset, filediff, interfilediff, force_interdiff,
               enable_syntax_highlighting):
    def diff_line(vlinenum, oldlinenum, newlinenum, oldline, newline,
                  oldmarkup, newmarkup):
        if oldline and newline and oldline != newline:
            oldregion, newregion = get_line_changed_regions(oldline, newline)
        else:
            oldregion = newregion = []

        return [vlinenum,
                oldlinenum or '', mark_safe(oldmarkup or ''), oldregion,
                newlinenum or '', mark_safe(newmarkup or ''), newregion]

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


    # There are three ways this function is called:
    #
    #     1) filediff, no interfilediff
    #        - Returns chunks for a single filediff. This is the usual way
    #          people look at diffs in the diff viewer.
    #
    #          In this mode, we get the original file based on the filediff
    #          and then patch it to get the resulting file.
    #
    #          This is also used for interdiffs where the source revision
    #          has no equivalent modified file but the interdiff revision
    #          does. It's no different than a standard diff.
    #
    #     2) filediff, interfilediff
    #        - Returns chunks showing the changes between a source filediff
    #          and the interdiff.
    #
    #          This is the typical mode used when showing the changes
    #          between two diffs. It requires that the file is included in
    #          both revisions of a diffset.
    #
    #     3) filediff, no interfilediff, force_interdiff
    #        - Returns chunks showing the changes between a source
    #          diff and an unmodified version of the diff.
    #
    #          This is used when the source revision in the diffset contains
    #          modifications to a file which have then been reverted in the
    #          interdiff revision. We don't actually have an interfilediff
    #          in this case, so we have to indicate that we are indeed in
    #          interdiff mode so that we can special-case this and not
    #          grab a patched file for the interdiff version.

    assert filediff

    file = filediff.source_file
    revision = filediff.source_revision

    old = get_original_file(filediff)
    new = get_patched_file(old, filediff)

    if interfilediff:
        old = new
        interdiff_orig = get_original_file(interfilediff)
        new = get_patched_file(interdiff_orig, interfilediff)
    elif force_interdiff:
        # Basically, revert the change.
        temp = old
        old = new
        new = temp

    encoding = diffset.repository.encoding or 'iso-8859-15'
    old = convert_to_utf8(old, encoding)
    new = convert_to_utf8(new, encoding)

    # Normalize the input so that if there isn't a trailing newline, we add
    # it.
    if old and old[-1] != '\n':
        old += '\n'

    if new and new[-1] != '\n':
        new += '\n'

    a = re.split(r"\r?\n", old or '')
    b = re.split(r"\r?\n", new or '')

    # Remove the trailing newline, now that we've split this. This will
    # prevent a duplicate line number at the end of the diff.
    del(a[-1])
    del(b[-1])

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

    if not markup_a:
        markup_a = re.split(r"\r?\n", escape(old))

    if not markup_b:
        markup_b = re.split(r"\r?\n", escape(new))

    siteconfig = SiteConfiguration.objects.get_current()

    chunks = []
    linenum = 1

    ignore_space = True
    for pattern in siteconfig.get("diffviewer_include_space_patterns"):
        if fnmatch.fnmatch(file, pattern):
            ignore_space = False
            break

    differ = Differ(a, b, ignore_space=ignore_space,
                    compat_version=diffset.diffcompat)

    # TODO: Make this back into a preference if people really want it.
    context_num_lines = siteconfig.get("diffviewer_context_num_lines")
    collapse_threshold = 2 * context_num_lines + 3

    if interfilediff:
        logging.debug("Generating diff chunks for interdiff ids %s-%s",
                      filediff.id, interfilediff.id)
    else:
        logging.debug("Generating diff chunks for filediff id %s", filediff.id)

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        oldlines = markup_a[i1:i2]
        newlines = markup_b[j1:j2]
        numlines = max(len(oldlines), len(newlines))

        lines = map(diff_line,
                    xrange(linenum, linenum + numlines),
                    xrange(i1 + 1, i2 + 1), xrange(j1 + 1, j2 + 1),
                    a[i1:i2], b[j1:j2], oldlines, newlines)
        linenum += numlines

        if tag == 'equal' and numlines > collapse_threshold:
            last_range_start = numlines - context_num_lines

            if len(chunks) == 0:
                add_ranged_chunks(lines, 0, last_range_start, True)
                add_ranged_chunks(lines, last_range_start, numlines)
            else:
                add_ranged_chunks(lines, 0, context_num_lines)

                if i2 == a_num_lines and j2 == b_num_lines:
                    add_ranged_chunks(lines, context_num_lines, numlines, True)
                else:
                    add_ranged_chunks(lines, context_num_lines,
                                      last_range_start, True)
                    add_ranged_chunks(lines, last_range_start, numlines)
        else:
            chunks.append(new_chunk(lines, numlines, tag))

    if interfilediff:
        logging.debug("Done generating diff chunks for interdiff ids %s-%s",
                      filediff.id, interfilediff.id)
    else:
        logging.debug("Done generating diff chunks for filediff id %s",
                      filediff.id)

    return chunks


def add_navigation_cues(files):
    """Add index and changed_chunks to a list of files and their chunks"""
    # FIXME: this modifies in-place right now, which is kind of ugly
    for i, file in enumerate(files):
        file['index'] = i
        file['changed_chunks'] = []

        for j, chunk in enumerate(file['chunks']):
            chunk['index'] = j
            if chunk['change'] != 'equal':
                file['changed_chunks'].append(chunk)

        file['num_changes'] = len(file['changed_chunks'])


def get_revision_str(revision):
    if revision == HEAD:
        return "HEAD"
    elif revision == PRE_CREATION:
        return ""
    else:
        return "Revision %s" % revision


def generate_files(diffset, filediff, interdiffset, enable_syntax_highlighting):
    if filediff:
        filediffs = [filediff]

        if interdiffset:
            log_timer = log_timed("Generating diff file info for "
                                  "interdiffset ids %s-%s, filediff %s" %
                                  (diffset.id, interdiffset.id, filediff.id))
        else:
            log_timer = log_timed("Generating diff file info for "
                                  "diffset id %s, filediff %s" %
                                  (diffset.id, filediff.id))
    else:
        filediffs = diffset.files.all()

        if interdiffset:
            log_timer = log_timed("Generating diff file info for "
                                  "interdiffset ids %s-%s" %
                                  (diffset.id, interdiffset.id))
        else:
            log_timer = log_timed("Generating diff file info for "
                                  "diffset id %s" % diffset.id)


    # A map used to quickly look up the equivalent interfilediff given a
    # source file.
    interdiff_map = {}
    if interdiffset:
        for interfilediff in interdiffset.files.all():
            if not filediff or \
               filediff.source_file == interfilediff.source_file:
                interdiff_map[interfilediff.source_file] = interfilediff

    key_prefix = "diff-sidebyside-"

    if enable_syntax_highlighting:
        key_prefix += "hl-"


    # In order to support interdiffs properly, we need to display diffs
    # on every file in the union of both diffsets. Iterating over one diffset
    # or the other doesn't suffice.
    #
    # We build a list of parts containing the source filediff, the interdiff
    # filediff (if specified), and whether to force showing an interdiff
    # (in the case where a file existed in the source filediff but was
    # reverted in the interdiff).
    filediff_parts = []

    for filediff in filediffs:
        interfilediff = None

        if filediff.source_file in interdiff_map:
            interfilediff = interdiff_map[filediff.source_file]
            del(interdiff_map[filediff.source_file])

        filediff_parts.append((filediff, interfilediff, interdiffset != None))


    if interdiffset:
        # We've removed everything in the map that we've already found.
        # What's left are interdiff files that are new. They have no file
        # to diff against.
        #
        # The end result is going to be a view that's the same as when you're
        # viewing a standard diff. As such, we can pretend the interdiff is
        # the source filediff and not specify an interdiff. Keeps things
        # simple, code-wise, since we really have no need to special-case
        # this.
        for interdiff in interdiff_map.values():
            filediff_parts.append((interdiff, None, False))


    files = []
    for parts in filediff_parts:
        filediff, interfilediff, force_interdiff = parts

        if filediff.binary:
            chunks = []
        else:
            key = key_prefix

            if not force_interdiff:
                key += str(filediff.id)
            elif interfilediff:
                key += "interdiff-%s-%s" % (filediff.id, interfilediff.id)
            else:
                key += "interdiff-%s-none" % filediff.id

            chunks = cache_memoize(key,
                lambda: get_chunks(filediff.diffset,
                                   filediff, interfilediff,
                                   force_interdiff,
                                   enable_syntax_highlighting))

        if interdiffset:
            # In the case of interdiffs, don't show any unmodified files
            has_changes = False

            for chunk in chunks:
                if chunk['change'] != 'equal':
                    has_changes = True
                    break

            if not has_changes:
                continue

        filediff_revision_str = get_revision_str(filediff.source_revision)
        newfile = (filediff.source_revision == PRE_CREATION)

        if interdiffset:
            source_revision = "Diff Revision %s" % diffset.revision

            if not interfilediff and force_interdiff:
                dest_revision = "Diff Revision %s - File Reverted" % \
                                interdiffset.revision
            else:
                dest_revision = "Diff Revision %s" % interdiffset.revision
        else:
            source_revision = get_revision_str(filediff.source_revision)

            if newfile:
                dest_revision = _("New File")
            else:
                dest_revision = _("New Change")

        i = filediff.source_file.rfind('/')

        if i != -1:
            basepath = filediff.source_file[:i]
            basename = filediff.source_file[i + 1:]
        else:
            basepath = ""
            basename = filediff.source_file

        files.append({
            'depot_filename': filediff.source_file,
            'basename': basename,
            'basepath': basepath,
            'revision': source_revision,
            'dest_revision': dest_revision,
            'chunks': chunks,
            'filediff': filediff,
            'interfilediff': interfilediff,
            'force_interdiff': force_interdiff,
            'binary': filediff.binary,
            'newfile': newfile,
        })

    add_navigation_cues(files)

    def cmp_file(x, y):
        # Sort based on basepath in asc order
        if x["basepath"] != y["basepath"]:
            return cmp(x["basepath"], y["basepath"])
        # Sort based on filename in asc order, then basod on extension in desc
        # order, to make *.h be ahead of *.c/cpp
        x_file, x_ext = os.path.splitext(x["basename"])
        y_file, y_ext = os.path.splitext(y["basename"])
        if x_file != y_file:
            return cmp(x_file, y_file)
        else:
            return cmp(y_ext, x_ext)

    files.sort(cmp_file)

    log_timer.done()

    return files


def get_diff_files(diffset, filediff=None, interdiffset=None,
                   enable_syntax_highlighting=True):
    return generate_files(diffset, filediff, interdiffset,
                          enable_syntax_highlighting)
