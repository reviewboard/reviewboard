"""Unit tests for reviewboard.attachments.mimetypes.

Version Added:
    7.0.3
"""

from __future__ import annotations

import os
import subprocess

import kgb
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from djblets.util.filesystem import is_exe_in_path

from reviewboard.attachments.mimetypes import guess_mimetype
from reviewboard.testing import TestCase


class GuessMimetypeTests(kgb.SpyAgency, TestCase):
    """Unit tests for guess_mimetype.

    Version Added:
        7.0.3
    """

    def test_with_text(self) -> None:
        """Testing guess_mimetype with text file"""
        file = SimpleUploadedFile('test.txt', b'this is a text\n')

        self.assertEqual(guess_mimetype(file), 'text/plain')
        self.assertEqual(file.tell(), 0)

    def test_with_image(self) -> None:
        """Testing guess_mimetype with text file"""
        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'logo.png')

        with open(filename, 'rb') as fp:
            file = SimpleUploadedFile(fp.name, fp.read())

        self.assertEqual(guess_mimetype(file), 'image/png')
        self.assertEqual(file.tell(), 0)

    def test_with_pdf(self) -> None:
        """Testing guess_mimetype with PDF"""
        file = SimpleUploadedFile('test.pdf', b'\x25\x50\x44\x46\x2d')

        self.assertEqual(guess_mimetype(file), 'application/pdf')
        self.assertEqual(file.tell(), 0)

    def test_with_unknown(self) -> None:
        """Testing guess_mimetype with unknown file type"""
        file = SimpleUploadedFile('image.png', b'\0\1\2\3\4\5')

        self.assertEqual(guess_mimetype(file), 'application/octet-stream')
        self.assertEqual(file.tell(), 0)

    def test_with_large_file(self) -> None:
        """Testing guess_mimetype with large file"""
        # We'll pick a big payload size that should go beyond the read length
        # from `file`, causing the pipe to close early.
        #
        # Not that not all Python subprocess.Popen implementations will crash
        # when trying to close a pipe more than once.
        file = SimpleUploadedFile(
            'test.bin',
            b'\x25\x50\x44\x46\x2d' + (b'\0' * 1024 * 1024 * 5))

        self.assertEqual(guess_mimetype(file), 'application/pdf')
        self.assertEqual(file.tell(), 0)

    def test_with_exit_error(self) -> None:
        """Testing guess_mimetype with non-0 exit code"""
        self.spy_on(subprocess.Popen.wait,
                    owner=subprocess.Popen,
                    op=kgb.SpyOpReturn(1))

        file = SimpleUploadedFile('test.pdf', b'\x25\x50\x44\x46\x2d')

        self.assertEqual(guess_mimetype(file), 'application/octet-stream')
        self.assertEqual(file.tell(), 0)

    def test_with_file_exe_not_found(self) -> None:
        """Testing guess_mimetype with file executable not found"""
        self.spy_on(is_exe_in_path, op=kgb.SpyOpReturn(False))

        file = SimpleUploadedFile('test.pdf', b'\x25\x50\x44\x46\x2d')

        self.assertEqual(guess_mimetype(file), 'application/octet-stream')
        self.assertEqual(file.tell(), 0)
