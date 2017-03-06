from __future__ import unicode_literals

import os
import re

from django.utils import six
from django.utils.six.moves import range

from reviewboard.diffviewer.processors import (filter_interdiff_opcodes,
                                               post_process_filtered_equals)


class MoveRange(object):
    """Stores information on a move range.

    This will store the start and end of the range, and all groups that
    are a part of it.
    """
    def __init__(self, start, end, groups=[]):
        self.start = start
        self.end = end
        self.groups = groups

    @property
    def last_group(self):
        return self.groups[-1]

    def add_group(self, group, group_index):
        if self.groups[-1] != group:
            self.groups.append((group, group_index))

    def __repr__(self):
        return '<MoveRange(%d, %d, %r)>' % (self.start, self.end, self.groups)


class DiffOpcodeGenerator(object):
    ALPHANUM_RE = re.compile(r'\w')
    WHITESPACE_RE = re.compile(r'\s')

    MOVE_PREFERRED_MIN_LINES = 2
    MOVE_MIN_LINE_LENGTH = 20

    TAB_SIZE = 8

    def __init__(self, differ, filediff=None, interfilediff=None):
        self.differ = differ
        self.filediff = filediff
        self.interfilediff = interfilediff

    def __iter__(self):
        """Returns opcodes from the differ with extra metadata.

        This is a wrapper around a differ's get_opcodes function, which returns
        extra metadata along with each range. That metadata includes
        information on moved blocks of code and whitespace-only lines.

        This returns a list of opcodes as tuples in the form of
        (tag, i1, i2, j1, j2, meta).
        """
        self.groups = []
        self.removes = {}
        self.inserts = []

        # Run the opcodes through the chain.
        opcodes = self.differ.get_opcodes()
        opcodes = self._apply_processors(opcodes)
        opcodes = self._generate_opcode_meta(opcodes)
        opcodes = self._apply_meta_processors(opcodes)

        self._group_opcodes(opcodes)
        self._compute_moves()

        for opcodes in self.groups:
            yield opcodes

    def _apply_processors(self, opcodes):
        if self.interfilediff:
            # Filter out any lines unrelated to these changes from the
            # interdiff. This will get rid of any merge information.
            opcodes = filter_interdiff_opcodes(opcodes, self.filediff.diff,
                                               self.interfilediff.diff)

        for opcode in opcodes:
            yield opcode

    def _generate_opcode_meta(self, opcodes):
        for tag, i1, i2, j1, j2 in opcodes:
            meta = {
                # True if this chunk is only whitespace.
                'whitespace_chunk': False,

                # List of tuples (i, j), with whitespace changes.
                'whitespace_lines': [],
            }

            if tag == 'replace':
                # replace groups are good for whitespace only changes.
                assert (i2 - i1) == (j2 - j1)

                for i, j in zip(range(i1, i2), range(j1, j2)):
                    if (self.WHITESPACE_RE.sub('', self.differ.a[i]) ==
                            self.WHITESPACE_RE.sub('', self.differ.b[j])):
                        # Both original lines are equal when removing all
                        # whitespace, so include their original line number in
                        # the meta dict.
                        meta['whitespace_lines'].append((i + 1, j + 1))

                # If all lines are considered to have only whitespace change,
                # the whole chunk is considered a whitespace-only chunk.
                if len(meta['whitespace_lines']) == (i2 - i1):
                    meta['whitespace_chunk'] = True
            elif tag == 'equal':
                for group in self._compute_chunk_indentation(i1, i2, j1, j2):
                    ii1, ii2, ij1, ij2, indentation_changes = group

                    if indentation_changes:
                        new_meta = dict({
                            'indentation_changes': indentation_changes,
                        }, **meta)
                    else:
                        new_meta = meta

                    yield tag, ii1, ii2, ij1, ij2, new_meta

                continue

            yield tag, i1, i2, j1, j2, meta

    def _apply_meta_processors(self, opcodes):
        if self.interfilediff:
            # When filtering out opcodes, we may have converted chunks into
            # "filtered-equal" chunks. This allowed us to skip any additional
            # processing, particularly the indentation highlighting. It's
            # now time to turn those back into "equal" chunks.
            opcodes = post_process_filtered_equals(opcodes)

        for opcode in opcodes:
            yield opcode

    def _group_opcodes(self, opcodes):
        for group_index, group in enumerate(opcodes):
            self.groups.append(group)

            # Store delete/insert ranges for later lookup. We will be building
            # keys that in most cases will be unique for the particular block
            # of text being inserted/deleted. There is a chance of collision,
            # so we store a list of matching groups under that key.
            #
            # Later, we will loop through the keys and attempt to find insert
            # keys/groups that match remove keys/groups.
            tag = group[0]

            if tag in ('delete', 'replace'):
                i1 = group[1]
                i2 = group[2]

                for i in range(i1, i2):
                    line = self.differ.a[i].strip()

                    if line:
                        self.removes.setdefault(line, []).append(
                            (i, group, group_index))

            if tag in ('insert', 'replace'):
                self.inserts.append(group)

    def _compute_chunk_indentation(self, i1, i2, j1, j2):
        # We'll be going through all the opcodes in this equals chunk and
        # grouping with adjacent opcodes based on whether they have
        # indentation changes or not. This allows us to keep the lines with
        # indentation changes from being collapsed in the diff viewer.
        indentation_changes = {}
        prev_has_indent = False
        prev_start_i = i1
        prev_start_j = j1

        for i, j in zip(range(i1, i2), range(j1, j2)):
            old_line = self.differ.a[i]
            new_line = self.differ.b[j]
            new_indentation_changes = {}

            indent_info = self._compute_line_indentation(old_line, new_line)
            has_indent = indent_info is not None

            if has_indent:
                key = '%d-%d' % (i + 1, j + 1)
                new_indentation_changes[key] = indent_info

            if has_indent != prev_has_indent:
                if prev_start_i != i or prev_start_j != j:
                    # Yield the previous group.
                    yield prev_start_i, i, prev_start_j, j, indentation_changes

                # We have a new group. Set it up, starting with the current
                # calculated state.
                prev_start_i = i
                prev_start_j = j
                prev_has_indent = has_indent
                indentation_changes = new_indentation_changes
            elif has_indent:
                indentation_changes.update(new_indentation_changes)

        # Yield the last group, if we haven't already yielded it.
        if prev_start_i != i2 or prev_start_j != j2:
            yield prev_start_i, i2, prev_start_j, j2, indentation_changes

    def _compute_line_indentation(self, old_line, new_line):
        if old_line == new_line:
            return None

        old_line_stripped = old_line.lstrip()
        new_line_stripped = new_line.lstrip()

        # These are fake-equal. They really have some indentation changes.
        # We want to mark those up.
        #
        # Our goal for this function from here on out is to figure out whether
        # the new line has increased or decreased its indentation, and then
        # to determine how much that has increased or decreased by.
        #
        # Since we may be dealing with the additional or removal of tabs,
        # we have some challenges here. We need to expand those tabs in
        # order to determine if the new line is indented further or not,
        # and then we need to figure out how much of the leading whitespace
        # on either side represents new indentation levels.
        #
        # We do this by chopping off all leading whitespace and expanding
        # any tabs, and then figuring out the total line lengths. That gives
        # us a basis for comparison to determine whether we've indented
        # or unindented.
        #
        # We can then later figure out exactly which indentation characters
        # were added or removed, and then store that information.
        old_line_indent_len = len(old_line) - len(old_line_stripped)
        new_line_indent_len = len(new_line) - len(new_line_stripped)
        old_line_indent = old_line[:old_line_indent_len]
        new_line_indent = new_line[:new_line_indent_len]

        norm_old_line_indent = old_line_indent.expandtabs(self.TAB_SIZE)
        norm_new_line_indent = new_line_indent.expandtabs(self.TAB_SIZE)
        norm_old_line_indent_len = len(norm_old_line_indent)
        norm_new_line_indent_len = len(norm_new_line_indent)
        norm_old_line_len = (norm_old_line_indent_len +
                             len(old_line_stripped))
        norm_new_line_len = (norm_new_line_indent_len +
                             len(new_line_stripped))
        line_len_diff = norm_new_line_len - norm_old_line_len

        if line_len_diff == 0:
            return None

        # We know that a spacing change did take place. We need to figure
        # out now how many characters of indentation were actually
        # added or removed.
        is_indent = (line_len_diff > 0)

        if is_indent:
            raw_indent_len = new_line_indent_len
        else:
            raw_indent_len = old_line_indent_len

        # Figure out how many characters of indentation were in common
        # at the end of the strings. We'll want to exclude these
        # characters when showing indentation changes.
        #
        # This is the area after any new indentation. If the indentation
        # style changed (such as going from tabs to spaces), then nothing
        # will be in common.
        #
        # We figure out the common trailing indentation by reversing both
        # strings and then finding the common prefix. We only care about
        # the length, so we can throw the string away.
        #
        # It may seem odd that we're using os.path.commonprefix, but this
        # isn't really limited to paths. Certainly not in our case. It's
        # worth not re-implementing that logic.
        raw_indent_len -= len(os.path.commonprefix([
            old_line_indent[::-1],
            new_line_indent[::-1],
        ]))

        return (is_indent,
                raw_indent_len,
                abs(norm_old_line_indent_len - norm_new_line_indent_len))

    def _compute_moves(self):
        # We now need to figure out all the moved locations.
        #
        # At this point, we know all the inserted groups, and all the
        # individually deleted lines. We'll be going through and finding
        # consecutive groups of matching inserts/deletes that represent a
        # move block.
        #
        # The algorithm will be documented as we go in the code.
        #
        # We start by looping through all the inserted groups.
        for insert in self.inserts:
            self._compute_move_for_insert(*insert)

    def _compute_move_for_insert(self, itag, ii1, ii2, ij1, ij2, imeta):
        # Store some state on the range we'll be working with inside this
        # insert group.
        #
        # i_move_cur is the current location inside the insert group
        # (from ij1 through ij2).
        #
        # i_move_range is the current range of consecutive lines that
        # we'll use for a move. Each line in this range has a
        # corresponding consecutive delete line.
        #
        # r_move_ranges represents deleted move ranges. The key is a
        # string in the form of "{i1}-{i2}-{j1}-{j2}", with those
        # positions taken from the remove group for the line. The value
        # is an instance of MoveRange. The values in MoveRange are used to
        # quickly locate deleted lines we've found that match the inserted
        # lines, so we can assemble ranges later.
        i_move_cur = ij1
        i_move_range = MoveRange(i_move_cur, i_move_cur)
        r_move_ranges = {}  # key -> (start, end, group)
        r_move_indexes_used = set()
        move_key = None

        is_replace = (itag == 'replace')

        # Loop through every location from ij1 through ij2 - 1 until we've
        # reached the end.
        while i_move_cur < ij2:
            try:
                iline = self.differ.b[i_move_cur].strip()
            except IndexError:
                iline = None

            updated_range = False

            if iline and iline in self.removes:
                # The inserted line at this location has a corresponding
                # removed line.
                #
                # If there's already some information on removed line ranges
                # for this particular move block we're processing then we'll
                # update the range.
                #
                # The way we do that is to find each removed line that matches
                # this inserted line, and for each of those find out if there's
                # an existing move range that the found removed line
                # immediately follows. If there is, we update the existing
                # range.
                #
                # If there isn't any move information for this line, we'll
                # simply add it to the move ranges.
                for ri, rgroup, rgroup_index in self.removes[iline]:
                    # Ignore any lines that have already been processed as
                    # part of a move, so we don't end up with incorrect blocks
                    # of lines being matched.
                    if ri in r_move_indexes_used:
                        continue

                    r_move_range = r_move_ranges.get(move_key)

                    if not r_move_range or ri != r_move_range.end + 1:
                        # We either didn't have a previous range, or this
                        # group didn't immediately follow it, so we need
                        # to start a new one.
                        move_key = '%s-%s-%s-%s' % rgroup[1:5]
                        r_move_range = r_move_ranges.get(move_key)

                    if r_move_range:
                        # If the remove information for the line is next in
                        # the sequence for this calculated move range...
                        if ri == r_move_range.end + 1:
                            # This is part of the current range, so update
                            # the end of the range to include it.
                            r_move_range.end = ri
                            r_move_range.add_group(rgroup, rgroup_index)
                            updated_range = True
                    else:
                        # Check that this isn't a replace line that's just
                        # "replacing" itself (which would happen if it's just
                        # changing whitespace).
                        if not is_replace or i_move_cur - ij1 != ri - ii1:
                            # We don't have any move ranges yet, or we're done
                            # with the existing range, so it's time to build one
                            # based on any removed lines we find that match the
                            # inserted line.
                            r_move_ranges[move_key] = \
                                MoveRange(ri, ri, [(rgroup, rgroup_index)])
                            updated_range = True

                if not updated_range and r_move_ranges:
                    # We didn't find a move range that this line is a part
                    # of, but we do have some existing move ranges stored.
                    #
                    # Given that updated_range is set, we'll be processing
                    # the known move ranges below. We'll actually want to
                    # re-check this line afterward, so that we can start a
                    # new move range after we've finished processing the
                    # current ones.
                    #
                    # To do that, just i_move_cur back by one. That negates
                    # the increment below.
                    i_move_cur -= 1
                    move_key = None
            elif iline == '' and move_key:
                # This is a blank or whitespace-only line, which would not
                # be in the list of removed lines above. We also have been
                # working on a move range.
                #
                # At this point, the plan is to just attach this blank
                # line onto the end of the last range being operated on.
                #
                # This blank line will help tie together adjacent move
                # ranges. If it turns out to be a trailing line, it'll be
                # stripped later in _determine_move_range.
                r_move_range = r_move_ranges.get(move_key)

                if r_move_range:
                    new_end_i = r_move_range.end + 1

                    if (new_end_i < len(self.differ.a) and
                        self.differ.a[new_end_i].strip() == ''):
                        # There was a matching blank line on the other end
                        # of the range, so we should feel more confident about
                        # adding the blank line here.
                        r_move_range.end = new_end_i

                        # It's possible that this blank line is actually an
                        # "equal" line. Though technically it didn't move,
                        # we're trying to create a logical, seamless move
                        # range, so we need to try to find that group and
                        # add it to the list of groups in the range, if it'
                        # not already there.
                        last_group, last_group_index = r_move_range.last_group

                        if new_end_i >= last_group[2]:
                            # This is in the next group, which hasn't been
                            # added yet. So add it.
                            cur_group_index = r_move_range.last_group[1] + 1
                            r_move_range.add_group(
                                self.groups[cur_group_index],
                                cur_group_index)

                        updated_range = True

            i_move_cur += 1

            if not updated_range or i_move_cur == ij2:
                # We've reached the very end of the insert group. See if
                # we have anything that looks like a move.
                if r_move_ranges:
                    r_move_range = self._find_longest_move_range(r_move_ranges)

                    # If we have a move range, see if it's one we want to
                    # include or filter out. Some moves are not impressive
                    # enough to display. For example, a small portion of a
                    # comment, or whitespace-only changes.
                    r_move_range = self._determine_move_range(r_move_range)

                    if r_move_range:
                        # Rebuild the insert and remove ranges based on where
                        # we are now and which range we won.
                        #
                        # The new ranges will be actual lists of positions,
                        # rather than a beginning and end. These will be
                        # provided to the renderer.
                        #
                        # The ranges expected by the renderers are 1-based,
                        # whereas our calculations for this algorithm are
                        # 0-based, so we add 1 to the numbers.
                        #
                        # The upper boundaries passed to the range() function
                        # must actually be one higher than the value we want.
                        # So, for r_move_range, we actually increment by 2.  We
                        # only increment i_move_cur by one, because i_move_cur
                        # already factored in the + 1 by being at the end of
                        # the while loop.
                        i_range = range(i_move_range.start + 1,
                                        i_move_cur + 1)
                        r_range = range(r_move_range.start + 1,
                                        r_move_range.end + 2)

                        moved_to_ranges = dict(zip(r_range, i_range))

                        for group, group_index in r_move_range.groups:
                            rmeta = group[-1]
                            rmeta.setdefault('moved-to', {}).update(
                                moved_to_ranges)

                        imeta.setdefault('moved-from', {}).update(
                            dict(zip(i_range, r_range)))

                        # Record each of the positions in the removed range
                        # as used, so that they're not factored in again when
                        # determining possible ranges for future moves.
                        #
                        # We'll use the r_range above, but normalize back to
                        # 0-based indexes.
                        r_move_indexes_used.update(r - 1 for r in r_range)

                # Reset the state for the next range.
                move_key = None
                i_move_range = MoveRange(i_move_cur, i_move_cur)
                r_move_ranges = {}

    def _find_longest_move_range(self, r_move_ranges):
        # Go through every range of lines we've found and find the longest.
        #
        # The longest move range wins. If we find two ranges that are equal,
        # though, we'll ignore both. The idea is that if we have two identical
        # moves, then it's probably common enough code that we don't want to
        # show the move. An example might be some standard part of a comment
        # block, with no real changes in content.
        #
        # Note that with the current approach, finding duplicate moves doesn't
        # cause us to reset the winning range to the second-highest identical
        # match. We may want to do that down the road, but it means additional
        # state, and this is hopefully uncommon enough to not be a real
        # problem.
        r_move_range = None

        for iter_move_range in six.itervalues(r_move_ranges):
            if not r_move_range:
                r_move_range = iter_move_range
            else:
                len1 = r_move_range.end - r_move_range.start
                len2 = iter_move_range.end - iter_move_range.start

                if len1 < len2:
                    r_move_range = iter_move_range
                elif len1 == len2:
                    # If there are two that are the same, it may be common
                    # code that we don't want to see moves for. Comments,
                    # for example.
                    r_move_range = None

        return r_move_range

    def _determine_move_range(self, r_move_range):
        """Determines if a move range is valid and should be included.

        This performs some tests to try to eliminate trivial changes that
        shouldn't have moves associated.

        Specifically, a move range is valid if it has at least one line
        with alpha-numeric characters and is at least 4 characters long when
        stripped.

        If the move range is valid, any trailing whitespace-only lines will
        be stripped, ensuring it covers only a valid range of content.
        """
        if not r_move_range:
            return None

        end_i = r_move_range.end
        lines = self.differ.a[r_move_range.start:end_i + 1]
        new_end_i = None
        valid = False

        for i, line in enumerate(reversed(lines)):
            line = line.strip()

            if line:
                if len(line) >= 4 and self.ALPHANUM_RE.search(line):
                    valid = True

                if new_end_i is None or valid:
                    new_end_i = end_i - i

                if valid:
                    break

        # Accept this if there's more than one line or if the first
        # line is long enough, in order to filter out small bits of garbage.
        valid = (
            valid and
            (new_end_i - r_move_range.start + 1 >=
                 self.MOVE_PREFERRED_MIN_LINES or
             len(self.differ.a[r_move_range.start].strip()) >=
                 self.MOVE_MIN_LINE_LENGTH))

        if not valid:
            return None

        assert new_end_i is not None

        return MoveRange(r_move_range.start, new_end_i, r_move_range.groups)


_generator = DiffOpcodeGenerator


def get_diff_opcode_generator_class():
    """Returns the DiffOpcodeGenerator class used for generating opcodes."""
    return _generator


def set_diff_opcode_generator_class(renderer):
    """Sets the DiffOpcodeGenerator class used for generating opcodes."""
    assert renderer

    globals()['_generator'] = renderer


def get_diff_opcode_generator(*args, **kwargs):
    """Returns a DiffOpcodeGenerator instance used for generating opcodes."""
    return _generator(*args, **kwargs)
