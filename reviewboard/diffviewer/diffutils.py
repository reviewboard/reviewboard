from __future__ import unicode_literals

import logging
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

    if not filediff.is_new:
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


def get_matched_interdiff_files(tool, filediffs, interfilediffs):
    """Generate pairs of matched files for display in interdiffs.

    This compares a list of filediffs and a list of interfilediffs, attempting
    to best match up the files in both for display in the diff viewer.

    This will prioritize matches that share a common source filename,
    destination filename, and new/deleted state. Failing that, matches that
    share a common source filename are paired off.

    Any entries in ``interfilediffs` that don't have any match in ``filediffs``
    are considered new changes in the interdiff, and any entries in
    ``filediffs`` that don't have entries in ``interfilediffs`` are considered
    reverted changes.

    Args:
        tool (reviewboard.scmtools.core.SCMTool)
            The tool used for all these diffs.

        filediffs (list of reviewboard.diffviewer.models.FileDiff):
            The list of filediffs on the left-hand side of the diff range.

        interfilediffs (list of reviewboard.diffviewer.models.FileDiff):
            The list of filediffs on the right-hand side of the diff range.

    Yields:
        tuple:
        A paired off filediff match. This is a tuple containing two entries,
        each a :py:class:`~reviewboard.diffviewer.models.FileDiff` or ``None``.
    """
    parser = tool.get_parser('')
    _normfile = parser.normalize_diff_filename

    def _make_detail_key(filediff):
        return (_normfile(filediff.source_file),
                _normfile(filediff.dest_file),
                filediff.is_new,
                filediff.deleted)

    # In order to support interdiffs properly, we need to display diffs on
    # every file in the union of both diffsets. Iterating over one diffset
    # or the other doesn't suffice. We also need to be careful to handle
    # things like renamed/moved files, particularly when there are multiple
    # of them with the same source filename.
    #
    # This is done in four stages:
    #
    # 1. Build up maps and a set for keeping track of possible
    #    interfilediff candidates for future stages.
    #
    # 2. Look for any files that are common between the two diff revisions
    #    that have the same source filename, same destination filename, and
    #    the same new/deleted states.
    #
    #    Unless a diff is hand-crafted, there should never be more than one
    #    match here.
    #
    # 3. Look for any files that are common between the two diff revisions
    #    that have the same source filename and new/deleted state. These will
    #    ignore the destination filename, helping to match cases where diff 1
    #    modifies a file and diff 2 modifies + renames/moves it.
    #
    # 4. Add any remaining files from diff 2 that weren't found in diff 1.
    #
    # We don't have to worry about things like the order of matched diffs.
    # That will be taken care of at the end of the function.
    detail_interdiff_map = {}
    simple_interdiff_map = {}
    remaining_interfilediffs = set()

    # Stage 1: Build up the maps/set of interfilediffs.
    for interfilediff in interfilediffs:
        source_file = _normfile(interfilediff.source_file)
        detail_key = _make_detail_key(interfilediff)

        # We'll store this interfilediff in three spots: The set of
        # all interfilediffs, the detail map (for source + dest +
        # is_new file comparisons), and the simple map (for direct
        # source_file comparisons). These will be used for the
        # different matching stages.
        remaining_interfilediffs.add(interfilediff)
        detail_interdiff_map[detail_key] = interfilediff
        simple_interdiff_map.setdefault(source_file, set()).add(interfilediff)

    # Stage 2: Look for common files with the same source/destination
    #          filenames and new/deleted states.
    #
    # There will only be one match per filediff, at most. Any filediff or
    # interfilediff that we find will be excluded from future stages.
    remaining_filediffs = []

    for filediff in filediffs:
        source_file = _normfile(filediff.source_file)

        try:
            interfilediff = detail_interdiff_map.pop(
                _make_detail_key(filediff))
        except KeyError:
            remaining_filediffs.append(filediff)
            continue

        yield filediff, interfilediff

        if interfilediff:
            remaining_interfilediffs.discard(interfilediff)

            try:
                simple_interdiff_map.get(source_file, []).remove(interfilediff)
            except ValueError:
                pass

    # Stage 3: Look for common files with the same source/destination
    #          filenames (when they differ).
    #
    # Any filediff from diff 1 not already processed in stage 2 will be
    # processed here. We'll look for any filediffs from diff 2 that were
    # moved/copied from the same source to the same destination. This is one
    # half of the detailed file state we checked in stage 2.
    new_remaining_filediffs = []

    for filediff in remaining_filediffs:
        source_file = _normfile(filediff.source_file)
        found_interfilediffs = [
            temp_interfilediff
            for temp_interfilediff in simple_interdiff_map.get(source_file, [])
            if (temp_interfilediff.dest_file == filediff.dest_file and
                filediff.source_file != filediff.dest_file)
        ]

        if found_interfilediffs:
            remaining_interfilediffs.difference_update(found_interfilediffs)

            for interfilediff in found_interfilediffs:
                simple_interdiff_map[source_file].remove(interfilediff)
                yield filediff, interfilediff
        else:
            new_remaining_filediffs.append(filediff)

    remaining_filediffs = new_remaining_filediffs

    # Stage 4: Look for common files with the same source filenames and
    #          new/deleted states.
    #
    # Any filediff from diff 1 not already processed in stage 3 will be
    # processed here. We'll look for any filediffs from diff 2 that match
    # the source filename and the new/deleted state. Any that we find will
    # be matched up.
    new_remaining_filediffs = []

    for filediff in remaining_filediffs:
        source_file = _normfile(filediff.source_file)
        found_interfilediffs = [
            temp_interfilediff
            for temp_interfilediff in simple_interdiff_map.get(source_file, [])
            if (temp_interfilediff.is_new == filediff.is_new and
                temp_interfilediff.deleted == filediff.deleted)
        ]

        if found_interfilediffs:
            remaining_interfilediffs.difference_update(found_interfilediffs)

            for interfilediff in found_interfilediffs:
                simple_interdiff_map[source_file].remove(interfilediff)
                yield filediff, interfilediff
        else:
            new_remaining_filediffs.append(filediff)

    remaining_filediffs = new_remaining_filediffs

    # Stage 5: Look for common files with the same source filenames and
    #          compatible new/deleted states.
    #
    # This will help catch files that were marked as new in diff 1 but not in
    # diff 2, or deleted in diff 2 but not in diff 1. (The inverse for either
    # is NOT matched!). This is important because if a file is introduced in a
    # parent diff, the file can end up showing up as new itself (which is a
    # separate bug).
    #
    # Even if that bug did not exist, it's still possible for a file to be new
    # in one revision but committed separately (by that user or another), so we
    # need these matched.
    #
    # Any files not found with a matching interdiff will simply be yielded.
    # This is the last stage dealing with the filediffs in the first revision.
    for filediff in remaining_filediffs:
        source_file = _normfile(filediff.source_file)
        found_interfilediffs = [
            temp_interfilediff
            for temp_interfilediff in simple_interdiff_map.get(source_file, [])
            if (((filediff.is_new or not temp_interfilediff.is_new) or
                 (not filediff.is_new and temp_interfilediff.is_new and
                  filediff.dest_detail == temp_interfilediff.dest_detail)) and
                (not filediff.deleted or temp_interfilediff.deleted))
        ]

        if found_interfilediffs:
            remaining_interfilediffs.difference_update(found_interfilediffs)

            for interfilediff in found_interfilediffs:
                # NOTE: If more stages are ever added that deal with
                #       simple_interdiff_map, then we'll need to remove
                #       interfilediff from that map here.
                yield filediff, interfilediff
        else:
            yield filediff, None

    # Stage 6: Add any remaining files from the interdiff.
    #
    # We've removed everything that we've already found.  What's left are
    # interdiff files that are new. They have no file to diff against.
    #
    # The end result is going to be a view that's the same as when you're
    # viewing a standard diff. As such, we can pretend the interdiff is
    # the source filediff and not specify an interdiff. Keeps things
    # simple, code-wise, since we really have no need to special-case
    # this.
    for interfilediff in remaining_interfilediffs:
        yield None, interfilediff


