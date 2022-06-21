"""Unit tests for reviewboard.cmdline.utils.console."""

import io
import math
import shutil

import kgb
from django.core.management.color import supports_color

from reviewboard.cmdline.utils.console import Console
from reviewboard.testing.testcase import TestCase


class ConsoleTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.cmdline.utils.console.Console."""

    def test_with_non_utf8_streams(self):
        """Testing Console with non-utf-8 stdout/stderr streams"""
        stdout_buffer = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_buffer, encoding='latin1')

        stderr_buffer = io.BytesIO()
        stderr = io.TextIOWrapper(stderr_buffer, encoding='latin1')

        try:
            console = Console(stdout=stdout,
                              stderr=stderr)

            # This will output Unicode content to stdout, and should fail
            # if there's an encoding issue.
            console.print('\U0001f9f8')

            # There's no wrapper for stderr, so write to it directly.
            console.stderr.write('\U0001f534')

            # Make sure we got the results we expected.
            self.assertEqual(stdout_buffer.getvalue(),
                             b'\xf0\x9f\xa7\xb8\n')
            self.assertEqual(stderr_buffer.getvalue(),
                             b'\xf0\x9f\x94\xb4')
        finally:
            stdout.close()
            stderr.close()

    def test_print_with_styled_prefix(self):
        """Testing Console.print with styled indent prefix"""
        self.spy_on(supports_color, op=kgb.SpyOpReturn(True))
        self.spy_on(shutil.get_terminal_size, op=kgb.SpyOpReturn((50, 40)))

        stdout_buffer = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_buffer)

        try:
            console = Console(stdout=stdout,
                              allow_color=True)

            prefix_len = len('Warning: ')
            avail_len = console.term_width - prefix_len - 1

            console.warning('x ' * math.ceil(3 * (avail_len / 2)))

            self.assertEqual(
                stdout_buffer.getvalue(),
                b'\n'
                b'\x1b[33;1mWarning: \x1b[0m'
                b'x x x x x x x x x x x x x x x x x x x x x\n'
                b'         x x x x x x x x x x x x x x x x x x x x x\n'
                b'         x x x x x x x x x x x x x x x x x x\n'
                b'\n')
        finally:
            stdout.close()

    def test_print_with_prefix_and_multiple_paragraphs(self):
        """Testing Console.print with indent prefix and multiple paragraphs"""
        self.spy_on(shutil.get_terminal_size, op=kgb.SpyOpReturn((50, 40)))

        stdout_buffer = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_buffer)

        try:
            console = Console(stdout=stdout)
            console.warning('line 1\n'
                            'line 2\n'
                            'line 3\n')

            self.assertEqual(
                stdout_buffer.getvalue(),
                b'\n'
                b'Warning: line 1\n'
                b'\n'
                b'         line 2\n'
                b'\n'
                b'         line 3\n'
                b'\n')
        finally:
            stdout.close()
