"""Utilities for creating FileDiffs."""

from __future__ import unicode_literals

import os
from functools import cmp_to_key

from django.utils.encoding import force_bytes, force_text
from django.utils.translation import ugettext as _
from djblets.util.compat.python.past import cmp

from reviewboard.diffviewer.errors import EmptyDiffError
from reviewboard.scmtools.core import (FileNotFoundError,
                                       PRE_CREATION,
                                       Revision,
                                       UNKNOWN)


# Extensions used for intelligent sorting of header files
# before implementation files.
_HEADER_EXTENSIONS = [
    b'h', b'H', b'hh', b'hpp', b'hxx', b'h++'
]

_IMPL_EXTENSIONS = [
    b'c', b'C', b'cc', b'cpp', b'cxx', b'c++', b'm', b'mm', b'M'
]


def create_filediffs(diff_file_contents, parent_diff_file_contents,
                     repository, basedir, base_commit_id, diffset,
                     request=None, check_existence=True, get_file_exists=None,
                     diffcommit=None, validate_only=False):
    """Create FileDiffs from the given data.

    Args:
        diff_file_contents (bytes):
            The contents of the diff file.

        parent_diff_file_contents (bytes):
            The contents of the parent diff file.

        repository (reviewboard.scmtools.models.Repository):
            The repository the diff is being posted against.

        basedir (unicode):
            The base directory to prepend to all file paths in the diff.

        base_commit_id (unicode):
            The ID of the commit that the diff is based upon. This is
            needed by some SCMs or hosting services to properly look up
            files, if the diffs represent blob IDs instead of commit IDs
            and the service doesn't support those lookups.

        diffset (reviewboard.diffviewer.models.diffset.DiffSet):
            The DiffSet to attach the created FileDiffs to.

        request (django.http.HttpRequest, optional):
            The current HTTP request.

        check_existence (bool, optional):
            Whether or not existence checks should be performed against
            the upstream repository.

            This argument defaults to ``True``.

        get_file_exists (callable, optional):
            A callable that is used to determine if a file exists.

            This must be provided if ``check_existence`` is ``True``.

        diffcommit (reviewboard.diffviewer.models.diffcommit.DiffCommit,
                    optional):
            The Diffcommit to attach the created FileDiffs to.

        validate_only (bool, optional):
            Whether to just validate and not save. If ``True``, then this
            won't populate the database at all and will return ``None``
            upon success. This defaults to ``False``.

    Returns:
        list of reviewboard.diffviewer.models.filediff.FileDiff:
        The created FileDiffs.

        If ``validate_only`` is ``True``, the returned list will be empty.
    """
    from reviewboard.diffviewer.diffutils import convert_to_unicode
    from reviewboard.diffviewer.models import FileDiff

    files, parser, parent_commit_id, parent_files = _prepare_file_list(
        diff_file_contents=diff_file_contents,
        parent_diff_file_contents=parent_diff_file_contents,
        repository=repository,
        request=request,
        basedir=basedir,
        check_existence=check_existence,
        get_file_exists=get_file_exists,
        base_commit_id=base_commit_id)

    encoding_list = repository.get_encoding_list()
    filediffs = []

    for f in files:
        parent_file = None
        parent_content = b''

        extra_data = f.extra_data.copy()
        extra_data['is_symlink'] = f.is_symlink

        if f.orig_filename in parent_files:
            parent_file = parent_files[f.orig_filename]
            parent_content = parent_file.data

            # Store the information on the parent's filename and revision.
            # It's important we force these to text, since they may be
            # byte strings and the revision may be a Revision instance.
            extra_data.update({
                'parent_source_filename':
                    convert_to_unicode(parent_file.orig_filename,
                                       encoding_list)[1],
                'parent_source_revision':
                    convert_to_unicode(parent_file.orig_file_details,
                                       encoding_list)[1],
            })

            if parent_file.moved or parent_file.copied:
                extra_data['parent_moved'] = True

            extra_data[FileDiff._IS_PARENT_EMPTY_KEY] = (
                parent_file.insert_count == 0 and
                parent_file.delete_count == 0
            )

        # If there is a parent file there is not necessarily an original
        # revision for the parent file in the case of a renamed file in
        # git.
        if parent_commit_id and f.orig_file_details != PRE_CREATION:
            orig_rev = parent_commit_id
        else:
            orig_rev = f.orig_file_details

        orig_file = convert_to_unicode(f.orig_filename, encoding_list)[1]
        dest_file = convert_to_unicode(f.modified_filename, encoding_list)[1]

        if f.deleted:
            status = FileDiff.DELETED
        elif f.moved:
            status = FileDiff.MOVED
        elif f.copied:
            status = FileDiff.COPIED
        else:
            status = FileDiff.MODIFIED

        filediff = FileDiff(
            diffset=diffset,
            commit=diffcommit,
            source_file=parser.normalize_diff_filename(orig_file),
            dest_file=parser.normalize_diff_filename(dest_file),
            source_revision=force_text(orig_rev),
            dest_detail=force_text(f.modified_file_details),
            binary=f.binary,
            status=status,
            extra_data=extra_data)

        if not validate_only:
            # This state all requires making modifications to the database.
            # We only want to do this if we're saving.
            filediff.diff = f.data
            filediff.parent_diff = parent_content

            filediff.set_line_counts(raw_insert_count=f.insert_count,
                                     raw_delete_count=f.delete_count)

        filediffs.append(filediff)

    if not validate_only:
        FileDiff.objects.bulk_create(filediffs)
        num_filediffs = len(filediffs)

    return filediffs