def get_diff_files(diffset, filediff=None, interdiffset=None,
                   interfilediff=None, request=None):
    """Return a list of files that will be displayed in a diff.

    This will go through the given diffset/interdiffset, or a given filediff
    within that diffset, and generate the list of files that will be
    displayed. This file list will contain a bunch of metadata on the files,
    such as the index, original/modified names, revisions, associated
    filediffs/diffsets, and so on.

    This can be used along with :py:func:`populate_diff_chunks` to build a full
    list containing all diff chunks used for rendering a side-by-side diff.

    Args:
        diffset (reviewboard.diffviewer.models.DiffSet):
            The diffset containing the files to return.

        filediff (reviewboard.diffviewer.models.FileDiff, optional):
            A specific file in the diff to return information for.

        interdiffset (reviewboard.diffviewer.models.DiffSet, optional):
            A second diffset used for an interdiff range.

        interfilediff (reviewboard.diffviewer.models.FileDiff, optional):
            A second specific file in ``interdiffset`` used to return
            information for. This should be provided if ``filediff`` and
            ``interdiffset`` are both provided. If it's ``None`` in this
            case, then the diff will be shown as reverted for this file.

    Returns:
        list of dict:
        A list of dictionaries containing information on the files to show
        in the diff, in the order in which they would be shown.
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
        filediffs = list(diffset.files.select_related().all())

        if interdiffset:
            log_timer = log_timed("Generating diff file info for "
                                  "interdiffset ids %s-%s" %
                                  (diffset.id, interdiffset.id),
                                  request=request)
        else:
            log_timer = log_timed("Generating diff file info for "
                                  "diffset id %s" % diffset.id,
                                  request=request)

    # Filediffs that were created with leading slashes stripped won't match
    # those created with them present, so we need to compare them without in
    # order for the filenames to match up properly.
    tool = diffset.repository.get_scmtool()

    if interdiffset:
        if not filediff:
            interfilediffs = list(interdiffset.files.all())
        elif interfilediff:
            interfilediffs = [interfilediff]
        else:
            interfilediffs = []

        filediff_parts = []
        matched_filediffs = get_matched_interdiff_files(
            tool=tool,
            filediffs=filediffs,
            interfilediffs=interfilediffs)

        for temp_filediff, temp_interfilediff in matched_filediffs:
            if temp_filediff:
                filediff_parts.append((temp_filediff, temp_interfilediff,
                                       True))
            elif temp_interfilediff:
                filediff_parts.append((temp_interfilediff, None, False))
            else:
                logging.error(
                    'get_matched_interdiff_files returned an entry with an '
                    'empty filediff and interfilediff for diffset=%r, '
                    'interdiffset=%r, filediffs=%r, interfilediffs=%r',
                    diffset, interdiffset, filediffs, interfilediffs)

                raise ValueError(
                    'Internal error: get_matched_interdiff_files returned an '
                    'entry with an empty filediff and interfilediff! Please '
                    'report this along with information from the server '
                    'error log.')
    else:
        # We're not working with interdiffs. We can easily create the
        # filediff_parts directly.
        filediff_parts = [
            (temp_filediff, None, False)
            for temp_filediff in filediffs
        ]

    # Now that we have all the bits and pieces we care about for the filediffs,
    # we can start building information about each entry on the diff viewer.
    files = []

    for parts in filediff_parts:
        filediff, interfilediff, force_interdiff = parts

        newfile = filediff.is_new

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

        else:
            source_revision = get_revision_str(filediff.source_revision)

        if interfilediff:
            dest_revision = _('Diff Revision %s') % interdiffset.revision
        else:
            if force_interdiff:
                dest_revision = (_('Diff Revision %s - File Reverted') %
                                 interdiffset.revision)
            elif newfile:
                dest_revision = _('New File')
            else:
                dest_revision = _('New Change')

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
        return get_sorted_filediffs(
            files,
            key=lambda f: f['interfilediff'] or f['filediff'])


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
        chunks = list(generator.get_chunks())

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


def get_file_from_filediff(context, filediff, interfilediff):
    """Return the files that corresponds to the filediff/interfilediff.

    This is primarily intended for use with templates. It takes a
    RequestContext for looking up the user and for caching file lists,
    in order to improve performance and reduce lookup times for files that have
    already been fetched.

    This function returns either exactly one file or ``None``.
    """
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
                               interfilediff=interfilediff,
                               request=request)
        populate_diff_chunks(files, get_enable_highlighting(context['user']),
                             request=request)
        context[key] = files

    if not files:
        return None

    assert len(files) == 1
    return files[0]


def get_last_line_number_in_diff(context, filediff, interfilediff):
    """Determine the last virtual line number in the filediff/interfilediff.

    This returns the virtual line number to be used in expandable diff
    fragments.
    """
    f = get_file_from_filediff(context, filediff, interfilediff)

    last_chunk = f['chunks'][-1]
    last_line = last_chunk['lines'][-1]

    return last_line[0]


def _get_last_header_in_chunks_before_line(chunks, target_line):
    """Find the last header in the list of chunks before the target line."""
    def find_last_line_numbers(lines):
        """Return a tuple of the last line numbers in the given list of lines.

        The last line numbers are not always contained in the last element of
        the ``lines`` list. This is the case when dealing with interdiffs that
        have filtered out opcodes.

        See :py:func:`get_chunks_in_range` for a description of what is
        contained in each element of ``lines``.
        """
        last_left = None
        last_right = None

        for line in reversed(lines):
            if not last_right and line[4]:
                last_right = line[4]

            if not last_left and line[1]:
                last_left = line[1]

            if last_left and last_right:
                break

        return last_left, last_right

    def find_header(headers, offset, last_line):
        """Return the last header that occurs before a line.

        The offset parameter is the difference between the virtual number and
        and actual line number in the chunk. This is required because the
        header line numbers are original or patched line numbers, not virtual
        line numbers.
        """
        # In the case of interdiffs, it is possible that there will be headers
        # in the chunk that don't belong to it, but were put there due to
        # chunks being merged together. We must therefore ensure that the
        # header we're looking at is actually in the chunk.
        end_line = min(last_line, target_line)

        for header in reversed(headers):
            virtual_line = header[0] + offset

            if virtual_line < end_line:
                return {
                    'line': virtual_line,
                    'text': header[1]
                }

    # The most up-to-date header information
    header = {
        'left': None,
        'right': None
    }

    for chunk in chunks:
        lines = chunk['lines']
        virtual_first_line = lines[0][0]

        if virtual_first_line <= target_line:
            if virtual_first_line == target_line:
                # The given line number is the first line of a new chunk so
                # there can't be any relevant header information here.
                break

            last_left, last_right = find_last_line_numbers(lines)

            if 'left_headers' in chunk['meta'] and lines[0][1]:
                offset = virtual_first_line - lines[0][1]

                left_header = find_header(chunk['meta']['left_headers'],
                                          offset, last_left + offset)

                header['left'] = left_header or header['left']

            if 'right_headers' in chunk['meta'] and lines[0][4]:
                offset = virtual_first_line - lines[0][4]

                right_header = find_header(chunk['meta']['right_headers'],
                                           offset, last_right + offset)

                header['right'] = right_header or header['right']
        else:
            # We've gone past the given line number.
            break

    return header


def get_last_header_before_line(context, filediff, interfilediff, target_line):
    """Get the last header that occurs before the given line.

    This returns a dictionary of ``left`` header and ``right`` header. Each
    header is either ``None`` or a dictionary with the following fields:

    ======== ==============================================================
    Field    Description
    ======== ==============================================================
    ``line`` Virtual line number (union of the original and patched files)
    ``text`` The header text
    ======== ==============================================================
    """
    f = get_file_from_filediff(context, filediff, interfilediff)

    return _get_last_header_in_chunks_before_line(f['chunks'], target_line)


def get_file_chunks_in_range(context, filediff, interfilediff,
                             first_line, num_lines):
    """Generate the chunks within a range of lines in the specified filediff.

    This is primarily intended for use with templates. It takes a
    RequestContext for looking up the user and for caching file lists,
    in order to improve performance and reduce lookup times for files that have
    already been fetched.

    See :py:func:`get_chunks_in_range` for information on the returned state
    of the chunks.
    """
    f = get_file_from_filediff(context, filediff, interfilediff)

    if f:
        return get_chunks_in_range(f['chunks'], first_line, num_lines)
    else:
        return []


def get_chunks_in_range(chunks, first_line, num_lines):
    """Generate the chunks within a range of lines of a larger list of chunks.

    This takes a list of chunks, computes a subset of those chunks from the
    line ranges provided, and generates a new set of those chunks.

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
    for i, chunk in enumerate(chunks):
        lines = chunk['lines']

        if lines[-1][0] >= first_line >= lines[0][0]:
            start_index = first_line - lines[0][0]

            if first_line + num_lines <= lines[-1][0]:
                last_index = start_index + num_lines
            else:
                last_index = len(lines)

            new_chunk = {
                'index': i,
                'lines': chunk['lines'][start_index:last_index],
                'numlines': last_index - start_index,
                'change': chunk['change'],
                'meta': chunk.get('meta', {}),
            }

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
    extension in descending order. This will make :file:`*.h` sort ahead of
    :file:`*.c`/:file:`*.cpp`, for example.

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

        filename = filediff.dest_file
        i = filename.rfind('/')

        if i == -1:
            return '', filename
        else:
            return filename[:i], filename[i + 1:]

    return sorted(filediffs, cmp=cmp_filediffs, key=make_key)


