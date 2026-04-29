"""Diff processing and filtering logic.

.. note::

   Functions in here are considered internal API for the diff processing
   logic. Signatures and behavior may change without a deprecation process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from django.http import HttpRequest
    from typing_extensions import TypeAlias

    from reviewboard.diffviewer.differ import Differ

    _InterdiffChangeRange: TypeAlias = tuple[int, int]


def _get_interdiff_change_ranges(
    *,
    differ: Differ,
) -> Iterator[_InterdiffChangeRange]:
    """Return change ranges for one side of an interdiff.

    This runs a diff on the original and patched file content, collecting
    the ranges of modified lines. These will be used by the interdiff
    filtering algorithm to determine which lines should be shown and which
    should be filtered out.

    The same differ must be used for both range generation and opcode
    generation in order to ensure that ranges will line up.

    The returned ranges are in ``[start, end)`` form, meaning ``start`` is
    inclusive and ``end`` is exclusive (one past the end of the changed
    lines).

    Version Added:
        8.0

    Args:
        differ (reviewboard.diffviewer.differ.Differ):
            The differ used to generate the ranges.

    Yields:
        tuple:
        A 2-tuple of the changed region in the form of:

        Tuple:
            0 (int):
                The start of the range (inclusive).

            1 (int):
                The end of the range (exclusive).
    """
    pending_range: (_InterdiffChangeRange | None) = None

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag != 'equal' and j1 != j2:
            if pending_range is not None and pending_range[1] >= j1:
                # Extend the existing range.
                pending_range = (pending_range[0], j2)
            else:
                # Yield what we already have before we replace it.
                if pending_range is not None:
                    yield pending_range

                pending_range = (j1, j2)

    # Yield the final range, now that we're done with the opcodes.
    if pending_range is not None:
        yield pending_range


def filter_interdiff_opcodes(
    *,
    opcodes: Iterable[tuple[str, int, int, int, int]],
    differ: Differ,
    filediff_orig_lines: Sequence[str],
    interfilediff_orig_lines: Sequence[str],
    request: (HttpRequest | None) = None,
) -> Iterator[tuple[str, int, int, int, int]]:
    """Filter the opcodes for an interdiff to remove unnecessary lines.

    An interdiff may contain lines of code that have changed as the result of
    updates to the tree between the time that the first and second diff were
    created. This leads to some annoyances when reviewing.

    This function will filter the opcodes to remove as much of this as
    possible. It will only output non-"equal" opcodes if it falls into the
    ranges of lines dictated in the uploaded diff files.

    Version Changed:
        8.0:
        * Support for the v1 and v2 interdiff filtering algorithms have been
          removed. This now uses the v3 algorithm for dual-phase splitting,
          range considerations, and consistent differs, which produces more
          reliable results.

        * Added ``filediff_orig_lines``, ``interfilediff_orig_lines``, and
          ``differ`` parameters, used for the v3 algorithm.

        * Removed the old ``filediff_data`` and ``interfilediff_data``
          parameters.

    Version Changed:
        3.0.18:
        Added the ``request`` argument, and added support for the version 2
        algorithm from Review Board 4.0 (through the :py:data:`~reviewboard
        .diffviewer.features.filter_interdiffs_v2_feature` feature).

    Args:
        opcodes (list of tuple):
            The list of opcodes to filter.

        differ (reviewboard.diffviewer.differ.Differ, optional):
            The differ used for the interdiff comparison.

            This is used to retrieve opcodes for the patched versions of
            both ends of the interdiff.

            Version Added:
                8.0

        filediff_orig_lines (list of str, optional):
            The lines of the original file before the filediff was applied.

            Version Added:
                8.0

        interfilediff_orig_lines (list of str, optional):
            The lines of the original file before the interfilediff was
            applied.

            Version Added:
                8.0

        request (django.http.HttpRequest, optional):
            The HTTP request from the client.

    Yields:
        tuple:
        An opcode to render for the diff.
    """
    # Fetch the changed regions from within the two diff files, and grab the
    # first entry in each, if available.
    differ_cls = type(differ)
    orig_ranges = _get_interdiff_change_ranges(
        differ=differ_cls(
            a=filediff_orig_lines,
            b=differ.a,
            ignore_space=differ.ignore_space,
            compat_version=differ.compat_version,
        ),
    )
    new_ranges = _get_interdiff_change_ranges(
        differ=differ_cls(
            a=interfilediff_orig_lines,
            b=differ.b,
            ignore_space=differ.ignore_space,
            compat_version=differ.compat_version,
        ),
    )

    try:
        orig_range = next(orig_ranges)
    except StopIteration:
        orig_range = None

    try:
        new_range = next(new_ranges)
    except StopIteration:
        new_range = None

    if not orig_range and not new_range:
        # There's nothing in here. Just yield the original opcodes, disabling
        # filtering.
        yield from opcodes

        return

    # Interdiff filtering version 3.
    #
    # Okay, let's go over the approach.
    #
    # There are two main pieces of data we're working with:
    #
    # 1. The diff opcodes coming from the opcode generator.
    #
    #    These featuring a tag (delete, equal, insert, replace), and
    #    [i1, i2), [j1, j2) opcode ranges.
    #
    # 2. Changed ranges for both sides of the interdiff.
    #
    #    To generate each list of changed ranges, the differ (same one used
    #    for this interdiff, with the same settings) is run against the
    #    original and patched versions of the file for the start of the
    #    interdiff and for the end.
    #
    #    The same diff algorithm must be used to ensure that there are no
    #    behavioral differences regarding placement of lines.
    #
    # Based on those, we're going to find which diff opcodes correspond to
    # change ranges, and output those. Any diff opcodes that are outside of
    # those ranges are potential upstream changes not part of the uploaded
    # diff, and will be split out into "filtered-equal" changes. Those will
    # turn back into "equal" changes in post-processing.
    #
    # How we do all this is the complicated part.
    #
    # We start with a main loop that processes the opcodes. This will
    # generally operate on them as they come in from the opcode generation
    # chain, but has a one-entry buffer that can be populated with an opcode
    # that's split and needs further processing.
    #
    # At the start of the loop, we take the change ranges for either side,
    # advancing them if we're past the ends of the previous range.
    #
    # We then begin processing using two phases, each designed to yield an
    # opcode or split it into a "filtered-equal" and a new opcode for
    # further processing.
    #
    # Phase 1: Pre-range split.
    #
    #     An opcode may start before the current range's left boundary
    #     (range[0]) but extend into or past it.
    #
    #     If it starts before a range, the opcode will be split in two at
    #     the start of the range boundary. The part before the range will be
    #     emitted as a "filtered-equal" opcode, and the remainder will be
    #     put into the buffer for immediate re-processing. Since this will
    #     start within the range, it will skip phase 1 in the next iteration
    #     and go straight to phase 2.
    #
    #     If instead the opcode starts within the current range, phase 1
    #     has nothing to do, and we proceed to phase 2.
    #
    #     This is handled for inserts, deletes, and replaces, with their
    #     respective ranges. For inserts and deletes, we only perform the
    #     above checks for the corresponding range. For replaces, we only
    #     split if both sides start before the range, and allow Phase 2 to
    #     handle it if only one side does.
    #
    # Phase 2: Starts-in-range validity check and opcode cap.
    #
    #     An opcode may start within the current range but extend past it.
    #
    #     If it's not even within the range, then it's emitted as a
    #     "filtered-equal". Phase 1 would have caught legitimate cases of
    #     this, so we're in a situation where we couldn't even advance to a
    #     range that would contain this, meaning it's likely past any change
    #     ranges in the diff.
    #
    #     If it starts within the range, but extends past it, then it's split
    #     at the range's right boundary (range[1]). The first part is emitted
    #     as a valid opcode, and the rest is re-queued for further processing
    #     (which may result in further splits from phase 1 or 2, or emitting
    #     as a "filtered-equal").
    #
    #     If it fits fully in the range, then it's emitted as-is.
    #
    #     Like phase 1, this is handled for inserts, deletes, and replaces,
    #     with their respective ranges.
    #
    # The two phases together cover four cases for each opcode:
    #
    # 1. Precedes range (i1 < range[0] and i2 <= range[0]):
    #
    #    The opcode is entirely before the diff change range.
    #
    #    Phase 1 won't kick in (since it's not straddling a range).
    #
    #    Phase 2 will see this as an invalid range and convert to a
    #    "filtered-equal".
    #
    # 2. Straddles start of range (i1 < range[0] and i2 > range[0]):
    #
    #    The opcode straddles the left edge of the range.
    #
    #    Phase 1 will emit the part before the range as a "filtered-equal",
    #    and queue processing of the rest.
    #
    #    Phase 2 will process the rest as one of the next two cases.
    #
    # 3. Fits within range (i1 >= range[0] and i2 <= range[1]):
    #
    #    The opcode fits entirely within the range.
    #
    #    Phase 1 is a no-op (since it doesn't straddle the left of the range).
    #
    #    Phase 2 will emit the opcode as-is.
    #
    # 4. Starts in but exceeds range (i1 >= range[0] and i2 > range[1]):
    #
    #    The opcode starts within the range but extends past it.
    #
    #    Phase 1 is a no-op (since it doesn't straddle the left of the range).
    #
    #    Phase 2 will split at range[1], emit the first part as a valid
    #    opcode, and then either queue processing the rest or emit it as a
    #    "filtered-equal" if there are no more ranges.
    #
    # The result of all this should be "insert", "replace", or "delete"
    # opcodes that correspond to modified ranges within the diff, filtering
    # out anything else as equals.
    #
    # Version 3 of the algorithm was introduced in Review Board 8. Version 2
    # had the Phase 2 behavior, with some workarounds to avoid losing some
    # ranges (but did in some edge cases).
    opcodes_iter = iter(opcodes)
    pending_opcode = None

    # Begin the main opcode processing loop.
    while True:
        # First, we'll begin fetching the opcode we want to process, either
        # from the buffer or the generator.
        if pending_opcode is not None:
            # An opcode was put back in the buffer for re-processing. Use
            # that opcode and clear the buffer.
            tag, i1, i2, j1, j2 = pending_opcode
            pending_opcode = None
        else:
            # Fetch the next opcode from the generator.
            try:
                tag, i1, i2, j1, j2 = next(opcodes_iter)
            except StopIteration:
                break

        # Then advance the range on either side if the corresponding diff
        # opcode has moved beyond the previous one.
        #
        # As a reminder, range[1] is exclusive, so range[1] falls outside of
        # the valid ranges for diff opcodes.
        while orig_range is not None and i1 >= orig_range[1]:
            # We've left the range of the current change to consider in the
            # original diff. Move on to the next one.
            try:
                orig_range = next(orig_ranges)
            except StopIteration:
                # There are no more ranges to consider for the original side.
                orig_range = None

        while new_range is not None and j1 >= new_range[1]:
            # We've left the range of the current change to consider in the
            # new diff. Move on to the next one.
            try:
                new_range = next(new_ranges)
            except StopIteration:
                # There are no more ranges to consider for the modified side.
                new_range = None

        # Phase 1: Pre-range split.
        #
        # If an opcode starts before the current range's left boundary, but
        # also extends into or past it, we split it here. The prefix (up to
        # range[0]) is emitted as a "filtered-equal". The remainder is queued
        # for further processing, and will be handled in phase 2.
        #
        # Without this step, an opcode straddling range[0] would fail the
        # validity check in phase 2 (since i1 < range[0]), and would end up
        # as a "filtered-equal".
        #
        # If it's an equal, we just skip the phase.
        if tag != 'equal':
            orig_needs_split = (
                orig_range is not None and
                tag in {'replace', 'delete'} and
                i1 < orig_range[0] < i2
            )
            new_needs_split = (
                new_range is not None and
                tag in {'replace', 'insert'} and
                j1 < new_range[0] < j2
            )

            if tag == 'replace':
                # A replace opcode will have equal length on both sides, and
                #
                # If only one side starts before its range, phase 2 would
                # consider it valid and perform a cap, and that process would
                # correctly handle alignment of the opcode.
                #
                # If both sides start before their respective range
                # boundaries, they will need to be split.
                needs_split = orig_needs_split and new_needs_split
            else:
                needs_split = orig_needs_split or new_needs_split

            if needs_split:
                if tag == 'insert':
                    assert new_range is not None

                    # Inserts don't affect the orig range, so only the
                    # modified side needs to advance.
                    split_i1 = i1
                    split_j1 = new_range[0]
                elif tag == 'delete':
                    assert orig_range is not None

                    # Deletes don't affect the modified range, so only the
                    # orig side needs to advance.
                    split_i1 = orig_range[0]
                    split_j1 = j1
                else:
                    assert tag == 'replace'

                    # Replace lines affect both ranges, so both need to
                    # advance to a consistent split point.
                    #
                    # We'll compute deltas between the start of the change
                    # range and the opcode position within it.
                    #
                    # The larger of the two deltas will be used for the split
                    # point advancement. This will prevent either side from
                    # ending up behind its range boundary after splitting.
                    if orig_range is not None and i1 < orig_range[0]:
                        orig_delta = orig_range[0] - i1
                    else:
                        orig_delta = 0

                    if new_range is not None and j1 < new_range[0]:
                        new_delta = new_range[0] - j1
                    else:
                        new_delta = 0

                    delta = max(orig_delta, new_delta)
                    split_i1 = i1 + delta
                    split_j1 = j1 + delta

                # Only split if at least one opcode range's split point is
                # before the end of the range.
                if split_i1 < i2 or split_j1 < j2:
                    # Emit the part we've finished processing as a
                    # "filtered-equal".
                    #
                    # These will get turned back into "equal" chunks in the
                    # post-processing step.
                    yield 'filtered-equal', i1, split_i1, j1, split_j1

                    # Queue the remainder to be processed next.
                    pending_opcode = (tag, split_i1, i2, split_j1, j2)

                    continue

        # Phase 2: Starts-in-range validity check and opcode cap.
        #
        # At this point the opcode starts at or after range[0] (Phase 1
        # ensured that for straddling opcodes). Check whether it falls inside
        # either the orig or new valid range.
        #
        # If either side of the diff opcode has a zero length range
        # (i1 == i2 or j1 == j2), then that's either the new side of a
        # delete or the orig side of an insert. Those aren't considered
        # valid ranges, since there's no content there.
        #
        # Change ranges are [start, end), meaning the end is exclusive. That
        # end may fall within the lines of context or, theoretically, in
        # another range. We'll check if the op is safely within the allowed
        # part of range, for each side.
        orig_starts_valid = (
            i1 != i2 and
            orig_range is not None and
            orig_range[0] <= i1 < orig_range[1]
        )
        new_starts_valid = (
            j1 != j2 and
            new_range is not None and
            new_range[0] <= j1 < new_range[1]
        )

        valid_chunk = orig_starts_valid or new_starts_valid

        if not valid_chunk:
            # The opcode is entirely outside all current valid ranges.
            # Emit it as "filtered-equal".
            #
            # These will get turned back into "equal" chunks in the
            # post-processing step.
            yield 'filtered-equal', i1, i2, j1, j2

            continue

        # The opcode is valid. It may extend past the current range's right
        # boundary (range[1]), so clip each side to the range end.
        if orig_range:
            cap_i2 = orig_range[1]
        else:
            cap_i2 = i2

        if new_range:
            cap_j2 = new_range[1]
        else:
            cap_j2 = j2

        # Determine the end of the valid range for each side.
        if orig_starts_valid:
            valid_i2 = min(i2, cap_i2)
        else:
            valid_i2 = i2

        if new_starts_valid:
            valid_j2 = min(j2, cap_j2)
        else:
            valid_j2 = j2

        if tag in {'equal', 'replace'}:
            # A replace (or equal) opcode must always be of equal length on
            # both the orig and modified sides. We need to determine the end
            # point of this capped range:
            #
            # * If the orig side went out of bounds (valid_i2 > cap_i2),
            #   the modified side is in bounds, so we'll use the modified
            #   length.
            #
            # * If the modified side went out of bounds, the orig side wins
            #   (for the same reasons as above).
            #
            # * If both are in bounds, the longer of the two wins. This
            #   prevents discarding lines that one side still considers valid.
            i_diff = valid_i2 - i1
            j_diff = valid_j2 - j1

            if valid_i2 > cap_i2:
                # Sanity-check that valid_j2 is in bounds. We don't need
                # to check this in the following conditionals, though,
                # since that's covered by the conditionals themselves.
                assert valid_j2 <= cap_j2

                max_cap = j_diff
            elif valid_j2 > cap_j2:
                max_cap = i_diff
            else:
                max_cap = max(i_diff, j_diff)

            # Clamp to the actual opcode bounds so valid_i2/valid_j2 cannot
            # exceed i2/j2 (which would spill over into the next opcode).
            max_cap = min(max_cap, i2 - i1, j2 - j1)

            # Set each valid range to be the same length.
            valid_i2 = i1 + max_cap
            valid_j2 = j1 + max_cap

            # Update the caps to match the computed ends of the opcode ranges
            # so that any splitting will start here later.
            cap_i2 = valid_i2
            cap_j2 = valid_j2

        # Emit the valid part of this opcode.
        yield tag, i1, valid_i2, j1, valid_j2

        # Check if we've handled the full opcode (meaning it's fully in
        # range), or if we need to split out part for re-processing.
        if valid_i2 != i2 or valid_j2 != j2:
            # The opcode extended past the current range. Advance i1/j1 to
            # the start of the remaining part of the opcode where it was
            # split.
            if orig_range is not None and i2 + 1 > cap_i2:
                i1 = cap_i2
            elif orig_range is None and valid_i2 < i2:
                i1 = valid_i2

            if new_range is not None and j2 + 1 > cap_j2:
                j1 = cap_j2
            elif new_range is None and valid_j2 < j2:
                j1 = valid_j2

            # Re-queue the split-off opcode so it can be checked in the next
            # iteration.
            pending_opcode = (tag, i1, i2, j1, j2)


def post_process_filtered_equals(opcodes):
    """Post-processes filtered-equal and equal chunks from interdiffs.

    Any filtered-out "filtered-equal" chunks will get turned back into "equal"
    chunks and merged into any prior equal chunks. Likewise, simple "equal"
    chunks will also get merged.

    "equal" chunks that have any indentation information will remain
    their own chunks, with nothing merged in.
    """
    cur_chunk = None

    for tag, i1, i2, j1, j2, meta in opcodes:
        if ((tag == 'equal' and not meta.get('indentation_changes')) or
            tag == 'filtered-equal'):
            # We either have a plain equal chunk without any indentation
            # changes, or a filtered-equal chunk. In these cases, we can
            # safely merge the chunks together and transform them into
            # an "equal" chunk.
            if cur_chunk:
                i1 = cur_chunk[1]
                j1 = cur_chunk[3]
                meta = cur_chunk[5]

            cur_chunk = ('equal', i1, i2, j1, j2, meta)
        else:
            # This is some sort of changed chunk (insert, delete, replace,
            # or equal with indentation changes). Yield the previous chunk
            # we were working with, if any, and then yield the current chunk.
            if cur_chunk:
                yield cur_chunk
                cur_chunk = None

            yield tag, i1, i2, j1, j2, meta

    if cur_chunk:
        yield cur_chunk
