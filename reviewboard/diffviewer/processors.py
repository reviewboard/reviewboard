from __future__ import unicode_literals

import re


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
        lines = diff.splitlines()
        process_changes = False
        ranges = []

        # Look through the chunks of the diff, trying to find the amount
        # of context shown at the beginning of each chunk. Though this
        # will usually be 3 lines, it may be fewer or more, depending
        # on file length and diff generation settings.
        for line in lines:
            if process_changes:
                if line.startswith(('-', '+')):
                    # We've found the first change in the chunk. We now
                    # know how many lines of context we have.
                    #
                    # We reduce the indexes by 1 because the chunk ranges
                    # in diffs start at 1, and we want a 0-based index.
                    start = chunk_start - 1 + lines_of_context
                    ranges.append((start, start + chunk_len))
                    process_changes = False
                    continue
                else:
                    lines_of_context += 1

            # This was not a change within a chunk, or we weren't processing,
            # so check to see if this is a chunk header instead.
            m = CHUNK_RANGE_RE.match(line)

            if m:
                # It is a chunk header. Reset the state for the next range,
                # and pull the line number and length from the header.
                chunk_start = int(m.group('new_start'))
                chunk_len = int(m.group('new_len') or '1')
                process_changes = True
                lines_of_context = 0

        return ranges

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
        valid_chunk = (
            (orig_range is not None and
             (tag == 'delete' or i1 != i2) and
             (i1 >= orig_range[0] and i2 <= orig_range[1])) or
            (new_range is not None and
             (tag == 'delete' or j1 != j2) and
             (j1 >= new_range[0] and j2 <= new_range[1]))
        )

        if not valid_chunk:
            # Turn this into an "filtered-equal" chunk. The left-hand and
            # right-hand side of the diffs will look different, which may be
            # noticeable, but it will still help the user pay attention to
            # what's actually changed that they care about.
            #
            # These will get turned back into "equal" chunks in the
            # post-processing step.
            tag = 'filtered-equal'

        yield tag, i1, i2, j1, j2


def merge_adjacent_chunks(opcodes):
    """Merges adjacent chunks of the same tag.

    This will take any chunks that have the same tag (such as two "equal"
    chunks) and merge them together.
    """
    cur_chunk = None

    for tag, i1, i2, j1, j2 in opcodes:
        if cur_chunk and cur_chunk[0] == tag:
            cur_chunk = (tag, cur_chunk[1], i2, cur_chunk[3], j2)
        else:
            if cur_chunk:
                yield cur_chunk

            cur_chunk = (tag, i1, i2, j1, j2)

    if cur_chunk:
        yield cur_chunk


def post_process_interdiff_chunks(opcodes):
    """Post-processes interdiff chunks.

    Any filtered-out "filtered-equal" chunks will get turned back into "equal"
    chunks.
    """
    for tag, i1, i2, j1, j2, meta in opcodes:
        if tag == 'filtered-equal':
            tag = 'equal'

        yield tag, i1, i2, j1, j2, meta
