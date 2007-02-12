import unittest

from django.core.exceptions import ImproperlyConfigured

from reviewboard.scmtools.core import SCMException, FileNotFoundException, \
                                      Revision, HEAD, PRE_CREATION, get_tool, \
                                      ChangeSet
from reviewboard.scmtools.svn import SVNTool
from reviewboard.scmtools.perforce import PerforceTool

class CoreTests(unittest.TestCase):
    """Tests for the scmtools.core module"""

    def testGetTool(self):
        """Testing tool instantiation"""
        tool = get_tool('reviewboard.scmtools.svn.SVNTool')
        self.assertEqual(tool.__class__, SVNTool)

        tool = get_tool('reviewboard.scmtools.perforce.PerforceTool')
        self.assertEqual(tool.__class__, PerforceTool)

        self.assertRaises(ImproperlyConfigured,
                          lambda: get_tool('blah.blah'))

        self.assertRaises(ImproperlyConfigured,
                          lambda: get_tool('reviewboard.scmtools.svn.Foo'))


    def testInterface(self):
        """Sanity checking scmtools.core API"""

        # Empty changeset
        cs = ChangeSet()
        self.assertEqual(cs.changenum, None)
        self.assertEqual(cs.summary, '')
        self.assertEqual(cs.description, '')
        self.assertEqual(cs.branch, '')
        self.assert_(len(cs.bugs_closed) == 0)
        self.assert_(len(cs.files) == 0)


class SubversionTests(unittest.TestCase):
    """Unit tests for subversion.  These will fail if you're offline."""

    def setUp(self):
        self.repo = 'http://svn.collab.net/repos/svn/'
        self.tool = SVNTool(repopath=self.repo)

    def testGetFile(self):
        """Checking SVNTool.get_file"""
        expected = 'include ../tools/Makefile.base-vars\nNAME = misc-docs\n' + \
                   'OUTNAME = svn-misc-docs\nINSTALL_DIR = $(DESTDIR)/usr/s' + \
                   'hare/doc/subversion\ninclude ../tools/Makefile.base-rul' + \
                   'es\n'

        # There are 3 versions of this test in order to get 100% coverage of
        # the svn module.
        rev = Revision('19741')
        file = 'trunk/doc/misc-docs/Makefile'

        self.assertEqual(self.tool.get_file(file, rev), expected)

        self.assertEqual(self.tool.get_file('/' + file, rev), expected)

        self.assertEqual(self.tool.get_file(self.repo + '/' + file, rev),
                         expected)


        self.assert_(self.tool.file_exists('trunk/doc/misc-docs/Makefile'))
        self.assert_(not self.tool.file_exists('trunk/doc/misc-docs/Makefile2'))

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


class PerforceTests(unittest.TestCase):
    """Unit tests for perforce.

       This uses the open server at public.perforce.com to test various
       pieces.  Because we have no control over things like pending
       changesets, not everything can be tested.
       """

    def setUp(self):
        self.tool = PerforceTool('public.perforce.com:1666')

    def testChangeset(self):
        """Checking PerforceTool.get_changeset"""

        desc = self.tool.get_changeset(157)
        self.assertEqual(desc.changenum, 157)
        self.assertEqual(hash(desc.description), -209144366)

        expected_files = [
            '//public/perforce/api/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/api/python/P4Client/p4.py',
            '//public/perforce/api/python/P4Client/review.py',
            '//public/perforce/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/python/P4Client/p4.py',
            '//public/perforce/python/P4Client/review.py',
        ]
        for file, expected in zip(desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(hash(desc.summary), 588429333)

    def testGetFile(self):
        """Checking PerforceTool.get_file"""

        file = self.tool.get_file('//public/perforce/api/python/P4Client/p4.py',
                                  157)
        self.assertEqual(hash(file), 1241177531)
