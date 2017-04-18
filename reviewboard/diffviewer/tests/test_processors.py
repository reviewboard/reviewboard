from __future__ import unicode_literals

from reviewboard.diffviewer.processors import (filter_interdiff_opcodes,
                                               post_process_filtered_equals)
from reviewboard.testing import TestCase


class FilterInterdiffOpcodesTests(TestCase):
    """Unit tests for filter_interdiff_opcodes."""

    def test_filter_interdiff_opcodes(self):
        """Testing filter_interdiff_opcodes"""
        opcodes = [
            ('insert', 0, 0, 0, 1),
            ('equal', 0, 5, 1, 6),
            ('delete', 5, 10, 6, 6),
            ('equal', 10, 25, 6, 21),
            ('replace', 25, 26, 21, 22),
            ('equal', 26, 40, 22, 36),
            ('insert', 40, 40, 36, 46),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = self._build_dummy_diff_data(22, 10, 22, 10)
        new_diff = b''.join([
            self._build_dummy_diff_data(2, 14, 2, 9),
            self._build_dummy_diff_data(22, 10, 22, 10),
        ])

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('filtered-equal', 0, 0, 0, 1),
            ('filtered-equal', 0, 5, 1, 6),
            ('filtered-equal', 5, 10, 6, 6),
            ('equal', 10, 25, 6, 21),
            ('replace', 25, 26, 21, 22),
            ('equal', 26, 28, 22, 24),
            ('filtered-equal', 28, 40, 24, 36),
            ('filtered-equal', 40, 40, 36, 46),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def test_filter_interdiff_opcodes_replace_after_valid_ranges(self):
        """Testing filter_interdiff_opcodes with replace after valid range"""
        # While developing the fix for replace lines in
        # https://reviews.reviewboard.org/r/6030/, an iteration of the fix
        # broke replace lines when one side exceeded its last range found in
        # the diff.
        opcodes = [
            ('replace', 12, 13, 5, 6),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = self._build_dummy_diff_data(2, 10, 2, 10)
        new_diff = self._build_dummy_diff_data(2, 10, 2, 10)

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('replace', 12, 13, 5, 6),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def test_filter_interdiff_opcodes_1_line(self):
        """Testing filter_interdiff_opcodes with a 1 line file"""
        opcodes = [
            ('replace', 0, 1, 0, 1),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = self._build_dummy_diff_data(1, 1, 1, 2,
                                                pre_lines_of_context=0)
        new_diff = self._build_dummy_diff_data(1, 1, 1, 2,
                                               pre_lines_of_context=0)

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('replace', 0, 1, 0, 1),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def test_filter_interdiff_opcodes_early_change(self):
        """Testing filter_interdiff_opcodes with a change early in the file"""
        opcodes = [
            ('replace', 2, 3, 2, 3),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = self._build_dummy_diff_data(1, 5, 1, 6,
                                                pre_lines_of_context=2)
        new_diff = self._build_dummy_diff_data(1, 5, 1, 6,
                                               pre_lines_of_context=2)

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('replace', 2, 3, 2, 3),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def test_filter_interdiff_opcodes_with_inserts_right(self):
        """Testing filter_interdiff_opcodes with inserts on the right"""
        # These opcodes were taken from the r1-r2 interdiff at
        # http://reviews.reviewboard.org/r/4221/
        opcodes = [
            ('equal', 0, 141, 0, 141),
            ('replace', 141, 142, 141, 142),
            ('insert', 142, 142, 142, 144),
            ('equal', 142, 165, 144, 167),
            ('replace', 165, 166, 167, 168),
            ('insert', 166, 166, 168, 170),
            ('equal', 166, 190, 170, 194),
            ('insert', 190, 190, 194, 197),
            ('equal', 190, 232, 197, 239),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = self._build_dummy_diff_data(0, 3, 1, 235)
        new_diff = self._build_dummy_diff_data(0, 3, 1, 242)

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('filtered-equal', 0, 141, 0, 141),
            ('replace', 141, 142, 141, 142),
            ('insert', 142, 142, 142, 144),
            ('equal', 142, 165, 144, 167),
            ('replace', 165, 166, 167, 168),
            ('insert', 166, 166, 168, 170),
            ('equal', 166, 190, 170, 194),
            ('insert', 190, 190, 194, 197),
            ('equal', 190, 232, 197, 239),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def test_filter_interdiff_opcodes_with_many_ignorable_ranges(self):
        """Testing filter_interdiff_opcodes with many ignorable ranges"""
        # These opcodes were taken from the r1-r2 interdiff at
        # http://reviews.reviewboard.org/r/4257/
        opcodes = [
            ('equal', 0, 631, 0, 631),
            ('replace', 631, 632, 631, 632),
            ('insert', 632, 632, 632, 633),
            ('equal', 632, 882, 633, 883),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = b''.join([
            self._build_dummy_diff_data(post_lines_of_context=0, *values)
            for values in (
                (413, 6, 413, 8),
                (422, 9, 424, 13),
                (433, 6, 439, 8),
                (442, 6, 450, 9),
                (595, 6, 605, 205),
                (636, 6, 845, 36),
            )
        ])
        new_diff = b''.join([
            self._build_dummy_diff_data(post_lines_of_context=0, *values)
            for values in (
                (413, 6, 413, 8),
                (422, 9, 424, 13),
                (433, 6, 439, 8),
                (442, 6, 450, 8),
                (595, 6, 605, 206),
                (636, 6, 846, 36),
            )
        ])

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('filtered-equal', 0, 631, 0, 631),
            ('replace', 631, 632, 631, 632),
            ('insert', 632, 632, 632, 633),
            ('equal', 632, 809, 633, 810),
            ('filtered-equal', 809, 882, 810, 883),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def test_filter_interdiff_opcodes_with_replace_overflowing_range(self):
        """Testing filter_interdiff_opcodes with replace overflowing range"""
        # In the case where there's a replace chunk with i2 or j2 larger than
        # the end position of the current range, the chunk would get chopped,
        # and the two replace ranges could be unequal. This broke an assertion
        # check when generating opcode metadata, and would result in a
        # corrupt-looking diff.
        #
        # This is bug #3440
        #
        # Before the fix, the below opcodes and diff ranges would result
        # in the replace turning into (2, 6, 2, 15), instead of staying at
        # (2, 15, 2, 15).
        #
        # This only really tends to happen in early ranges (since the range
        # numbers are small), but could also happen further into the diff
        # if a replace range is huge on one side.
        opcodes = [
            ('equal', 0, 2, 0, 2),
            ('replace', 2, 100, 2, 100),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = b''.join([
            self._build_dummy_diff_data(1, 4, 1, 3, pre_lines_of_context=0),
            self._build_dummy_diff_data(8, 21, 9, 22),
        ])
        new_diff = self._build_dummy_diff_data(1, 13, 1, 17,
                                               pre_lines_of_context=0)

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('equal', 0, 2, 0, 2),
            ('replace', 2, 15, 2, 15),
            ('filtered-equal', 15, 100, 15, 100),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def test_filter_interdiff_opcodes_with_trailing_context(self):
        """Testing filter_interdiff_opcodes with trailing context"""
        opcodes = [
            ('replace', 0, 13, 0, 13),
            ('insert', 13, 13, 13, 14),
            ('replace', 13, 20, 14, 21),
        ]
        self._sanity_check_opcodes(opcodes)

        orig_diff = self._build_dummy_diff_data(10, 5, 10, 6)
        new_diff = self._build_dummy_diff_data(10, 6, 10, 7,
                                               pre_lines_of_context=4)

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('filtered-equal', 0, 13, 0, 13),
            ('insert', 13, 13, 13, 14),
            ('filtered-equal', 13, 20, 14, 21),
        ])
        self._sanity_check_opcodes(new_opcodes)

    def _sanity_check_opcodes(self, opcodes):
        prev_i2 = None
        prev_j2 = None

        for index, opcode in enumerate(opcodes):
            tag, i1, i2, j1, j2 = opcode

            if tag in ('equal', 'replace'):
                i_range = i2 - i1
                j_range = j2 - j1

                self.assertEqual(
                    (i2 - i1), (j2 - j1),
                    'Ranges are not equal for opcode index %s: %r. Got '
                    'i_range=%s, j_range=%s'
                    % (index, opcode, i_range, j_range))
            elif tag == 'insert':
                self.assertEqual(
                    i1, i2,
                    'i range should not change for opcode index %s: %r. Got '
                    'i1=%s, i2=%s'
                    % (index, opcode, i1, i2))
            elif tag == 'delete':
                self.assertEqual(
                    j1, j2,
                    'j range should not change for opcode index %s: %r. Got '
                    'j1=%s, j2=%s'
                    % (index, opcode, j1, j2))

            if prev_i2 is not None and prev_j2 is not None:
                self.assertEqual(i1, prev_i2)
                self.assertEqual(j1, prev_j2)

            prev_i2 = i2
            prev_j2 = j2

    def _build_dummy_diff_data(self, orig_start, orig_len, new_start, new_len,
                               pre_lines_of_context=3,
                               post_lines_of_context=None):
        """Build diff data that can be used for interdiff tests.

        This will create a diff for one hunk in a file covering the provided
        ranges. The generated diff will have context, inserts, and deletes that
        add up to the ranges.

        Args:
            orig_start (int):
                The 1-based index for the original range (as in
                ``@@ -start,len ...``).

            orig_len (int):
                The length of the original range (as in ``@@ -start,len ...``),
                factoring in context lines (equals) and deletes.

            new_start (int):
                The 1-based index for the new range (as in
                ``... +start,len @@``).

            orig_len (int):
                The length of the original range (as in ``... +start,len @@``),
                factoring in context lines (equals) and inserts.

            pre_lines_of_context (int, optional):
                The number of lines of context (equals) before any changes.
                This defaults to 3. To represent a change within the first
                three lines of a file, you will need to change this.

            post_lines_of_context (int, optional):
                The number of lines of context (equals) after any changes.
                The default is calculated based on ``pre_lines_of_context`` and
                the range lengths.

        Returns:
            bytes:
            The resulting diff data.
        """
        if post_lines_of_context is None:
            # Try to calculate a suitable number of lines of context after
            # the changes. We want upwards of 3 lines, no fewer than 0. We'll
            # see how much room we have left by taking the smaller of the two
            # ranges and seeing how many lines are left after factoring in
            # the preceding lines of context.
            post_lines_of_context = \
                max(min(min(orig_len, new_len) - pre_lines_of_context, 3), 0)

        delete_line_count = (orig_len - pre_lines_of_context -
                             post_lines_of_context)
        insert_line_count = (new_len - pre_lines_of_context -
                             post_lines_of_context)

        return b''.join([
            b'@@ -%s,%s +%s,%s @@\n' % (orig_start, orig_len, new_start,
                                        new_len),
            b' #\n' * pre_lines_of_context,
            b'-# deleted\n' * delete_line_count,
            b'+# inserted\n' * insert_line_count,
            b' #\n' * post_lines_of_context,
        ])


class PostProcessFilteredEqualsTests(TestCase):
    """Unit tests for post_process_filtered_equals."""

    def test_post_process_filtered_equals(self):
        """Testing post_process_filtered_equals"""
        opcodes = [
            ('equal', 0, 10, 0, 10, {}),
            ('insert', 10, 20, 0, 10, {}),
            ('equal', 20, 30, 10, 20, {}),
            ('equal', 30, 40, 20, 30, {}),
            ('filtered-equal', 40, 50, 30, 40, {}),
        ]

        new_opcodes = list(post_process_filtered_equals(opcodes))

        self.assertEqual(
            new_opcodes,
            [
                ('equal', 0, 10, 0, 10, {}),
                ('insert', 10, 20, 0, 10, {}),
                ('equal', 20, 50, 10, 40, {}),
            ])

    def test_post_process_filtered_equals_with_indentation(self):
        """Testing post_process_filtered_equals with indentation changes"""
        opcodes = [
            ('equal', 0, 10, 0, 10, {}),
            ('insert', 10, 20, 0, 10, {}),
            ('equal', 20, 30, 10, 20, {
                'indentation_changes': {
                    '21-11': (True, 4),
                }
            }),
            ('equal', 30, 40, 20, 30, {}),
            ('filtered-equal', 30, 50, 20, 40, {}),
        ]

        new_opcodes = list(post_process_filtered_equals(opcodes))

        self.assertEqual(
            new_opcodes,
            [
                ('equal', 0, 10, 0, 10, {}),
                ('insert', 10, 20, 0, 10, {}),
                ('equal', 20, 30, 10, 20, {
                    'indentation_changes': {
                        '21-11': (True, 4),
                    }
                }),
                ('equal', 30, 50, 20, 40, {}),
            ])

    def test_post_process_filtered_equals_with_adjacent_indentation(self):
        """Testing post_process_filtered_equals with
        adjacent indentation changes
        """
        opcodes = [
            ('equal', 0, 10, 0, 10, {}),
            ('insert', 10, 20, 0, 10, {}),
            ('equal', 20, 30, 10, 20, {
                'indentation_changes': {
                    '21-11': (True, 4),
                }
            }),
            ('equal', 30, 40, 20, 30, {
                'indentation_changes': {
                    '31-21': (False, 8),
                }
            }),
            ('filtered-equal', 40, 50, 30, 40, {}),
        ]

        new_opcodes = list(post_process_filtered_equals(opcodes))

        self.assertEqual(
            new_opcodes,
            [
                ('equal', 0, 10, 0, 10, {}),
                ('insert', 10, 20, 0, 10, {}),
                ('equal', 20, 30, 10, 20, {
                    'indentation_changes': {
                        '21-11': (True, 4),
                    }
                }),
                ('equal', 30, 40, 20, 30, {
                    'indentation_changes': {
                        '31-21': (False, 8),
                    }
                }),
                ('equal', 40, 50, 30, 40, {}),
            ])