def get_displayed_diff_line_ranges(chunks, first_vlinenum, last_vlinenum):
    """Return the displayed line ranges based on virtual line numbers.

    This takes the virtual line numbers (the index in the side-by-side diff
    lines) and returns the human-readable line numbers, the chunks they're in,
    and mapped virtual line numbers.

    A virtual line range may start or end in a chunk not containing displayed
    line numbers (such as an "original" range starting/ending in an "insert"
    chunk). The resulting displayed line ranges will exclude these chunks.

    Args:
        chunks (list of dict):
            The list of chunks for the diff.

        first_vlinenum (int):
            The first virtual line number. This uses 1-based indexes.

        last_vlinenum (int):
            The last virtual line number. This uses 1-based indexes.

    Returns:
        tuple:
        A tuple of displayed line range information, containing 2 items.

        Each item will either be a dictionary of information, or ``None``
        if there aren't any displayed lines to show.

        The dictionary contains the following keys:

        ``display_range``:
            A tuple containing the displayed line range.

        ``virtual_range``:
            A tuple containing the virtual line range that ``display_range``
            maps to.

        ``chunk_range``:
            A tuple containing the beginning/ending chunks that
            ``display_range`` maps to.

    Raises:
        ValueError:
            The range provided was invalid.
    """
    if first_vlinenum < 0:
        raise ValueError('first_vlinenum must be >= 0')

    if last_vlinenum < first_vlinenum:
        raise ValueError('last_vlinenum must be >= first_vlinenum')

    orig_start_linenum = None
    orig_end_linenum = None
    orig_start_chunk = None
    orig_last_valid_chunk = None
    patched_start_linenum = None
    patched_end_linenum = None
    patched_start_chunk = None
    patched_last_valid_chunk = None

    for chunk in chunks:
        lines = chunk['lines']

        if not lines:
            logging.warning('get_displayed_diff_line_ranges: Encountered '
                            'empty chunk %r',
                            chunk)
            continue

        first_line = lines[0]
        last_line = lines[-1]
        chunk_first_vlinenum = first_line[0]
        chunk_last_vlinenum = last_line[0]

        if first_vlinenum > chunk_last_vlinenum:
            # We're too early. There won't be anything of interest here.
            continue

        if last_vlinenum < chunk_first_vlinenum:
            # We're not going to find anything useful at this point, so bail.
            break

        change = chunk['change']
        valid_for_orig = (change != 'insert' and first_line[1])
        valid_for_patched = (change != 'delete' and first_line[4])

        if valid_for_orig:
            orig_last_valid_chunk = chunk

            if not orig_start_chunk:
                orig_start_chunk = chunk

        if valid_for_patched:
            patched_last_valid_chunk = chunk

            if not patched_start_chunk:
                patched_start_chunk = chunk

        if chunk_first_vlinenum <= first_vlinenum <= chunk_last_vlinenum:
            # This chunk contains the first line that can possibly be used for
            # the comment range. We know the start and end virtual line numbers
            # in the range, so we can compute the proper offset.
            offset = first_vlinenum - chunk_first_vlinenum

            if valid_for_orig:
                orig_start_linenum = first_line[1] + offset
                orig_start_vlinenum = first_line[0] + offset

            if valid_for_patched:
                patched_start_linenum = first_line[4] + offset
                patched_start_vlinenum = first_line[0] + offset
        elif first_vlinenum < chunk_first_vlinenum:
            # One side of the the comment range may not have started in a valid
            # chunk (this would happen if a comment began in an insert or
            # delete chunk). If that happened, we may not have been able to set
            # the beginning of the range in the condition above. Check for this
            # and try setting it now.
            if orig_start_linenum is None and valid_for_orig:
                orig_start_linenum = first_line[1]
                orig_start_vlinenum = first_line[0]

            if patched_start_linenum is None and valid_for_patched:
                patched_start_linenum = first_line[4]
                patched_start_vlinenum = first_line[0]

    # Figure out the end ranges, now that we know the valid ending chunks of
    # each. We're going to try to get the line within the chunk that represents
    # the end, if within the chunk, capping it to the last line in the chunk.
    #
    # If a particular range did not have a valid chunk anywhere in that range,
    # we're going to invalidate the entire range.
    if orig_last_valid_chunk:
        lines = orig_last_valid_chunk['lines']
        first_line = lines[0]
        last_line = lines[-1]
        offset = last_vlinenum - first_line[0]

        orig_end_linenum = min(last_line[1], first_line[1] + offset)
        orig_end_vlinenum = min(last_line[0], first_line[0] + offset)

        assert orig_end_linenum >= orig_start_linenum
        assert orig_end_vlinenum >= orig_start_vlinenum

        orig_range_info = {
            'display_range': (orig_start_linenum, orig_end_linenum),
            'virtual_range': (orig_start_vlinenum, orig_end_vlinenum),
            'chunk_range': (orig_start_chunk, orig_last_valid_chunk),
        }
    else:
        orig_range_info = None

    if patched_last_valid_chunk:
        lines = patched_last_valid_chunk['lines']
        first_line = lines[0]
        last_line = lines[-1]
        offset = last_vlinenum - first_line[0]

        patched_end_linenum = min(last_line[4], first_line[4] + offset)
        patched_end_vlinenum = min(last_line[0], first_line[0] + offset)

        assert patched_end_linenum >= patched_start_linenum
        assert patched_end_vlinenum >= patched_start_vlinenum

        patched_range_info = {
            'display_range': (patched_start_linenum, patched_end_linenum),
            'virtual_range': (patched_start_vlinenum, patched_end_vlinenum),
            'chunk_range': (patched_start_chunk, patched_last_valid_chunk),
        }
    else:
        patched_range_info = None

    return orig_range_info, patched_range_info
