import os
import reviewboard.diffviewer.parser as diffparser
import unittest

class DiffParserTest(unittest.TestCase):
    PREFIX = 'diffviewer/testdata'

    def diff(self, options=''):
        f = os.popen('diff -rN -x .svn %s %s/orig_src %s/new_src' %
                     (options, self.PREFIX, self.PREFIX))
        data = f.read()
        f.close()
        return data

    def compareDiffs(self, files, testdir):
        self.failUnless(len(files) == 3)
        for file in files:
            f = open("%s/diffs/%s/%s.diff" %
                     (self.PREFIX, testdir, os.path.basename(file.newFile)))
            data = f.read()
            f.close()

            self.failUnless(file.origFile.startswith("%s/orig_src/" %
                                                     self.PREFIX))
            self.failUnless(file.newFile.startswith("%s/new_src/" %
                                                    self.PREFIX))
            self.assertNotEquals(file.origInfo, "")
            self.assertNotEquals(file.newInfo, "")

            self.assertNotEquals(file.data, "")
            self.assertNotEquals(data, "")

            # Can't really compare the strings because of timestamps...

    def testUnifiedDiff(self):
        """Checking parse on a unified diff"""
        data = self.diff('-u')
        files = diffparser.parse(data)
        self.compareDiffs(files, "unified")

    def testContextDiff(self):
        """Checking parse on a context diff"""
        data = self.diff('-c')
        files = diffparser.parse(data)
        self.compareDiffs(files, "context")
