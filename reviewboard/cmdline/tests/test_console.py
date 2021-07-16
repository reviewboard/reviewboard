"""Unit tests for reviewboard.cmdline.utils.console."""

from __future__ import print_function, unicode_literals

import io

from reviewboard.cmdline.utils.console import Console
from reviewboard.testing.testcase import TestCase


class ConsoleTests(TestCase):
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
