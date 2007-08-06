import os
import nose
import unittest

from django.test import TestCase as DjangoTestCase
try:
    from p4 import P4Error
except ImportError:
    pass

from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.scmtools.core import SCMError, FileNotFoundError, \
                                      Revision, HEAD, PRE_CREATION, \
                                      ChangeSet
from reviewboard.scmtools.models import Repository, Tool

class CoreTests(unittest.TestCase):
    """Tests for the scmtools.core module"""

    def testInterface(self):
        """Testing basic scmtools.core API"""

        # Empty changeset
        cs = ChangeSet()
        self.assertEqual(cs.changenum, None)
        self.assertEqual(cs.summary, '')
        self.assertEqual(cs.description, '')
        self.assertEqual(cs.branch, '')
        self.assert_(len(cs.bugs_closed) == 0)
        self.assert_(len(cs.files) == 0)


class CVSTests(unittest.TestCase):
    """Unit tests for CVS."""

    def setUp(self):
        self.cvs_repo_path = os.path.join(os.path.dirname(__file__),
                                          'testdata/cvs_repo')
        self.repository = Repository(name='CVS',
                                     path=self.cvs_repo_path,
                                     tool=Tool.objects.get(name='CVS'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest

    def testGetFile(self):
        """Testing CVSTool.get_file"""
        expected = "test content\n"
        file = 'test/testfile'
        rev = Revision('1.1')

        self.assertEqual(self.tool.get_file(file, rev), expected)

        self.assert_(self.tool.file_exists('test/testfile'))
        self.assert_(not self.tool.file_exists('test/testfile2'))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file(''))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', PRE_CREATION))

    def testRevisionParsing(self):
        """Testing revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('', 'PRE-CREATION')[1],
                         PRE_CREATION)
        self.assertEqual(self.tool.parse_diff_revision('', '7 Nov 2005 13:17:07 -0000	1.2')[1],
                         '1.2')
        self.assertEqual(self.tool.parse_diff_revision('', '7 Nov 2005 13:17:07 -0000	1.2.3.4')[1],
                         '1.2.3.4')
        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

    def testInterface(self):
        """Testing basic CVSTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), True)
        self.assertEqual(self.tool.get_fields(), ['diff_path'])

    def testSimpleDiff(self):
        """Testing parsing CVS simple diff"""
        diff = "Index: testfile\n==========================================" + \
               "=========================\nRCS file: %s/test/testfile,v\nre" + \
               "trieving revision 1.1.1.1\ndiff -u -r1.1.1.1 testfile\n--- " + \
               "testfile    26 Jul 2007 08:50:30 -0000      1.1.1.1\n+++ te" + \
               "stfile    26 Jul 2007 10:20:20 -0000\n@@ -1 +1,2 @@\n-test " + \
               "content\n+updated test content\n+added info\n"
        diff = diff % self.cvs_repo_path

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/testfile')
        self.assertEqual(file.origInfo, '26 Jul 2007 08:50:30 -0000      1.1.1.1')
        self.assertEqual(file.newFile, 'testfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:20:20 -0000')
        self.assertEqual(file.data, diff)

    def testBadDiff(self):
        """Testing parsing CVS diff with bad info"""
        diff = "Index: newfile\n===========================================" + \
               "========================\ndiff -N newfile\n--- /dev/null	1" + \
               "Jan 1970 00:00:00 -0000\n+++ newfile	26 Jul 2007 10:11:45 " + \
               "-0000\n@@ -0,0 +1 @@\n+new file content"

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def testBadDiff2(self):
        """Testing parsing CVS bad diff with new file"""
        diff = "Index: newfile\n===========================================" + \
               "========================\nRCS file: newfile\ndiff -N newfil" + \
               "e\n--- /dev/null\n+++ newfile	2" + \
               "6 Jul 2007 10:11:45 -0000\n@@ -0,0 +1 @@\n+new file content"

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def testNewfileDiff(self):
        """Testing parsing CVS diff with new file"""
        diff = "Index: newfile\n===========================================" + \
               "========================\nRCS file: newfile\ndiff -N newfil" + \
               "e\n--- /dev/null	1 Jan 1970 00:00:00 -0000\n+++ newfile	2" + \
               "6 Jul 2007 10:11:45 -0000\n@@ -0,0 +1 @@\n+new file content\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'newfile')
        self.assertEqual(file.origInfo, 'PRE-CREATION')
        self.assertEqual(file.newFile, 'newfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:11:45 -0000')
        self.assertEqual(file.data, diff)


