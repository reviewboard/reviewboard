"""Utilities for creating FileDiffs."""

import os
from copy import deepcopy
from functools import cmp_to_key

from django.utils.encoding import force_bytes, force_str
from django.utils.translation import gettext as _
from djblets.util.compat.python.past import cmp

from reviewboard.diffviewer.errors import EmptyDiffError
from reviewboard.scmtools.core import (FileLookupContext,
                                       PRE_CREATION,
                                       Revision,
                                       UNKNOWN)
from reviewboard.scmtools.errors import FileNotFoundError


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
            The DiffCommit to attach the created FileDiffs to.

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

    diff_info = _prepare_diff_info(
        diff_file_contents=diff_file_contents,
        parent_diff_file_contents=parent_diff_file_contents,
        repository=repository,
        request=request,
        basedir=basedir,
        check_existence=check_existence,
        get_file_exists=get_file_exists,
        base_commit_id=base_commit_id)

    parent_files = diff_info['parent_files']
    parsed_diff = diff_info['parsed_diff']
    parsed_parent_diff = diff_info['parsed_parent_diff']
    parser = diff_info['parser']

    encoding_list = repository.get_encoding_list()

    # Copy over any extra_data for the DiffSet and DiffCommit, if any were
    # set by the parser.
    #
    # We'll do this even if we're validating, to ensure the data can be
    # copied over fine.
    main_extra_data = deepcopy(parsed_diff.extra_data)
    change_extra_data = deepcopy(parsed_diff.changes[0].extra_data)

    if change_extra_data:
        if diffcommit is not None:
            # We've already checked in _parse_diff that there's only a single
            # change in the diff, so we can assume that here.
            diffcommit.extra_data.update(change_extra_data)
        else:
            main_extra_data['change_extra_data'] = change_extra_data

    if main_extra_data:
        diffset.extra_data.update(main_extra_data)

    if parsed_parent_diff is not None:
        parent_extra_data = deepcopy(parsed_parent_diff.extra_data)
        parent_change_extra_data = deepcopy(
            parsed_parent_diff.changes[0].extra_data)

        if parent_change_extra_data:
            if diffcommit is not None:
                diffcommit.extra_data['parent_extra_data'] = \
                    parent_change_extra_data
            else:
                parent_extra_data['change_extra_data'] = \
                    parent_change_extra_data

        if parent_extra_data:
            diffset.extra_data['parent_extra_data'] = parent_extra_data

    # Convert the list of parsed files into FileDiffs.
    filediffs = []

    for f in diff_info['files']:
        parent_file = None
        parent_content = b''

        extra_data = f.extra_data.copy()

        if parsed_parent_diff is not None:
            parent_file = parent_files.get(f.orig_filename)

            if parent_file is not None:
                parent_content = parent_file.data

                # Store the information on the parent's filename and revision.
                # It's important we force these to text, since they may be
                # byte strings and the revision may be a Revision instance.
                parent_source_filename = parent_file.orig_filename
                parent_source_revision = parent_file.orig_file_details

                parent_is_empty = (
                    parent_file.insert_count == 0 and
                    parent_file.delete_count == 0
                )

                if parent_file.moved or parent_file.copied:
                    extra_data['parent_moved'] = True

                if parent_file.extra_data:
                    extra_data['parent_extra_data'] = \
                        parent_file.extra_data.copy()
            else:
                # We don't have an entry, but we still want to record the
                # parent ID, so we have something in common for all the files
                # when looking up the source revision to fetch from the
                # repository.
                parent_is_empty = True
                parent_source_filename = f.orig_filename
                parent_source_revision = f.orig_file_details

                if (parent_source_revision != PRE_CREATION and
                    parsed_diff.uses_commit_ids_as_revisions):
                    # Since the file wasn't explicitly provided in the parent
                    # diff, but the ParsedDiff says that commit IDs are used
                    # as revisions, we can use its parent commit ID as the
                    # parent revision here.
                    parent_commit_id = \
                        parsed_parent_diff.changes[0].parent_commit_id
                    assert parent_commit_id

                    parent_source_revision = parent_commit_id

            # Store the information on the parent's filename and revision.
            # It's important we force these to text, since they may be
            # byte strings and the revision may be a Revision instance.
            #
            # Starting in Review Board 4.0.5, we store this any time there's
            # a parent diff, whether or not the file existed in the parent
            # diff.
            extra_data.update({
                FileDiff._IS_PARENT_EMPTY_KEY: parent_is_empty,
                'parent_source_filename':
                    convert_to_unicode(parent_source_filename,
                                       encoding_list)[1],
                'parent_source_revision':
                    convert_to_unicode(parent_source_revision,
                                       encoding_list)[1],
            })

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
            source_revision=force_str(f.orig_file_details),
            dest_detail=force_str(f.modified_file_details),
            binary=f.binary,
            status=status,
            extra_data=extra_data)

        # Set this unconditionally, for backwards-compatibility purposes.
        # Review Board 4.0.6 introduced attribute wrappers in FileDiff and
        # introduced symlink targets. We ideally would not set this unless
        # it's True, but we don't want to risk breaking any assumptions on
        # its presence at this time.
        filediff.is_symlink = f.is_symlink

        if f.is_symlink:
            if f.old_symlink_target:
                filediff.old_symlink_target = \
                    convert_to_unicode(f.old_symlink_target, encoding_list)[1]

            if f.new_symlink_target:
                filediff.new_symlink_target = \
                    convert_to_unicode(f.new_symlink_target, encoding_list)[1]

        filediff.old_unix_mode = f.old_unix_mode
        filediff.new_unix_mode = f.new_unix_mode

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

        if diffset.extra_data:
            diffset.save(update_fields=('extra_data',))

        if diffcommit is not None and diffcommit.extra_data:
            diffcommit.save(update_fields=('extra_data',))

    return filediffs


