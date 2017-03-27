from __future__ import unicode_literals

import os

import reviewboard.diffviewer.diffutils as diffutils
import reviewboard.diffviewer.parser as diffparser
from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.opcode_generator import get_diff_opcode_generator
from reviewboard.testing import TestCase


class DiffParserTest(TestCase):
    def test_form_feed(self):
        """Testing DiffParser.parse with a form feed in the file"""
        data = (
            b'--- README  123\n'
            b'+++ README  (new)\n'
            b'@@ -1,4 +1,6 @@\n'
            b' Line 1\n'
            b' Line 2\n'
            b'+\x0c\n'
            b'+Inserted line\n'
            b' Line 3\n'
            b' Line 4\n')
        files = diffparser.DiffParser(data).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 0)
        self.assertEqual(files[0].data, data)

    def test_patch(self):
        """Testing diffutils.patch"""
        old = (b'int\n'
               b'main()\n'
               b'{\n'
               b'\tprintf("foo\\n");\n'
               b'}\n')

        new = (b'#include <stdio.h>\n'
               b'\n'
               b'int\n'
               b'main()\n'
               b'{\n'
               b'\tprintf("foo bar\\n");\n'
               b'\treturn 0;\n'
               b'}\n')

        diff = (b'--- foo.c\t2007-01-24 02:11:31.000000000 -0800\n'
                b'+++ foo.c\t2007-01-24 02:14:42.000000000 -0800\n'
                b'@@ -1,5 +1,8 @@\n'
                b'+#include <stdio.h>\n'
                b'+\n'
                b' int\n'
                b' main()\n'
                b' {\n'
                b'-\tprintf("foo\\n");\n'
                b'+\tprintf("foo bar\\n");\n'
                b'+\treturn 0;\n'
                b' }\n')

        patched = diffutils.patch(diff, old, 'foo.c')
        self.assertEqual(patched, new)

        diff = (b'--- README\t2007-01-24 02:10:28.000000000 -0800\n'
                b'+++ README\t2007-01-24 02:11:01.000000000 -0800\n'
                b'@@ -1,9 +1,10 @@\n'
                b' Test data for a README file.\n'
                b' \n'
                b' There\'s a line here.\n'
                b'-\n'
                b' A line there.\n'
                b' \n'
                b' And here.\n')

        with self.assertRaises(Exception):
            diffutils.patch(diff, old, 'foo.c')

    def test_empty_patch(self):
        """Testing diffutils.patch with an empty diff"""
        old = 'This is a test'
        diff = ''
        patched = diffutils.patch(diff, old, 'test.c')
        self.assertEqual(patched, old)

    def test_patch_crlf_file_crlf_diff(self):
        """Testing diffutils.patch with a CRLF file and a CRLF diff"""
        old = (b'Test data for a README file.\r\n'
               b'\r\n'
               b'There\'s a line here.\r\n'
               b'\r\n'
               b'A line there.\r\n'
               b'\r\n'
               b'And here.\r\n')

        new = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        diff = (b'--- README\t2007-07-02 23:33:27.000000000 -0700\n'
                b'+++ README\t2007-07-02 23:32:59.000000000 -0700\n'
                b'@@ -1,7 +1,6 @@\n'
                b' Test data for a README file.\r\n'
                b' \r\n'
                b' There\'s a line here.\r\n'
                b'-\r\n'
                b' A line there.\r\n'
                b' \r\n'
                b' And here.\r\n')

        patched = diffutils.patch(diff, old, new)
        self.assertEqual(patched, new)

    def test_patch_cr_file_crlf_diff(self):
        """Testing diffutils.patch with a CR file and a CRLF diff"""
        old = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        new = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        diff = (b'--- README\t2007-07-02 23:33:27.000000000 -0700\n'
                b'+++ README\t2007-07-02 23:32:59.000000000 -0700\n'
                b'@@ -1,7 +1,6 @@\n'
                b' Test data for a README file.\r\n'
                b' \r\n'
                b' There\'s a line here.\r\n'
                b'-\r\n'
                b' A line there.\r\n'
                b' \r\n'
                b' And here.\r\n')

        patched = diffutils.patch(diff, old, new)
        self.assertEqual(patched, new)

    def test_patch_crlf_file_cr_diff(self):
        """Testing diffutils.patch with a CRLF file and a CR diff"""
        old = (b'Test data for a README file.\r\n'
               b'\r\n'
               b'There\'s a line here.\r\n'
               b'\r\n'
               b'A line there.\r\n'
               b'\r\n'
               b'And here.\r\n')

        new = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        diff = (b'--- README\t2007-07-02 23:33:27.000000000 -0700\n'
                b'+++ README\t2007-07-02 23:32:59.000000000 -0700\n'
                b'@@ -1,7 +1,6 @@\n'
                b' Test data for a README file.\n'
                b' \n'
                b' There\'s a line here.\n'
                b'-\n'
                b' A line there.\n'
                b' \n'
                b' And here.\n')

        patched = diffutils.patch(diff, old, new)
        self.assertEqual(patched, new)

    def test_patch_file_with_fake_no_newline(self):
        """Testing diffutils.patch with a file indicating no newline
        with a trailing \\r
        """
        old = (
            b'Test data for a README file.\n'
            b'\n'
            b'There\'s a line here.\n'
            b'\n'
            b'A line there.\n'
            b'\n'
            b'And a new line here!\n'
            b'\n'
            b'We must have several lines to reproduce this problem.\n'
            b'\n'
            b'So that there\'s enough hidden context.\n'
            b'\n'
            b'And dividers so we can reproduce the bug.\n'
            b'\n'
            b'Which will a --- line at the end of one file due to the '
            b'lack of newline,\n'
            b'causing a parse error.\n'
            b'\n'
            b'And here.\n'
            b'Yes, this is a good README file. Like most README files, '
            b'this doesn\'t tell youanything you really didn\'t already '
            b'know.\r')

        new = (
            b'Test data for a README file.\n'
            b'\n'
            b'There\'s a line here.\n'
            b'Here\'s a change!\n'
            b'\n'
            b'A line there.\n'
            b'\n'
            b'And a new line here!\n'
            b'\n'
            b'We must have several lines to reproduce this problem.\n'
            b'\n'
            b'So that there\'s enough hidden context.\n'
            b'\n'
            b'And dividers so we can reproduce the bug.\n'
            b'\n'
            b'Which will a --- line at the end of one file due to the '
            b'lack of newline,\n'
            b'causing a parse error.\n'
            b'\n'
            b'And here.\n'
            b'Yes, this is a good README file. Like most README files, '
            b'this doesn\'t tell youanything you really didn\'t '
            b'already know.\n')

        diff = (
            b'--- README\t2008-02-25 03:40:42.000000000 -0800\n'
            b'+++ README\t2008-02-25 03:40:55.000000000 -0800\n'
            b'@@ -1,6 +1,7 @@\n'
            b' Test data for a README file.\n'
            b' \n'
            b' There\'s a line here.\n'
            b'+Here\'s a change!\n'
            b' \n'
            b' A line there.\n'
            b' \n'
            b'@@ -16,4 +17,4 @@\n'
            b' causing a parse error.\n'
            b' \n'
            b' And here.\n'
            b'-Yes, this is a good README file. Like most README files, this '
            b'doesn\'t tell youanything you really didn\'t already know.\n'
            b'\\ No newline at end of file\n'
            b'+Yes, this is a good README file. Like most README files, this '
            b'doesn\'t tell youanything you really didn\'t already know.\n')

        files = diffparser.DiffParser(diff).parse()
        patched = diffutils.patch(files[0].data, old, 'README')
        self.assertEqual(diff, files[0].data)
        self.assertEqual(patched, new)

    def test_move_detection(self):
        """Testing diff viewer move detection"""
        # This has two blocks of code that would appear to be moves:
        # a function, and an empty comment block. Only the function should
        # be seen as a move, whereas the empty comment block is less useful
        # (since it's content-less) and shouldn't be seen as one.
        old = (
            b'/*\n'
            b' *\n'
            b' */\n'
            b'// ----\n'
            b'\n'
            b'\n'
            b'/*\n'
            b' * Says hello\n'
            b' */\n'
            b'void\n'
            b'say_hello()\n'
            b'{\n'
            b'\tprintf("Hello world!\\n");\n'
            b'}\n'
            b'\n'
            b'\n'
            b'int\n'
            b'dummy()\n'
            b'{\n'
            b'\tif (1) {\n'
            b'\t\t// whatever\n'
            b'\t}\n'
            b'}\n'
            b'\n'
            b'\n'
            b'void\n'
            b'say_goodbye()\n'
            b'{\n'
            b'\tprintf("Goodbye!\\n");\n'
            b'}\n')

        new = (
            b'// ----\n'
            b'\n'
            b'\n'
            b'int\n'
            b'dummy()\n'
            b'{\n'
            b'\tif (1) {\n'
            b'\t\t// whatever\n'
            b'\t}\n'
            b'}\n'
            b'\n'
            b'\n'
            b'/*\n'
            b' * Says goodbye\n'
            b' */\n'
            b'void\n'
            b'say_goodbye()\n'
            b'{\n'
            b'\tprintf("Goodbye!\\n");\n'
            b'}\n'
            b'\n'
            b'\n'
            b'void\n'
            b'say_hello()\n'
            b'{\n'
            b'\tprintf("Hello world!\\n");\n'
            b'}\n'
            b'\n'
            b'\n'
            b'/*\n'
            b' *\n'
            b' */\n')

        self._test_move_detection(
            old.splitlines(),
            new.splitlines(),
            [
                {
                    23: 10,
                    24: 11,
                    25: 12,
                    26: 13,
                }
            ],
            [
                {
                    10: 23,
                    11: 24,
                    12: 25,
                    13: 26,
                }
            ])

    def test_move_detection_with_replace_lines(self):
        """Testing diff viewer move detection with replace lines"""
        self._test_move_detection(
            [
                'this is line 1, and it is sufficiently long',
                '-------------------------------------------',
                '-------------------------------------------',
                'this is line 2, and it is sufficiently long',
            ],
            [
                'this is line 2, and it is sufficiently long',
                '-------------------------------------------',
                '-------------------------------------------',
                'this is line 1, and it is sufficiently long',
            ],
            [
                {1: 4},
                {4: 1},
            ],
            [
                {1: 4},
                {4: 1},
            ]
        )

    def test_move_detection_with_whitespace_replace_lines(self):
        """Testing diff viewer move detection with whitespace-only
        changes on replace lines
        """
        self._test_move_detection(
            [
                'this is line 1, and it is sufficiently long',
                '-------------------------------------------',
                '-------------------------------------------',
                'this is line 2, and it is sufficiently long  ',
            ],
            [
                '  this is line 1, and it is sufficiently long',
                '-------------------------------------------',
                '-------------------------------------------',
                'this is line 2, and it is sufficiently long',
            ],
            [],
            []
        )

    def test_move_detection_with_last_line_in_range(self):
        """Testing diff viewer move detection with last line in a range"""
        # The move detection rewrite in 2.0 introduced an off-by-one where
        # the last line in a chunk wasn't being processed as a move unless
        # the line after the chunk had content. That line should never have
        # been processed either.
        self._test_move_detection(
            [
                'this line will be replaced',
                '',
                'foo bar blah blah',
                'this is line 1, and it is sufficiently long',
                '',
            ],
            [
                'this is line 1, and it is sufficiently long',
                '',
                'foo bar blah blah',
                '',
            ],
            [
                {1: 4},
            ],
            [
                {4: 1},
            ]
        )

    def test_move_detection_with_adjacent_regions(self):
        """Testing diff viewer move detection with adjacent regions"""
        self._test_move_detection(
            [
                '1. Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
                '2. Phasellus et lectus vulputate, dictum mi id, auctor ante.',
                '3. Nulla accumsan tellus ut felis ultrices euismod.',
                '4. Donec quis augue sed arcu tristique pellentesque.',
                '5. Fusce rutrum diam vel viverra sagittis.',
                '6. Nam tincidunt sapien vitae lorem vestibulum tempor.',
                '7. Donec fermentum tortor ut egestas convallis.',
            ],
            [
                '6. Nam tincidunt sapien vitae lorem vestibulum tempor.',
                '7. Donec fermentum tortor ut egestas convallis.',
                '4. Donec quis augue sed arcu tristique pellentesque.',
                '5. Fusce rutrum diam vel viverra sagittis.',
                '1. Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
                '2. Phasellus et lectus vulputate, dictum mi id, auctor ante.',
                '3. Nulla accumsan tellus ut felis ultrices euismod.',
            ],
            [
                {
                    1: 6,
                    2: 7,
                    3: 4,
                    4: 5,
                }
            ],
            [
                {
                    4: 3,
                    5: 4,
                    6: 1,
                    7: 2,
                }
            ],
        )

    def test_move_detection_spanning_chunks(self):
        """Testing diff viewer move detection spanning left-hand-side chunks"""
        # This is testing an insert move range (the first 4 lines on the
        # second list of lines) that spans 3 chunks (1 replace line, 1 equal
        # blank line, and 2 delete lines).
        self._test_move_detection(
            [
                'Unchanged line 1',
                'Unchanged line 2',
                'Unchanged line 3',
                'Unchanged line 4',
                '====',
                'this is line 1, and it is sufficiently long',
                '',
                'this is line 2, and it is sufficiently long',
                'this is line 3, and it is sufficiently long',
                '',
            ],
            [
                'this is line 1, and it is sufficiently long',
                '',
                'this is line 2, and it is sufficiently long',
                'this is line 3, and it is sufficiently long',
                'Unchanged line 1',
                'Unchanged line 2',
                'Unchanged line 3',
                'Unchanged line 4',
                '====',
                'this is line X, and it is sufficiently long',
                '',
                '',
            ],
            [
                {
                    1: 6,
                    2: 7,
                    3: 8,
                    4: 9,
                },
            ],
            [
                # The entire move range is stored for every chunk, hence
                # the repeats.
                {
                    6: 1,
                    7: 2,
                    8: 3,
                    9: 4,
                },
                {
                    6: 1,
                    7: 2,
                    8: 3,
                    9: 4,
                },
                {
                    6: 1,
                    7: 2,
                    8: 3,
                    9: 4,
                },
            ]
        )

    def test_move_detection_single_line_thresholds(self):
        """Testing diff viewer move detection with a single line and
        line length threshold
        """
        self._test_move_detection(
            [
                '0123456789012345678',
                '----',
                '----',
                'abcdefghijklmnopqrst',
            ],
            [
                'abcdefghijklmnopqrst',
                '----',
                '----',
                '0123456789012345678',
            ],
            [
                {1: 4},
            ],
            [
                {4: 1},
            ]
        )

    def test_move_detection_multi_line_thresholds(self):
        """Testing diff viewer move detection with a multiple lines and
        line count threshold
        """
        self._test_move_detection(
            [
                '123',
                '456',
                '789',
                'ten',
                'abcdefghijk',
                'lmno',
                'pqr',
            ],
            [
                'abcdefghijk',
                'lmno',
                'pqr',
                '123',
                '456',
                '789',
                'ten',
            ],
            [
                {
                    1: 5,
                    2: 6,
                },
            ],
            [
                {
                    5: 1,
                    6: 2,
                },
            ]
        )

    def test_move_detection_similar_blocks(self):
        """Testing diff viewer move detection with multiple blocks of similar
        moved lines
        """
        # See https://hellosplat.com/s/beanbag/tickets/4371/ for a description
        # of the bug.
        testdata_path = os.path.abspath(
            os.path.join(__file__, '..', '..', 'testdata', 'move_detection'))

        with open(os.path.join(testdata_path, 'bug-4371-old.js'), 'r') as fp:
            old = fp.readlines()

        with open(os.path.join(testdata_path, 'bug-4371-new.js'), 'r') as fp:
            new = fp.readlines()

        self._test_move_detection(
            old,
            new,
            [{
                2633: 16,
                2634: 17,
                2635: 18,
                2636: 19,
                2637: 20,
                2638: 21,
                2639: 22,
                2640: 23,
                2642: 24,
                2643: 25,
                2644: 26,
                2645: 27,
                2646: 28,
                2649: 31,
                2650: 32,
                2651: 33,
                2652: 34,
                2653: 35,
                2654: 36,
                2655: 37,
                2656: 38,
                2657: 39,
                2658: 40,
                2659: 41,
                2660: 42,
                2661: 43,
                2662: 44,
                2663: 45,
                2664: 46,
                2665: 47,
            }],
            [{
                16: 2633,
                17: 2634,
                18: 2635,
                19: 2636,
                20: 2637,
                21: 2638,
                22: 2639,
                23: 2640,
                24: 2642,
                25: 2643,
                26: 2644,
                27: 2645,
                28: 2646,
                31: 2649,
                32: 2650,
                33: 2651,
                34: 2652,
                35: 2653,
                36: 2654,
                37: 2655,
                38: 2656,
                39: 2657,
                40: 2658,
                41: 2659,
                42: 2660,
                43: 2661,
                44: 2662,
                45: 2663,
                46: 2664,
                47: 2665,
            }]
        )

    def test_line_counts(self):
        """Testing DiffParser with insert/delete line counts"""
        diff = (
            b'+ This is some line before the change\n'
            b'- And another line\n'
            b'Index: foo\n'
            b'- One last.\n'
            b'--- README  123\n'
            b'+++ README  (new)\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'-blah\n'
            b'+blah!\n'
            b'-blah...\n'
            b'+blah?\n'
            b'-blah!\n'
            b'+blah?!\n')
        files = diffparser.DiffParser(diff).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].insert_count, 3)
        self.assertEqual(files[0].delete_count, 4)

    def _test_move_detection(self, a, b, expected_i_moves, expected_r_moves):
        differ = MyersDiffer(a, b)
        opcode_generator = get_diff_opcode_generator(differ)

        r_moves = []
        i_moves = []

        for opcodes in opcode_generator:
            meta = opcodes[-1]

            if 'moved-to' in meta:
                r_moves.append(meta['moved-to'])

            if 'moved-from' in meta:
                i_moves.append(meta['moved-from'])

        self.assertEqual(i_moves, expected_i_moves)
        self.assertEqual(r_moves, expected_r_moves)