def _prepare_file_list(diff_file_contents, parent_diff_file_contents,
                       repository, request, basedir, check_existence,
                       get_file_exists=None, base_commit_id=None):
    """Extract the list of files from the diff.

    Args:
        diff_file_contents (bytes):
            The contents of the diff.

        parent_diff_file_contents (bytes):
            The contents of the parent diff, if any.

        repository (reviewboard.scmtools.models.Repository):
            The repository against which the diff was created.

        request (django.http.HttpRequest):
            The current HTTP request.

        basedir (unicode):
            The base directory to prepend to all file paths in the diff.

        check_existence (bool):
            Whether or not existence checks should be performed against
            the upstream repository.

        get_file_exists (callable, optional):
            A callable to use to determine if a file exists in the repository.

            This argument must be provided if ``check_existence`` is ``True``.

        base_commit_id (unicode, optional):
            The ID of the commit that the diff is based upon. This is
            needed by some SCMs or hosting services to properly look up
            files, if the diffs represent blob IDs instead of commit IDs
            and the service doesn't support those lookups.

    Returns:
        tuple:
        A tuple of the following:

        * The files in the diff. (:py:class:`list` of
          :py:class:`ParsedDiffFile`)
        * The diff parser.
          (:py:class:`reviewboard.diffviewer.parser.DiffParser`)
        * The parent commit ID or ``None`` if not applicable.
          (:py:class:`unicode`)
        * A dictionary of files in the parent diff. (:py:class:`dict`)

    Raises:
        reviewboard.diffviewer.errors.EmptyDiffError:
            The diff contains no files.

        ValueError:
            ``check_existence`` was ``True`` but ``get_file_exists`` was not
            provided.
    """
    if check_existence and get_file_exists is None:
        raise ValueError('Must provide get_file_exists when check_existence '
                         'is True')

    tool = repository.get_scmtool()
    parser = tool.get_parser(diff_file_contents)
    files = list(_process_files(
        parser=parser,
        basedir=basedir,
        repository=repository,
        base_commit_id=base_commit_id,
        request=request,
        check_existence=(check_existence and
                         not parent_diff_file_contents),
        get_file_exists=get_file_exists))

    if len(files) == 0:
        raise EmptyDiffError(_('The diff is empty.'))

    # Sort the files so that header files come before implementation
    # files.
    files.sort(key=cmp_to_key(_compare_files))

    parent_files = {}

    # This is used only for tools like Mercurial that use atomic changeset
    # IDs to identify all file versions. but not individual file version
    # IDs.
    parent_commit_id = None

    if parent_diff_file_contents:
        diff_filenames = {f.orig_filename for f in files}
        parent_parser = tool.get_parser(parent_diff_file_contents)

        # If the user supplied a base diff, we need to parse it and later
        # apply each of the files that are in main diff.
        parent_files = {
            f.modified_filename: f
            for f in _process_files(
                get_file_exists=get_file_exists,
                parser=parent_parser,
                basedir=basedir,
                repository=repository,
                base_commit_id=base_commit_id,
                request=request,
                check_existence=check_existence,
                limit_to=diff_filenames)
        }

        # This will return a non-None value only for tools that use commit
        # IDs to identify file versions as opposed to file revision IDs.
        parent_commit_id = parent_parser.get_orig_commit_id()

    return files, parser, parent_commit_id, parent_files


