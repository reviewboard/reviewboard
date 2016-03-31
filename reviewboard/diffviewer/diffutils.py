from __future__ import unicode_literals

import os
import re
import subprocess
import tempfile
from difflib import SequenceMatcher

from django.core.exceptions import ObjectDoesNotExist
from django.utils import six
from django.utils.translation import ugettext as _
from djblets.log import log_timed
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.contextmanagers import controlled_subprocess

from reviewboard.scmtools.core import PRE_CREATION, HEAD


NEWLINE_CONVERSION_RE = re.compile(r'\r(\r?\n)?')
NEWLINE_RE = re.compile(r'(?:\n|\r(?:\r?\n)?)')

ALPHANUM_RE = re.compile(r'\w')
WHITESPACE_RE = re.compile(r'\s')


def convert_to_unicode(s, encoding_list):
    """Returns the passed string as a unicode object.

    If conversion to unicode fails, we try the user-specified encoding, which
    defaults to ISO 8859-15. This can be overridden by users inside the
    repository configuration, which gives users repository-level control over
    file encodings.

    Ideally, we'd like to have per-file encodings, but this is hard. The best
    we can do now is a comma-separated list of things to try.

    Returns the encoding type which was used and the decoded unicode object.
    """
    if isinstance(s, bytearray):
        # Some SCMTool backends return file data as a bytearray instead of
        # bytes.
        s = bytes(s)

    if isinstance(s, six.text_type):
        # Nothing to do
        return 'utf-8', s
    elif isinstance(s, six.string_types):
        try:
            # First try strict utf-8
            enc = 'utf-8'
            return enc, six.text_type(s, enc)
        except UnicodeError:
            # Now try any candidate encodings
            for e in encoding_list:
                try:
                    return e, six.text_type(s, e)
                except (UnicodeError, LookupError):
                    pass

            # Finally, try to convert to unicode and replace all unknown
            # characters.
            try:
                enc = 'utf-8'
                return enc, six.text_type(s, enc, errors='replace')
            except UnicodeError:
                raise Exception(
                    _("Diff content couldn't be converted to unicode using "
                      "the following encodings: %s")
                    % (['utf-8'] + encoding_list))
    else:
        raise TypeError('Value to convert is unexpected type %s', type(s))


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
    # and http://reviews.reviewboard.org/r/286/
    if data == b"":
        return b""

    if data[-1] == b"\r":
        data = data[:-1]

    return NEWLINE_CONVERSION_RE.sub(b'\n', data)


def split_line_endings(data):
    """Splits a string into lines while preserving all non-CRLF characters.

    Unlike the string's splitlines(), this will only split on the following
    character sequences: \\n, \\r, \\r\\n, and \\r\\r\\n.

    This is needed to prevent the sort of issues encountered with
    Unicode strings when calling splitlines(), which is that form feed
    characters would be split. patch and diff accept form feed characters
    as valid characters in diffs, and doesn't treat them as newlines, but
    splitlines() will treat it as a newline anyway.
    """
    lines = NEWLINE_RE.split(data)

    # splitlines() would chop off the last entry, if the string ends with
    # a newline. split() doesn't do this. We need to retain that same
    # behavior by chopping it off ourselves.
    if not lines[-1]:
        lines = lines[:-1]

    return lines


