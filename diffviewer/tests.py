import reviewboard.diffviewer.parser as diffparser
import os
import unittest

class DiffParserTest(unittest.TestCase):
    def diff(self, options=''):
        f = os.popen('diff -rN %s testdata/orig_src testdata/new_src')
        data = f.read()
        f.close()
        return data

    def compareDiffs(self, files, testdir):
        for file in files:
            f = os.open("%s/testdata/%s" %
                        (testdir, os.path.basename(file.newFile)))
            data = f.read()
            f.close()

            self.assertEquals(files.data, data)

    def testNormalDiff(self):
        data = self.diff()
        files = diffparser.parse(data)
        self.compareDiffs(files, "normal")

    def testUnifiedDiff(self):
        data = self.diff('-u')
        files = diffparser.parse(data)
        self.compareDiffs(files, "unified")

    def testContextDiff(self):
        data = self.diff('-c')
        files = diffparser.parse(data)
        self.compareDiffs(files, "context")
