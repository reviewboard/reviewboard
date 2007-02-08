from reviewboard import scmtools
import reviewboard.scmtools.svn as svn
import unittest

class SubversionTests(unittest.TestCase):
    """Unit tests for subversion.  These will fail if you're offline."""

    def setUp(self):
        self.tool = svn.SVNTool(repopath='http://svn.collab.net/repos/svn/')

    def testGetFile(self):
        """Checking SVNTool.get_file"""
        expected = 'include ../tools/Makefile.base-vars\nNAME = misc-docs\n' + \
                   'OUTNAME = svn-misc-docs\nINSTALL_DIR = $(DESTDIR)/usr/s' + \
                   'hare/doc/subversion\ninclude ../tools/Makefile.base-rul' + \
                   'es\n'

        rev = scmtools.Revision('19741')
        data = self.tool.get_file('trunk/doc/misc-docs/Makefile', )

        self.assertEqual(data, expected)

    def testInterface(self):
        """Sanity checking SVNTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), False)

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_pending_changesets(1))