def patch(diff, file, filename, request=None):
    """Apply a diff to a file.  Delegates out to `patch` because noone
       except Larry Wall knows how to patch."""

    log_timer = log_timed("Patching file %s" % filename,
                          request=request)

    if not diff.strip():
        # Someone uploaded an unchanged file. Return the one we're patching.
        return file

    # Prepare the temporary directory if none is available
    tempdir = tempfile.mkdtemp(prefix='reviewboard.')

    (fd, oldfile) = tempfile.mkstemp(dir=tempdir)
    f = os.fdopen(fd, "w+b")
    f.write(convert_line_endings(file))
    f.close()

    diff = convert_line_endings(diff)

    newfile = '%s-new' % oldfile

    process = subprocess.Popen(['patch', '-o', newfile, oldfile],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, cwd=tempdir)

    with controlled_subprocess("patch", process) as p:
        stdout, stderr = p.communicate(diff)
        failure = p.returncode

    if failure:
        absolute_path = os.path.join(tempdir, os.path.basename(filename))
        with open("%s.diff" % absolute_path, 'w') as f:
            f.write(diff)

        log_timer.done()

        # FIXME: This doesn't provide any useful error report on why the patch
        # failed to apply, which makes it hard to debug.  We might also want to
        # have it clean up if DEBUG=False
        raise Exception(
            _("The patch to '%(filename)s' didn't apply cleanly. The "
              "temporary files have been left in '%(tempdir)s' for debugging "
              "purposes.\n"
              "`patch` returned: %(output)s")
            % {
                'filename': filename,
                'tempdir': tempdir,
                'output': stderr,
            })

    with open(newfile, "r") as f:
        data = f.read()

    os.unlink(oldfile)
    os.unlink(newfile)
    os.rmdir(tempdir)

    log_timer.done()

    return data


def get_original_file(filediff, request, encoding_list):
    """
    Get a file either from the cache or the SCM, applying the parent diff if
    it exists.

    SCM exceptions are passed back to the caller.
    """
    data = b""

    if filediff.source_revision != PRE_CREATION:
        repository = filediff.diffset.repository
        data = repository.get_file(
            filediff.source_file,
            filediff.source_revision,
            base_commit_id=filediff.diffset.base_commit_id,
            request=request)

        # Convert to unicode before we do anything to manipulate the string.
        encoding, data = convert_to_unicode(data, encoding_list)

        # Repository.get_file doesn't know or care about how we need line
        # endings to work. So, we'll just transform every time.
        #
        # This is mostly only a problem if the diff chunks aren't in the
        # cache, though if several people are working off the same file,
        # we'll be doing extra work to convert those line endings for each
        # of those instead of once.
        #
        # Only other option is to cache the resulting file, but then we're
        # duplicating the cached contents.
        data = convert_line_endings(data)

        # Convert back to bytes using whichever encoding we used to decode.
        data = data.encode(encoding)

    # If there's a parent diff set, apply it to the buffer.
    if (filediff.parent_diff and
        (not filediff.extra_data or
         not filediff.extra_data.get('parent_moved', False))):
        data = patch(filediff.parent_diff, data, filediff.source_file,
                     request)

    return data


def get_patched_file(buffer, filediff, request):
    tool = filediff.diffset.repository.get_scmtool()
    diff = tool.normalize_patch(filediff.diff, filediff.source_file,
                                filediff.source_revision)
    return patch(diff, buffer, filediff.dest_file, request)


def get_revision_str(revision):
    if revision == HEAD:
        return "HEAD"
    elif revision == PRE_CREATION:
        return ""
    else:
        return _("Revision %s") % revision


