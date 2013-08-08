from __future__ import with_statement
import os
import re
import subprocess
import tempfile

from django.utils.translation import ugettext as _

from djblets.log import log_timed
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.contextmanagers import controlled_subprocess

from reviewboard.accounts.models import Profile
from reviewboard.admin.checks import get_can_enable_syntax_highlighting
from reviewboard.scmtools.core import PRE_CREATION, HEAD


NEW_FILE_STR = _("New File")
NEW_CHANGE_STR = _("New Change")

NEWLINE_CONVERSION_RE = re.compile(r'\r(\r?\n)?')

ALPHANUM_RE = re.compile(r'\w')
WHITESPACE_RE = re.compile(r'\s')


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
    if data == "":
        return ""

    if data[-1] == "\r":
        data = data[:-1]

    return NEWLINE_CONVERSION_RE.sub('\n', data)


def patch(diff, file, filename, request=None):
    """Apply a diff to a file.  Delegates out to `patch` because noone
       except Larry Wall knows how to patch."""

    log_timer = log_timed("Patching file %s" % filename,
                          request=request)

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

    newfile = '%s-new' % oldfile

    process = subprocess.Popen(['patch', '-o', newfile, oldfile],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

    with controlled_subprocess("patch", process) as p:
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


def get_original_file(filediff, request=None):
    """
    Get a file either from the cache or the SCM, applying the parent diff if
    it exists.

    SCM exceptions are passed back to the caller.
    """
    data = ""

    if filediff.source_revision != PRE_CREATION:
        repository = filediff.diffset.repository
        data = repository.get_file(
            filediff.source_file,
            filediff.source_revision,
            base_commit_id=filediff.diffset.base_commit_id,
            request=request)

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

    # If there's a parent diff set, apply it to the buffer.
    if filediff.parent_diff:
        data = patch(filediff.parent_diff, data, filediff.source_file,
                     request)

    return data


def get_patched_file(buffer, filediff, request=None):
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
        return "Revision %s" % revision


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

    if interdiffset:
        for interfilediff in interdiffset.files.all():
            if (not filediff or
                filediff.source_file == interfilediff.source_file):
                interdiff_map[interfilediff.source_file] = interfilediff

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
         interdiff_map.pop(temp_filediff.source_file, None),
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
            for interdiff in interdiff_map.itervalues()
        ]

    files = []

    for parts in filediff_parts:
        filediff, interfilediff, force_interdiff = parts

        newfile = (filediff.source_revision == PRE_CREATION)

        if interdiffset:
            # First, find out if we want to even process this one.
            # We only process if there's a difference in files.

            if (filediff and interfilediff and
                filediff.diff == interfilediff.diff):
                continue

            source_revision = "Diff Revision %s" % diffset.revision

            if not interfilediff and force_interdiff:
                dest_revision = "Diff Revision %s - File Reverted" % \
                                interdiffset.revision
            else:
                dest_revision = "Diff Revision %s" % interdiffset.revision
        else:
            source_revision = get_revision_str(filediff.source_revision)

            if newfile:
                dest_revision = NEW_FILE_STR
            else:
                dest_revision = NEW_CHANGE_STR

        i = filediff.source_file.rfind('/')

        if i != -1:
            basepath = filediff.source_file[:i]
            basename = filediff.source_file[i + 1:]
        else:
            basepath = ""
            basename = filediff.source_file

        tool = filediff.diffset.repository.get_scmtool()
        depot_filename = tool.normalize_path_for_display(filediff.source_file)
        dest_filename = tool.normalize_path_for_display(filediff.dest_file)

        files.append({
            'depot_filename': depot_filename,
            'dest_filename': dest_filename or depot_filename,
            'basename': basename,
            'basepath': basepath,
            'revision': source_revision,
            'dest_revision': dest_revision,
            'filediff': filediff,
            'interfilediff': interfilediff,
            'force_interdiff': force_interdiff,
            'binary': filediff.binary,
            'deleted': filediff.deleted,
            'moved': filediff.moved,
            'newfile': newfile,
            'index': len(files),
            'chunks_loaded': False,
        })

    def cmp_file(x, y):
        # Sort based on basepath in asc order
        if x["basepath"] != y["basepath"]:
            return cmp(x["basepath"], y["basepath"])

        # Sort based on filename in asc order, then based on extension in desc
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
            'whitespace_only': True,
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
        except Profile.DoesNotExist:
            pass

    siteconfig = SiteConfiguration.objects.get_current()
    return (siteconfig.get('diffviewer_syntax_highlighting') and
            user_syntax_highlighting and
            get_can_enable_syntax_highlighting())