def _prepare_diff_info(diff_file_contents, parent_diff_file_contents,
                       repository, request, basedir, check_existence,
                       get_file_exists=None, base_commit_id=None):
    """Extract information and files from a diff.

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
        dict:
        A dictionary of information about the diff and parser. This contains
        the following keys:

        ``files`` (:py:class:`list` of
        :py:class:`reviewboard.diffviewer.parser.ParsedDiffFile):
            All parsed files in the diff.

        ``parent_commit_id`` (:py:class:`unicode`):
            The ID of the parent commit, if any.

        ``parent_files`` (:py:class:`dict`):
            A mapping of modified filenames from ``files`` (:py:class:`bytes`)
            to :py:class:`reviewboard.diffviewer.parser.ParsedDiffFile`
            instances.

        ``parsed_diff`` (:py:class:`ParsedDiff`):
            The parsed diff file.

        ``parsed_parent_diff`` (:py:class:`ParsedDiff`):
            The parsed diff file for the parent diff.

        ``parser`` (:py:class:`BaseDiffParser`):
            The parent diff file.

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
    parsed_diff = _parse_diff(tool, diff_file_contents)

    files = list(_process_files(
        parsed_diff=parsed_diff,
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

    parsed_parent_diff = None
    parent_files = {}

    if parent_diff_file_contents:
        diff_filenames = {f.orig_filename for f in files}
        parsed_parent_diff = _parse_diff(tool, parent_diff_file_contents)

        # If the user supplied a base diff, we need to parse it and later
        # apply each of the files that are in main diff.
        parent_files = {
            f.modified_filename: f
            for f in _process_files(
                get_file_exists=get_file_exists,
                parsed_diff=parsed_parent_diff,
                basedir=basedir,
                repository=repository,
                base_commit_id=base_commit_id,
                request=request,
                check_existence=check_existence,
                limit_to=diff_filenames)
        }

    return {
        'files': files,
        'parent_files': parent_files,
        'parsed_diff': parsed_diff,
        'parsed_parent_diff': parsed_parent_diff,
        'parser': parsed_diff.parser,
    }


def _parse_diff(tool, diff_content):
    """Parse a diff using the SCMTool's diff parser.

    Args:
        tool (reviewboard.scmtools.core.SCMTool):
            The tool providing the diff parser.

        diff_content (bytes):
            The diff content to parse.

    Returns:
        reviewboard.diffviewer.parser.ParsedDiff:
        The resulting parsed diff file.
    """
    parser = tool.get_parser(diff_content)
    parsed_diff = parser.parse_diff()

    # We can only support parsing a single change at this time, and we have to
    # have exactly one. Future architectural work will be needed to allow a
    # single diff to be uploaded that spans multiple commits.
    assert len(parsed_diff.changes) == 1, (
        '%s.parse_diff() must extract exactly one change from a diff.'
        % type(parser).__name__)

    return parsed_diff


def _process_files(parsed_diff, basedir, repository, base_commit_id,
                   request, get_file_exists=None, check_existence=False,
                   limit_to=None):
    """Collect metadata about files in the parser.

    Args:
        parsed_diff (reviewboard.diffviewer.parser.ParsedDiff):
            The parsed diff to process.

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
       Each file present in the diff.

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

    parsed_change = parsed_diff.changes[0]

    for f in parsed_change.files:
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

        if (check_existence and
            source_revision not in (PRE_CREATION, UNKNOWN) and
            not f.binary and
            not f.deleted and
            not f.moved and
            not f.copied):
            context = FileLookupContext(
                request=request,
                base_commit_id=base_commit_id,
                diff_extra_data=parsed_diff.extra_data,
                commit_extra_data=parsed_change.extra_data,
                file_extra_data=f.extra_data)

            if not get_file_exists(path=force_str(source_filename),
                                   revision=force_str(source_revision),
                                   context=context):
                raise FileNotFoundError(path=force_str(source_filename),
                                        revision=force_str(source_revision),
                                        base_commit_id=base_commit_id,
                                        context=context)

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