def get_diff_files(diffset, filediff=None, interdiffset=None, request=None):
    """Generates a list of files that will be displayed in a diff.

    This will go through the given diffset/interdiffset, or a given filediff
    within that diffset, and generate the list of files that will be
    displayed. This file list will contain a bunch of metadata on the files,
    such as the index, original/modified names, revisions, associated
    filediffs/diffsets, and so on.

    This can be used along with populate_diff_chunks to build a full list
    containing all diff chunks used for rendering a side-by-side diff.
    """
    if filediff:
        filediffs = [filediff]

        if interdiffset:
            log_timer = log_timed("Generating diff file info for "
                                  "interdiffset ids %s-%s, filediff %s" %
                                  (diffset.id, interdiffset.id, filediff.id),
                                  request=request)
        else:
            log_timer = log_timed("Generating diff file info for "
                                  "diffset id %s, filediff %s" %
                                  (diffset.id, filediff.id),
                                  request=request)
    else:
        filediffs = diffset.files.select_related().all()

        if interdiffset:
            log_timer = log_timed("Generating diff file info for "
                                  "interdiffset ids %s-%s" %
                                  (diffset.id, interdiffset.id),
                                  request=request)
        else:
            log_timer = log_timed("Generating diff file info for "
                                  "diffset id %s" % diffset.id,
                                  request=request)

    # A map used to quickly look up the equivalent interfilediff given a
    # source file.
    interdiff_map = {}

    # Filediffs that were created with leading slashes stripped won't match
    # those created with them present, so we need to compare them without in
    # order for the filenames to match up properly.
    tool = diffset.repository.get_scmtool()
    parser = tool.get_parser('')

    def _normfile(filename):
        return parser.normalize_diff_filename(filename)

    if interdiffset:
        for interfilediff in interdiffset.files.all():
            interfilediff_source_file = _normfile(interfilediff.source_file)

            if (not filediff or
                _normfile(filediff.source_file) == interfilediff_source_file):
                interdiff_map[interfilediff_source_file] = interfilediff

    # In order to support interdiffs properly, we need to display diffs
    # on every file in the union of both diffsets. Iterating over one diffset
    # or the other doesn't suffice.
    #
    # We build a list of parts containing the source filediff, the interdiff
    # filediff (if specified), and whether to force showing an interdiff
    # (in the case where a file existed in the source filediff but was
    # reverted in the interdiff).
    has_interdiffset = interdiffset is not None

    filediff_parts = [
        (temp_filediff,
         interdiff_map.pop(_normfile(temp_filediff.source_file), None),
         has_interdiffset)
        for temp_filediff in filediffs
    ]

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
        filediff_parts += [
            (interdiff, None, False)
            for interdiff in six.itervalues(interdiff_map)
        ]

    files = []

    for parts in filediff_parts:
        filediff, interfilediff, force_interdiff = parts

        newfile = (filediff.source_revision == PRE_CREATION)

        if interdiffset:
            # First, find out if we want to even process this one.
            # If the diffs are identical, or the patched files are identical,
            # or if the files were deleted in both cases, then we can be
            # absolutely sure that there's nothing interesting to show to
            # the user.
            if (filediff and interfilediff and
                (filediff.diff == interfilediff.diff or
                 (filediff.deleted and interfilediff.deleted) or
                 (filediff.patched_sha1 is not None and
                  filediff.patched_sha1 == interfilediff.patched_sha1))):
                continue

            source_revision = _("Diff Revision %s") % diffset.revision

            if not interfilediff and force_interdiff:
                dest_revision = (_("Diff Revision %s - File Reverted") %
                                 interdiffset.revision)
            else:
                dest_revision = _("Diff Revision %s") % interdiffset.revision
        else:
            source_revision = get_revision_str(filediff.source_revision)

            if newfile:
                dest_revision = _("New File")
            else:
                dest_revision = _("New Change")

        if interfilediff:
            raw_depot_filename = filediff.dest_file
            raw_dest_filename = interfilediff.dest_file
        else:
            raw_depot_filename = filediff.source_file
            raw_dest_filename = filediff.dest_file

        depot_filename = tool.normalize_path_for_display(raw_depot_filename)
        dest_filename = tool.normalize_path_for_display(raw_dest_filename)

        f = {
            'depot_filename': depot_filename,
            'dest_filename': dest_filename or depot_filename,
            'revision': source_revision,
            'dest_revision': dest_revision,
            'filediff': filediff,
            'interfilediff': interfilediff,
            'force_interdiff': force_interdiff,
            'binary': filediff.binary,
            'deleted': filediff.deleted,
            'moved': filediff.moved,
            'copied': filediff.copied,
            'moved_or_copied': filediff.moved or filediff.copied,
            'newfile': newfile,
            'index': len(files),
            'chunks_loaded': False,
            'is_new_file': (newfile and not interfilediff and
                            not filediff.parent_diff),
        }

        if force_interdiff:
            f['force_interdiff_revision'] = interdiffset.revision

        files.append(f)

    log_timer.done()

    if len(files) == 1:
        return files
    else:
        return get_sorted_filediffs(files, key=lambda f: f['filediff'])


