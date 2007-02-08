from scmtools.core import SCMException, FileNotFoundException
from scmtools.core import HEAD, PRE_CREATION
from scmtools.core import Revision
from scmtools.svn import SVNTool
import unittest

class SubversionTests(unittest.TestCase):
    """Unit tests for subversion.  These will fail if you're offline."""

    def setUp(self):
        self.tool = SVNTool(repopath='http://svn.collab.net/repos/svn/')

    def testGetFile(self):
        """Checking SVNTool.get_file"""
        expected = 'include ../tools/Makefile.base-vars\nNAME = misc-docs\n' + \
                   'OUTNAME = svn-misc-docs\nINSTALL_DIR = $(DESTDIR)/usr/s' + \
                   'hare/doc/subversion\ninclude ../tools/Makefile.base-rul' + \
                   'es\n'

        data = self.tool.get_file('trunk/doc/misc-docs/Makefile',
                                  Revision('19741'))

        self.assertEqual(data, expected)


        self.assertRaises(FileNotFoundException,
                          lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundException,
                          lambda: self.tool.get_file('hello',
                                                     PRE_CREATION))

    def testRevisionParsing(self):
        """Testing revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('(working copy)'),
                         HEAD)
        self.assertEqual(self.tool.parse_diff_revision('(revision 0)'),
                         PRE_CREATION)

        self.assertEqual(self.tool.parse_diff_revision('(revision 1)'),
                         '1')
        self.assertEqual(self.tool.parse_diff_revision('(revision 23)'),
                         '23')

        self.assertRaises(SCMException,
                          lambda: self.tool.parse_diff_revision('hello'))

    def testInterface(self):
        """Sanity checking SVNTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), False)

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_pending_changesets(1))