def _process_files(parser, basedir, repository, base_commit_id,
                   request, get_file_exists=None, check_existence=False,
                   limit_to=None):
    """Collect metadata about files in the parser.

    Args:
        parser (reviewboard.diffviewer.parser.DiffParser):
            A DiffParser instance for the diff.

        basedir (unicode):
            The base directory to prepend to all file paths in the diff.

        repository (reviewboard.scmtools.models.Repository):
            The repository that the diff was created against.

        base_commit_id (unicode):
            The ID of the commit that the diff is based upon. This is
            needed by some SCMs or hosting services to properly look up
            files, if the diffs represent blob IDs instead of commit IDs
            and the service doesn't support those lookups.

        request (django.http.HttpRequest):
            The current HTTP request.

        check_existence (bool, optional):
            Whether or not existence checks should be performed against
            the upstream repository.

        get_file_exists (callable, optional):
            A callable to use to determine if a given file exists in the
            repository.

            If ``check_existence`` is ``True`` this argument must be
            provided.

        limit_to (list of unicode, optional):
            A list of filenames to limit the results to.

    Yields:
       reviewboard.diffviewer.parser.ParsedDiffFile:
       The files present in the diff.

    Raises:
        ValueError:
            ``check_existence`` was ``True`` but ``get_file_exists`` was not
            provided.
    """
    if check_existence and get_file_exists is None:
        raise ValueError('Must provide get_file_exists when check_existence '
                         'is True')

    tool = repository.get_scmtool()
    basedir = force_bytes(basedir)

    for f in parser.parse():
        # This will either be a Revision or bytes. Either way, convert it
        # bytes now.
        orig_revision = force_bytes(f.orig_file_details)

        source_filename, source_revision = tool.parse_diff_revision(
            f.orig_filename,
            orig_revision,
            moved=f.moved,
            copied=f.copied)

        assert isinstance(source_filename, bytes), (
            '%s.parse_diff_revision() must return a bytes filename, not %r'
            % (type(tool).__name__, type(source_filename)))
        assert isinstance(source_revision, (bytes, Revision)), (
            '%s.parse_diff_revision() must return a revision which is either '
            'bytes or reviewboard.scmtools.core.Revision, not %r'
            % (type(tool).__name__, type(source_revision)))

        dest_filename = _normalize_filename(f.modified_filename, basedir)

        if limit_to is not None and dest_filename not in limit_to:
            # This file isn't actually needed for the diff, so save
            # ourselves a remote file existence check and some storage.
            continue

        source_filename = _normalize_filename(source_filename, basedir)

        # FIXME: this would be a good place to find permissions errors
        if (source_revision != PRE_CREATION and
            source_revision != UNKNOWN and
            not f.binary and
            not f.deleted and
            not f.moved and
            not f.copied and
            (check_existence and
             not get_file_exists(force_text(source_filename),
                                 force_text(source_revision),
                                 base_commit_id=base_commit_id,
                                 request=request))):
            raise FileNotFoundError(force_text(source_filename),
                                    force_text(source_revision),
                                    base_commit_id)

        f.orig_filename = source_filename
        f.orig_file_details = source_revision
        f.modified_filename = dest_filename

        yield f


def _compare_files(file1, file2):
    """Compare two files to determine a relative sort order.

    This will compare two files, giving precedence to header files over
    source files. This allows the resulting list of files to be more
    intelligently sorted.

    Args:
        file1 (reviewboard.diffviewer.parser.ParsedDiffFile):
            The first file to compare.

        file2 (reviewboard.diffviewer.parser.ParsedDiffFile):
            The second file to compare.

    Returns:
        int:
        -1 if ``file1`` should appear before ``file2``.

        0 if ``file1`` and ``file2`` are considered equal.

        1 if ``file1`` should appear after ``file2``.
    """
    filename1 = file1.orig_filename
    filename2 = file2.orig_filename

    if filename1.find(b'.') != -1 and filename2.find(b'.') != -1:
        basename1, ext1 = filename1.rsplit(b'.', 1)
        basename2, ext2 = filename2.rsplit(b'.', 1)

        if basename1 == basename2:
            if (ext1 in _HEADER_EXTENSIONS and ext2 in _IMPL_EXTENSIONS):
                return -1
            elif (ext1 in _IMPL_EXTENSIONS and ext2 in _HEADER_EXTENSIONS):
                return 1

    return cmp(filename1, filename2)


def _normalize_filename(filename, basedir):
    """Normalize a filename to be relative to the repository root.

    Args:
        filename (bytes):
            The filename to normalize.

        basedir (bytes):
            The base directory to prepend to all file paths in the diff.

    Returns:
        bytes:
        The filename relative to the repository root.
    """
    assert isinstance(filename, bytes)
    assert isinstance(basedir, bytes)

    if filename.startswith(b'/'):
        return filename

    return os.path.join(basedir, filename).replace(b'\\', b'/')
