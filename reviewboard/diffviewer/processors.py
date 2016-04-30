from __future__ import unicode_literals

import re

from reviewboard.diffviewer.diffutils import split_line_endings


CHUNK_RANGE_RE = re.compile(
    r'^@@ -(?P<orig_start>\d+)(,(?P<orig_len>\d+))? '
    r'\+(?P<new_start>\d+)(,(?P<new_len>\d+))? @@',
    re.M)


def filter_interdiff_opcodes(opcodes, filediff_data, interfilediff_data):
    """Filters the opcodes for an interdiff to remove unnecessary lines.

    An interdiff may contain lines of code that have changed as the result of
    updates to the tree between the time that the first and second diff were
    created. This leads to some annoyances when reviewing.

    This function will filter the opcodes to remove as much of this as
    possible. It will only output non-"equal" opcodes if it falls into the
    ranges of lines dictated in the uploaded diff files.
    """
    def _find_range_info(diff):
        lines = split_line_endings(diff)
        process_changes = False
        process_trailing_context = False
        ranges = []

        chunk_start = None
        chunk_len = 0
        lines_of_context = 0

        # Look through the chunks of the diff, trying to find the amount
        # of context shown at the beginning of each chunk. Though this
        # will usually be 3 lines, it may be fewer or more, depending
        # on file length and diff generation settings.
        for line in lines:
            if process_changes:
                if line.startswith((b'-', b'+')):
                    # We've found the first change in the chunk. We now
                    # know how many lines of context we have.
                    #
                    # We reduce the indexes by 1 because the chunk ranges
                    # in diffs start at 1, and we want a 0-based index.
                    start = chunk_start - 1 + lines_of_context
                    chunk_len -= lines_of_context

                    # We then reduce by 1 again, compensating for the
                    # additional line of context, if any. We must do this
                    # because the first line after a "@@" section is being
                    # counted in lines_of_context, but is also the line
                    # referred to in chunk_start.
                    if lines_of_context > 0:
                        start -= 1

                    ranges.append((start, start + chunk_len))
                    process_changes = False
                    process_trailing_context = True
                    lines_of_context = 0
                    continue
                else:
                    lines_of_context += 1
            elif process_trailing_context:
                if line.startswith(b' '):
                    # This may be a line of context after the modifications
                    # in this chunk. Bump up the counter.
                    lines_of_context += 1
                    continue
                else:
                    # Reset the lines of trailing context, since we hit
                    # something other than an equal line.
                    lines_of_context = 0

            # This was not a change within a chunk, or we weren't processing,
            # so check to see if this is a chunk header instead.
            m = CHUNK_RANGE_RE.match(line)

            if m:
                # It is a chunk header. Start by updating the previous range
                # to factor in the lines of trailing context.
                if process_trailing_context and lines_of_context > 0:
                    last_range = ranges[-1]
                    ranges[-1] = (last_range[0],
                                  last_range[1] - lines_of_context)

                # Next, reset the state for the next range, and pull the line
                # number and length from the header.
                chunk_start = int(m.group('new_start'))
                chunk_len = int(m.group('new_len') or '1')
                process_changes = True
                process_trailing_context = False
                lines_of_context = 0

        # We need to adjust the last range, if we're still processing
        # trailing context.
        if process_trailing_context and lines_of_context > 0:
            last_range = ranges[-1]
            ranges[-1] = (last_range[0],
                          last_range[1] - lines_of_context)

        return ranges

    def _is_range_valid(line_range, tag, i1, i2):
        return (line_range is not None and
                i1 >= line_range[0] and
                (tag == 'delete' or i1 != i2))

    orig_ranges = _find_range_info(filediff_data)
    new_ranges = _find_range_info(interfilediff_data)

    orig_range_i = 0
    new_range_i = 0

    if orig_ranges:
        orig_range = orig_ranges[orig_range_i]
    else:
        orig_range = None

    if new_ranges:
        new_range = new_ranges[new_range_i]
    else:
        new_range = None

    if not orig_range and not new_range:
        # There's nothing in here, or it's not a unified diff. Just yield
        # what we get.
        for tag, i1, i2, j1, j2 in opcodes:
            yield tag, i1, i2, j1, j2

        return

    for tag, i1, i2, j1, j2 in opcodes:
        while orig_range and i1 > orig_range[1]:
            # We've left the range of the current chunk to consider in the
            # original diff. Move on to the next one.
            orig_range_i += 1

            if orig_range_i < len(orig_ranges):
                orig_range = orig_ranges[orig_range_i]
            else:
                orig_range = None

        while new_range and j1 > new_range[1]:
            # We've left the range of the current chunk to consider in the
            # new diff. Move on to the next one.
            new_range_i += 1

            if new_range_i < len(new_ranges):
                new_range = new_ranges[new_range_i]
            else:
                new_range = None

        # See if the chunk we're looking at is in the range of the chunk in
        # one of the uploaded diffs. If so, allow it through.
        orig_starts_valid = _is_range_valid(orig_range, tag, i1, i2)
        new_starts_valid = _is_range_valid(new_range, tag, j1, j2)

        if tag in ('equal', 'replace'):
            valid_chunk = orig_starts_valid or new_starts_valid
        elif tag == 'delete':
            valid_chunk = orig_starts_valid
        elif tag == 'insert':
            valid_chunk = new_starts_valid

        if valid_chunk:
            # This chunk is valid. It may only be a portion of the real
            # chunk, though. We'll need to split it up into a known valid
            # segment first, and yield that.
            if orig_range:
                cap_i2 = orig_range[1] + 1
            else:
                cap_i2 = i2

            if new_range:
                cap_j2 = new_range[1] + 1
            else:
                cap_j2 = j2

            if orig_starts_valid:
                valid_i2 = min(i2, cap_i2)
            else:
                valid_i2 = i2

            if new_starts_valid:
                valid_j2 = min(j2, cap_j2)
            else:
                valid_j2 = j2

            if tag in ('equal', 'replace'):
                # We need to take care to not let the replace lines have
                # differing ranges for the orig and modified files. We want the
                # replace to take up the full bounds of the two sides, but
                # capped to the valid chunk range.
                #
                # For this, we need to pick a consistent value for the length
                # of the range. We know at least one side will be within
                # bounds, since we have a valid chunk and at least one is
                # capped to be <= the end of the range.
                #
                # If one side is out of bounds of the range, the other range
                # will win. If both are in bounds, the largest wins.
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

                # Set each valid range to be the same length.
                valid_i2 = i1 + max_cap
                valid_j2 = j1 + max_cap

                # Update the caps, so that we'll process whatever we've
                # chopped off.
                cap_i2 = valid_i2
                cap_j2 = valid_j2

            yield tag, i1, valid_i2, j1, valid_j2

            if valid_i2 == i2 and valid_j2 == j2:
                continue

            # There were more parts of this range remaining. We know they're
            # all invalid, so let's update i1 and j1 to point to the start
            # of those invalid ranges, and mark them.
            if orig_range is not None and i2 + 1 > cap_i2:
                i1 = cap_i2

            if new_range is not None and j2 + 1 > cap_j2:
                j1 = cap_j2

            valid_chunk = False

        if not valid_chunk:
            # Turn this into an "filtered-equal" chunk. The left-hand and
            # right-hand side of the diffs will look different, which may be
            # noticeable, but it will still help the user pay attention to
            # what's actually changed that they care about.
            #
            # These will get turned back into "equal" chunks in the
            # post-processing step.
            yield 'filtered-equal', i1, i2, j1, j2


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