def populate_diff_chunks(files, enable_syntax_highlighting=True,
                         request=None):
    """Populates a list of diff files with chunk data.

    This accepts a list of files (generated by get_diff_files) and generates
    diff chunk data for each file in the list. The chunk data is stored in
    the file state.
    """
    from reviewboard.diffviewer.chunk_generator import get_diff_chunk_generator

    for diff_file in files:
        generator = get_diff_chunk_generator(request,
                                             diff_file['filediff'],
                                             diff_file['interfilediff'],
                                             diff_file['force_interdiff'],
                                             enable_syntax_highlighting)
        chunks = generator.get_chunks()

        diff_file.update({
            'chunks': chunks,
            'num_chunks': len(chunks),
            'changed_chunk_indexes': [],
            'whitespace_only': len(chunks) > 0,
        })

        for j, chunk in enumerate(chunks):
            chunk['index'] = j

            if chunk['change'] != 'equal':
                diff_file['changed_chunk_indexes'].append(j)
                meta = chunk.get('meta', {})

                if not meta.get('whitespace_chunk', False):
                    diff_file['whitespace_only'] = False

        diff_file.update({
            'num_changes': len(diff_file['changed_chunk_indexes']),
            'chunks_loaded': True,
        })


def get_file_chunks_in_range(context, filediff, interfilediff,
                             first_line, num_lines):
    """
    A generator that yields chunks within a range of lines in the specified
    filediff/interfilediff.

    This is primarily intended for use with templates. It takes a
    RequestContext for looking up the user and for caching file lists,
    in order to improve performance and reduce lookup times for files that have
    already been fetched.

    Each returned chunk is a dictionary with the following fields:

      ============= ========================================================
      Variable      Description
      ============= ========================================================
      ``change``    The change type ("equal", "replace", "insert", "delete")
      ``numlines``  The number of lines in the chunk.
      ``lines``     The list of lines in the chunk.
      ``meta``      A dictionary containing metadata on the chunk
      ============= ========================================================


    Each line in the list of lines is an array with the following data:

      ======== =============================================================
      Index    Description
      ======== =============================================================
      0        Virtual line number (union of the original and patched files)
      1        Real line number in the original file
      2        HTML markup of the original file
      3        Changed regions of the original line (for "replace" chunks)
      4        Real line number in the patched file
      5        HTML markup of the patched file
      6        Changed regions of the patched line (for "replace" chunks)
      7        True if line consists of only whitespace changes
      ======== =============================================================
    """
    def find_header(headers):
        for header in reversed(headers):
            if header[0] < first_line:
                return {
                    'line': header[0],
                    'text': header[1],
                }

    interdiffset = None

    key = "_diff_files_%s_%s" % (filediff.diffset.id, filediff.id)

    if interfilediff:
        key += "_%s" % (interfilediff.id)
        interdiffset = interfilediff.diffset

    if key in context:
        files = context[key]
    else:
        assert 'user' in context

        request = context.get('request', None)
        files = get_diff_files(filediff.diffset, filediff, interdiffset,
                               request=request)
        populate_diff_chunks(files, get_enable_highlighting(context['user']),
                             request=request)
        context[key] = files

    if not files:
        raise StopIteration

    assert len(files) == 1
    last_header = [None, None]

    for chunk in files[0]['chunks']:
        if ('headers' in chunk['meta'] and
                (chunk['meta']['headers'][0] or chunk['meta']['headers'][1])):
            last_header = chunk['meta']['headers']

        lines = chunk['lines']

        if lines[-1][0] >= first_line >= lines[0][0]:
            start_index = first_line - lines[0][0]

            if first_line + num_lines <= lines[-1][0]:
                last_index = start_index + num_lines
            else:
                last_index = len(lines)

            new_chunk = {
                'lines': chunk['lines'][start_index:last_index],
                'numlines': last_index - start_index,
                'change': chunk['change'],
                'meta': chunk.get('meta', {}),
            }

            if 'left_headers' in chunk['meta']:
                left_header = find_header(chunk['meta']['left_headers'])
                right_header = find_header(chunk['meta']['right_headers'])
                del new_chunk['meta']['left_headers']
                del new_chunk['meta']['right_headers']

                if left_header or right_header:
                    header = (left_header, right_header)
                else:
                    header = last_header

                new_chunk['meta']['headers'] = header

            yield new_chunk

            first_line += new_chunk['numlines']
            num_lines -= new_chunk['numlines']

            assert num_lines >= 0
            if num_lines == 0:
                break


