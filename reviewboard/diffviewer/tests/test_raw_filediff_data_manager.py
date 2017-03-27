from __future__ import unicode_literals

import bz2

from reviewboard.diffviewer.models import RawFileDiffData
from reviewboard.testing import TestCase


class RawFileDiffDataManagerTests(TestCase):
    """Unit tests for RawFileDiffDataManager."""

    small_diff = (
        b'diff --git a/README b/README\n'
        b'index d6613f5..5b50866 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@ -1,1 +1,1 @@\n'
        b'-blah blah\n'
        b'+blah!\n')

    large_diff = (
        b'diff --git a/README b/README\n'
        b'index d6613f5..5b50866 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@ -1,1 +1,10 @@\n'
        b'-blah blah\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n'
        b'+blah!\n')

    def test_process_diff_data_small_diff_uncompressed(self):
        """Testing RawFileDiffDataManager.process_diff_data with small diff
        results in uncompressed storage
        """
        data, compression = \
            RawFileDiffData.objects.process_diff_data(self.small_diff)

        self.assertEqual(data, self.small_diff)
        self.assertIsNone(compression)

    def test_process_diff_data_large_diff_compressed(self):
        """Testing RawFileDiffDataManager.process_diff_data with large diff
        results in bzip2-compressed storage
        """
        data, compression = \
            RawFileDiffData.objects.process_diff_data(self.large_diff)

        self.assertEqual(data, bz2.compress(self.large_diff, 9))
        self.assertEqual(compression, RawFileDiffData.COMPRESSION_BZIP2)