class SubversionTests(unittest.TestCase):
    """Unit tests for subversion."""

    def setUp(self):
        svn_repo_path = os.path.join(os.path.dirname(__file__),
                                     'testdata/svn_repo')
        self.repository = Repository(name='Subversion SVN',
                                     path='file://' + svn_repo_path,
                                     tool=Tool.objects.get(name='Subversion'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest

    def testGetFile(self):
        """Testing SVNTool.get_file"""
        expected = 'include ../tools/Makefile.base-vars\nNAME = misc-docs\n' + \
                   'OUTNAME = svn-misc-docs\nINSTALL_DIR = $(DESTDIR)/usr/s' + \
                   'hare/doc/subversion\ninclude ../tools/Makefile.base-rul' + \
                   'es\n'

        # There are 3 versions of this test in order to get 100% coverage of
        # the svn module.
        rev = Revision('2')
        file = 'trunk/doc/misc-docs/Makefile'

        self.assertEqual(self.tool.get_file(file, rev), expected)

        self.assertEqual(self.tool.get_file('/' + file, rev), expected)

        self.assertEqual(self.tool.get_file(self.repository.path + '/' + file, rev),
                         expected)


        self.assert_(self.tool.file_exists('trunk/doc/misc-docs/Makefile'))
        self.assert_(not self.tool.file_exists('trunk/doc/misc-docs/Makefile2'))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello',
                                                     PRE_CREATION))

    def testRevisionParsing(self):
        """Testing revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('', '(working copy)')[1],
                         HEAD)
        self.assertEqual(self.tool.parse_diff_revision('', '(revision 0)')[1],
                         PRE_CREATION)

        self.assertEqual(self.tool.parse_diff_revision('', '(revision 1)')[1],
                         '1')
        self.assertEqual(self.tool.parse_diff_revision('', '(revision 23)')[1],
                         '23')

        self.assertEqual(self.tool.parse_diff_revision('',
            '2007-06-06 15:32:23 UTC (rev 10958)')[1], '10958')

        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

    def testInterface(self):
        """Testing basic SVNTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), False)

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_pending_changesets(1))

    def testBinaryDiff(self):
        """Testing parsing SVN diff with binary file"""
        diff = "Index: binfile\n===========================================" + \
               "========================\nCannot display: file marked as a " + \
               "binary type.\nsvn:mime-type = application/octet-stream\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'binfile')
        self.assertEqual(file.binary, True)


