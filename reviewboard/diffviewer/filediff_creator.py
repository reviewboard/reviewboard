"""Utilities for creating FileDiffs."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import (Iterator, Mapping, Optional, Protocol, Sequence,
                    TYPE_CHECKING, Union)

from django.utils.encoding import force_bytes, force_str
from django.utils.translation import gettext as _
from housekeeping import deprecate_non_keyword_only_args
from typing_extensions import TypedDict

from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.diffviewer.errors import EmptyDiffError
from reviewboard.scmtools.core import (FileLookupContext,
                                       PRE_CREATION,
                                       Revision,
                                       UNKNOWN)
from reviewboard.scmtools.errors import FileNotFoundError

if TYPE_CHECKING:
    from django.http import HttpRequest

    from reviewboard.diffviewer.models import DiffCommit, DiffSet, FileDiff
    from reviewboard.diffviewer.parser import (BaseDiffParser,
                                               ParsedDiff,
                                               ParsedDiffFile)
    from reviewboard.scmtools.core import SCMTool
    from reviewboard.scmtools.models import Repository

    class _GetFileExistsFunc(Protocol):
        def __call__(
            self,
            *,
            path: str,
            revision: str,
            context: FileLookupContext,
        ) -> bool:
            ...


class _PreparedDiffInfo(TypedDict):
    """Intermediary information on a prepared diff.

    This is used for the FileDiff preparation stages. This is available
    only for internal typing.

    Version Added:
        7.1
    """

    #: All parsed files in the diff.
    files: Sequence[ParsedDiffFile]

    #: A mapping of modified filenames to parsed diff files.
    #:
    #: Each filename corresponds to a file in :py:attr:`files`.
    parent_files: Mapping[bytes, ParsedDiffFile]

    #: The parsed diff file.
    parsed_diff: ParsedDiff

    #: The parsed diff file for the parent diff.
    parsed_parent_diff: Optional[ParsedDiff]

    #: The parent diff file.
    parser: BaseDiffParser


@deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
def create_filediffs(
    *,
    diff_file_contents: bytes,
    parent_diff_file_contents: Optional[bytes],
    repository: Repository,
    basedir: Optional[Union[bytes, str]],
    base_commit_id: Optional[str],
    diffset: DiffSet,
    request: Optional[HttpRequest] = None,
    check_existence: bool = True,
    get_file_exists: Optional[_GetFileExistsFunc] = None,
    diffcommit: Optional[DiffCommit] = None,
    validate_only: bool = False,
) -> Sequence[FileDiff]:
    """Create FileDiffs from the given data.

    Version Changed:
        7.1:
        All arguments are now keyword-only arguments. Passing as positional
        arguments is deprecated and will be removed in Review Board 9.

    Args:
        diff_file_contents (bytes):
            The contents of the diff file.

        parent_diff_file_contents (bytes):
            The contents of the parent diff file.

        repository (reviewboard.scmtools.models.Repository):
            The repository the diff is being posted against.

        basedir (bytes or str):
            The base directory to prepend to all file paths in the diff.

        base_commit_id (str):
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
        basedir=force_bytes(basedir),
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
    filediffs: list[FileDiff] = []

    for f in diff_info['files']:
        parent_file: Optional[ParsedDiffFile] = None
        parent_content: bytes = b''

        extra_data = f.extra_data.copy()

        if parsed_parent_diff is not None:
            if f.orig_filename:
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

            # If this is a Revision, we'll need to ensure we specifically
            # cast it to a bytes before we convert it.
            if isinstance(parent_source_revision, Revision):
                parent_source_revision = bytes(parent_source_revision)

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


