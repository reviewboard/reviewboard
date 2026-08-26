"""Unit tests for reviewboard.admin.server.

Version Added:
    9.0
"""

from __future__ import annotations

import os
import tempfile

from reviewboard.admin.server import is_nfs_path
from reviewboard.testing import TestCase


class IsNFSPathTests(TestCase):
    """Unit tests for is_nfs_path.

    Version Added:
        9.0
    """

    #: The path to the mounts file used for testing.
    mounts_path: str

    @classmethod
    def setUpClass(cls) -> None:
        """Set up state for the test suite.

        This will create a mounts file for testing that can be used in
        individual unit tests.

        Any previously-cached NFS path state will be cleared before tests
        begin.
        """
        super().setUpClass()

        fd, mounts_path = tempfile.mkstemp()

        with os.fdopen(fd, 'wb') as fp:
            fp.write(b'server:/export /mnt/nfs nfs rw 0 0\n')
            fp.write(b'server:/export /mnt/nfs4 nfs4 rw 0 0\n')
            fp.write(b'/dev/sdb1 /mnt/nfs/local ext4 rw 0 0\n')
            fp.write(b'/dev/sdb2 /mnt/local ext4 rw 0 0\n')
            fp.close()

        cls.mounts_path = mounts_path
        is_nfs_path.cache_clear()

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down state for the test suite.

        This will clear out the mounts path used for the tests, and clear
        away any cached NFS path state.
        """
        os.unlink(cls.mounts_path)
        delattr(cls, 'mounts_path')

        is_nfs_path.cache_clear()

        super().tearDownClass()

    def test_with_nfs_mount(self) -> None:
        """Testing is_nfs_path with NFS mount path"""
        self.assertTrue(is_nfs_path(
            '/mnt/nfs/data',
            _mounts_path=self.mounts_path,
        ))

    def test_with_nfs4_mount(self) -> None:
        """Testing is_nfs_path with NFS4 mount path"""
        self.assertTrue(is_nfs_path(
            '/mnt/nfs4/data',
            _mounts_path=self.mounts_path,
        ))

    def test_with_local_mount(self) -> None:
        """Testing is_nfs_path with local mount"""
        self.assertFalse(is_nfs_path(
            '/mnt/local',
            _mounts_path=self.mounts_path,
        ))

    def test_with_local_over_nfs_precedence(self) -> None:
        """Testing is_nfs_path with local mount with higher precedence than
        NFS mount path
        """
        self.assertFalse(is_nfs_path(
            '/mnt/nfs/local/data',
            _mounts_path=self.mounts_path,
        ))

    def test_without_mount(self) -> None:
        """Testing is_nfs_path without mount path"""
        self.assertFalse(is_nfs_path(
            '/var/www/reviewboard/data',
            _mounts_path=self.mounts_path,
        ))

    def test_without_mounts_path(self) -> None:
        """Testing is_nfs_path without /proc/mounts path"""
        self.assertFalse(is_nfs_path(
            '/mnt/nfs/data',
            _mounts_path=f'{self.mounts_path}-XXX',
        ))
