import os
import unittest

import reviewboard.diffviewer.parser as diffparser
from reviewboard.diffviewer.diffutils import patch

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
        """Testing parse on a unified diff"""
        data = self.diff('-u')
        files = diffparser.parse(data)
        self.compareDiffs(files, "unified")

    def testContextDiff(self):
        """Testing parse on a context diff"""
        data = self.diff('-c')
        files = diffparser.parse(data)
        self.compareDiffs(files, "context")

    def testPatch(self):
        """Testing patching"""

        def get_file(*relative):
            f = open(os.path.join(*tuple([self.PREFIX] + list(relative))))
            data = f.read()
            f.close()
            return data

        file = 'foo.c'

        old = get_file('orig_src', file)
        new = get_file('new_src', file)
        diff = get_file('diffs', 'unified', 'foo.c.diff')

        patched = patch(diff, old, file)
        self.assertEqual(patched, new)

        diff = get_file('diffs', 'unified', 'README.diff')
        self.assertRaises(Exception, lambda: patch(diff, old, file))