def _prepare_diff_info(
    *,
    diff_file_contents: bytes,
    parent_diff_file_contents: Optional[bytes],
    repository: Repository,
    request: Optional[HttpRequest],
    basedir: bytes,
    check_existence: bool,
    get_file_exists: Optional[_GetFileExistsFunc] = None,
    base_commit_id: Optional[str] = None,
) -> _PreparedDiffInfo:
    """Extract information and files from a diff.

    Version Changed:
        7.1:
        All arguments are now keyword-only arguments.

    Args:
        diff_file_contents (bytes):
            The contents of the diff.

        parent_diff_file_contents (bytes):
            The contents of the parent diff, if any.

        repository (reviewboard.scmtools.models.Repository):
            The repository against which the diff was created.

        request (django.http.HttpRequest):
            The current HTTP request.

        basedir (bytes):
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
        _PreparedDiffInfo:
        A dictionary of information about the diff and parser.

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
    parsed_diff = _parse_diff(tool=tool,
                              diff_content=diff_file_contents)

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

    parsed_parent_diff = None
    parent_files: dict[bytes, ParsedDiffFile] = {}

    if parent_diff_file_contents:
        diff_filenames = {
            f.orig_filename
            for f in files
            if f.orig_filename
        }
        parsed_parent_diff = _parse_diff(
            tool=tool,
            diff_content=parent_diff_file_contents)

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
            if f.modified_filename
        }

    return {
        'files': files,
        'parent_files': parent_files,
        'parsed_diff': parsed_diff,
        'parsed_parent_diff': parsed_parent_diff,
        'parser': parsed_diff.parser,
    }


def _parse_diff(
    *,
    tool: SCMTool,
    diff_content: bytes,
) -> ParsedDiff:
    """Parse a diff using the SCMTool's diff parser.

    Version Changed:
        7.1:
        All arguments are now keyword-only arguments.

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


def _process_files(
    *,
    parsed_diff: ParsedDiff,
    basedir: bytes,
    repository: Repository,
    base_commit_id: Optional[str],
    request: Optional[HttpRequest],
    get_file_exists: Optional[_GetFileExistsFunc] = None,
    check_existence: bool = False,
    limit_to: Optional[set[bytes]] = None,
) -> Iterator[ParsedDiffFile]:
    """Collect metadata about files in the parser.

    Version Changed:
        7.1:
        All arguments are now keyword-only arguments.

    Args:
        parsed_diff (reviewboard.diffviewer.parser.ParsedDiff):
            The parsed diff to process.

        basedir (bytes):
            The base directory to prepend to all file paths in the diff.

        repository (reviewboard.scmtools.models.Repository):
            The repository that the diff was created against.

        base_commit_id (str):
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

        limit_to (set of bytes, optional):
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
    parsed_change = parsed_diff.changes[0]

    for f in parsed_change.files:
        # This will either be a Revision or bytes. Either way, convert it
        # bytes now.
        orig_revision = force_bytes(f.orig_file_details)

        assert f.orig_filename is not None
        assert f.modified_filename is not None

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

        dest_filename = _normalize_filename(filename=f.modified_filename,
                                            basedir=basedir)

        if limit_to is not None and dest_filename not in limit_to:
            # This file isn't actually needed for the diff, so save
            # ourselves a remote file existence check and some storage.
            continue

        source_filename = _normalize_filename(filename=source_filename,
                                              basedir=basedir)

        if (check_existence and
            source_revision not in (PRE_CREATION, UNKNOWN) and
            not f.binary and
            not f.deleted and
            not f.moved and
            not f.copied):
            assert get_file_exists is not None

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

            # If validation found a more suitable source revision, then set
            # that instead of what was parsed out of the diff. This is
            # important for SCMs like Mercurial, which support multiple
            # commits but don't have per-file revision information in diffs,
            # so we don't even know the commit that introduced the last change
            # to a file. We can only resolve this during the validation
            # phase.
            #
            # This was added in Review Board 7.0.2.
            validated_parent_id = \
                f.extra_data.pop('__validated_parent_id', None)

            if validated_parent_id is not None:
                assert isinstance(validated_parent_id, str)

                source_revision = validated_parent_id.encode('utf-8')

        f.orig_filename = source_filename
        f.orig_file_details = source_revision
        f.modified_filename = dest_filename

        yield f


def _normalize_filename(
    *,
    filename: bytes,
    basedir: bytes,
) -> bytes:
    """Normalize a filename to be relative to the repository root.

    Version Changed:
        7.1:
        All arguments are now keyword-only arguments.

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