class PerforceTests(unittest.TestCase):
    """Unit tests for perforce.

       This uses the open server at public.perforce.com to test various
       pieces.  Because we have no control over things like pending
       changesets, not everything can be tested.
       """

    def setUp(self):
        self.repository = Repository(name='Perforce.com',
                                     path='public.perforce.com:1666',
                                     tool=Tool.objects.get(name='Perforce'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest

    def testChangeset(self):
        """Testing PerforceTool.get_changeset"""

        try:
            desc = self.tool.get_changeset(157)
        except P4Error, e:
            if str(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise
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
        for file, expected in map(None, desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(hash(desc.summary), 588429333)

    def testGetFile(self):
        """Testing PerforceTool.get_file"""

        file = self.tool.get_file('//depot/foo', PRE_CREATION)
        self.assertEqual(file, '')

        try:
            file = self.tool.get_file('//public/perforce/api/python/P4Client/p4.py', 1)
        except Exception, e:
            if str(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise
        self.assertEqual(hash(file), 1392492355)

    def testEmptyDiff(self):
        """Testing Perforce empty diff parsing"""
        diff = "==== //depot/foo/proj/README#2 ==M== /src/proj/README ====\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/README')
        self.assertEqual(file.origInfo, '//depot/foo/proj/README#2')
        self.assertEqual(file.newFile, '/src/proj/README')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.binary, False)

    def testBinaryDiff(self):
        """Testing Perforce binary diff parsing"""
        diff = "==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png " + \
               "====\nBinary files /tmp/foo and /src/proj/test.png differ\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.binary, True)

    def testEmptyAndNormalDiffs(self):
        """Testing Perforce empty and normal diff parsing"""
        diff = "==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png " + \
               "====\n" + \
               "--- test.c  //depot/foo/proj/test.c#2\n" + \
               "+++ test.c  01-02-03 04:05:06\n" + \
               "@@ -1 +1,2 @@\n" + \
               "-test content\n" + \
               "+updated test content\n" + \
               "+added info\n"

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].origFile, '//depot/foo/proj/test.png')
        self.assertEqual(files[0].origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(files[0].newFile, '/src/proj/test.png')
        self.assertEqual(files[0].newInfo, '')
        self.assertEqual(files[0].binary, False)

        self.assertEqual(files[1].origFile, 'test.c')
        self.assertEqual(files[1].origInfo, '//depot/foo/proj/test.c#2')
        self.assertEqual(files[1].newFile, 'test.c')
        self.assertEqual(files[1].newInfo, '01-02-03 04:05:06')
        self.assertEqual(files[1].binary, False)


class VMWareTests(DjangoTestCase):
    """Tests for VMware specific code"""
    fixtures = ['vmware.json']

    def setUp(self):
        self.repository = Repository(name='VMware Test',
                                     path='perforce.eng.vmware.com:1666',
                                     tool=Tool.objects.get(name='VMware Perforce'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest

    def testParse(self):
        """Testing VMware changeset parsing"""

        file = open(os.path.join(os.path.dirname(__file__), 'testdata',
                                 'vmware.changeset'), 'r')
        data = file.read().split('\n')
        file.close()

        changeset = self.tool.parse_change_desc(data, 123456)
        self.assertEqual(changeset.summary, "Emma")
        self.assertEqual(hash(changeset.description), 315618127)
        self.assertEqual(changeset.changenum, 123456)
        self.assertEqual(hash(changeset.testing_done), 1030854806)

        self.assertEqual(len(changeset.bugs_closed), 1)
        self.assertEqual(changeset.bugs_closed[0], '128700')

        expected_files = [
            '//depot/bora/hosted07-rel/foo.cc',
            '//depot/bora/hosted07-rel/foo.hh',
            '//depot/bora/hosted07-rel/bar.cc',
            '//depot/bora/hosted07-rel/bar.hh',
        ]
        for file, expected in map(None, changeset.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(changeset.branch,
                         'hosted07-rel &rarr; hosted07 &rarr; bfg-main (manual)')


    def testParseSingleLineDesc(self):
        """Testing VMware changeset parsing with a single line description."""
        file = open(os.path.join(os.path.dirname(__file__), 'testdata',
                                 'vmware-single-line-desc.changeset'), 'r')
        data = file.read().split('\n')
        file.close()

        changeset = self.tool.parse_change_desc(data, 1234567)
        self.assertEqual(changeset.summary,
                         "There is only a single line in this changeset description.")
        self.assertEqual(changeset.description,
                         "There is only a single line in this changeset description.")
        self.assertEqual(changeset.changenum, 1234567)
        self.assertEqual(changeset.testing_done, "")

        self.assertEqual(len(changeset.bugs_closed), 0)

        expected_files = [
            '//depot/qa/foo/bar',
        ]
        for file, expected in map(None, changeset.files, expected_files):
            self.assertEqual(file, expected)

    def testParseMultiLineSummary(self):
        """Testing VMware changeset parsing with a summary spanning multiple lines."""
        file = open(os.path.join(os.path.dirname(__file__), 'testdata',
                                 'vmware-phil-is-crazy.changeset'), 'r')
        data = file.read().split('\n')
        file.close()

        changeset = self.tool.parse_change_desc(data, 123456)
        self.assertEqual(changeset.summary, "Changes: Emma")

        self.assertEqual(changeset.branch, 'bfg-main')