def get_enable_highlighting(user):
    user_syntax_highlighting = True

    if user.is_authenticated():
        try:
            profile = user.get_profile()
            user_syntax_highlighting = profile.syntax_highlighting
        except ObjectDoesNotExist:
            pass

    siteconfig = SiteConfiguration.objects.get_current()
    return (siteconfig.get('diffviewer_syntax_highlighting') and
            user_syntax_highlighting)


def get_line_changed_regions(oldline, newline):
    """Returns regions of changes between two similar lines."""
    if oldline is None or newline is None:
        return None, None

    # Use the SequenceMatcher directly. It seems to give us better results
    # for this. We should investigate steps to move to the new differ.
    differ = SequenceMatcher(None, oldline, newline)

    # This thresholds our results -- we don't want to show inter-line diffs
    # if most of the line has changed, unless those lines are very short.

    # FIXME: just a plain, linear threshold is pretty crummy here.  Short
    # changes in a short line get lost.  I haven't yet thought of a fancy
    # nonlinear test.
    if differ.ratio() < 0.6:
        return None, None

    oldchanges = []
    newchanges = []
    back = (0, 0)

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == 'equal':
            if (i2 - i1 < 3) or (j2 - j1 < 3):
                back = (j2 - j1, i2 - i1)

            continue

        oldstart, oldend = i1 - back[0], i2
        newstart, newend = j1 - back[1], j2

        if oldchanges and oldstart <= oldchanges[-1][1] < oldend:
            oldchanges[-1] = (oldchanges[-1][0], oldend)
        elif not oldline[oldstart:oldend].isspace():
            oldchanges.append((oldstart, oldend))

        if newchanges and newstart <= newchanges[-1][1] < newend:
            newchanges[-1] = (newchanges[-1][0], newend)
        elif not newline[newstart:newend].isspace():
            newchanges.append((newstart, newend))

        back = (0, 0)

    return oldchanges, newchanges


def get_sorted_filediffs(filediffs, key=None):
    """Sorts a list of filediffs.

    The list of filediffs will be sorted first by their base paths in
    ascending order.

    Within a base path, they'll be sorted by base name (minus the extension)
    in ascending order.

    If two files have the same base path and base name, we'll sort by the
    extension in descending order. This will make *.h sort ahead of *.c/cpp,
    for example.

    If the list being passed in is actually not a list of FileDiffs, it
    must provide a callable ``key`` parameter that will return a FileDiff
    for the given entry in the list. This will only be called once per
    item.
    """
    def cmp_filediffs(x, y):
        # Sort based on basepath in ascending order.
        if x[0] != y[0]:
            return cmp(x[0], y[0])

        # Sort based on filename in ascending order, then based on
        # the extension in descending order, to make *.h sort ahead of
        # *.c/cpp.
        x_file, x_ext = os.path.splitext(x[1])
        y_file, y_ext = os.path.splitext(y[1])

        if x_file == y_file:
            return cmp(y_ext, x_ext)
        else:
            return cmp(x_file, y_file)

    def make_key(filediff):
        if key:
            filediff = key(filediff)

        filename = filediff.source_file
        i = filename.rfind('/')

        if i == -1:
            return '', filename
        else:
            return filename[:i], filename[i + 1:]

    return sorted(filediffs, cmp=cmp_filediffs, key=make_key)
