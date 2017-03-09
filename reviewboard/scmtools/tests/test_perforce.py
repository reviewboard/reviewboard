# coding=utf-8
from __future__ import unicode_literals

import os
from hashlib import md5

import nose
from django.utils import six
from django.utils.six.moves import zip_longest
from djblets.util.filesystem import is_exe_in_path

from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import (AuthenticationError,
                                         RepositoryNotFoundError, SCMError)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.perforce import STunnelProxy, STUNNEL_SERVER
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing import online_only


class PerforceTests(SCMTestCase):
    """Unit tests for perforce.

    This uses the open server at public.perforce.com to test various
    pieces.  Because we have no control over things like pending
    changesets, not everything can be tested.
    """

    fixtures = ['test_scmtools']

    def setUp(self):
        super(PerforceTests, self).setUp()

        self.repository = Repository(name='Perforce.com',
                                     path='public.perforce.com:1666',
                                     username='anonymous',
                                     encoding='none',
                                     tool=Tool.objects.get(name='Perforce'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')

    @online_only
    def test_changeset(self):
        """Testing PerforceTool.get_changeset"""
        desc = self.tool.get_changeset(157)
        self.assertEqual(desc.changenum, 157)
        self.assertEqual(type(desc.description), six.text_type)
        self.assertEqual(md5(desc.description.encode('utf-8')).hexdigest(),
                         'b7eff0ca252347cc9b09714d07397e64')

        expected_files = [
            '//public/perforce/api/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/api/python/P4Client/p4.py',
            '//public/perforce/api/python/P4Client/review.py',
            '//public/perforce/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/python/P4Client/p4.py',
            '//public/perforce/python/P4Client/review.py',
        ]

        for file, expected in zip_longest(desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(md5(desc.summary.encode('utf-8')).hexdigest(),
                         '99a335676b0e5821ffb2f7469d4d7019')

    @online_only
    def test_encoding(self):
        """Testing PerforceTool.get_changeset with a specified encoding"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          username='anonymous',
                          tool=Tool.objects.get(name='Perforce'),
                          encoding='utf8')
        tool = repo.get_scmtool()

        try:
            tool.get_changeset(157)
            self.fail('Expected an error about unicode-enabled servers. Did '
                      'perforce.com turn on unicode for public.perforce.com?')
        except SCMError as e:
            # public.perforce.com doesn't have unicode enabled. Getting this
            # error means we at least passed the charset through correctly
            # to the p4 client.
            self.assertTrue('clients require a unicode enabled server' in
                            six.text_type(e))

    @online_only
    def test_changeset_broken(self):
        """Testing PerforceTool.get_changeset error conditions"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          username='samwise',
                          password='bogus',
                          encoding='none')

        try:
            tool = repo.get_scmtool()
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')

        self.assertRaises(AuthenticationError,
                          lambda: tool.get_changeset(157))

        repo = Repository(name='localhost:1',
                          path='localhost:1',
                          tool=Tool.objects.get(name='Perforce'))

        tool = repo.get_scmtool()
        self.assertRaises(RepositoryNotFoundError,
                          lambda: tool.get_changeset(1))

    @online_only
    def test_get_file(self):
        """Testing PerforceTool.get_file"""
        file = self.tool.get_file('//depot/foo', PRE_CREATION)
        self.assertEqual(file, b'')

        file = self.tool.get_file(
            '//public/perforce/api/python/P4Client/p4.py', 1)
        self.assertEqual(md5(file).hexdigest(),
                         '227bdd87b052fcad9369e65c7bf23fd0')

    @online_only
    def test_custom_host(self):
        """Testing Perforce client initialization with a custom P4HOST"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          username='anonymous',
                          tool=Tool.objects.get(name='Perforce'),
                          encoding='utf8')
        repo.extra_data['p4_host'] = 'my-custom-host'

        tool = repo.get_scmtool()

        with tool.client._connect():
            self.assertEqual(tool.client.p4.host, 'my-custom-host')

    def test_empty_diff(self):
        """Testing Perforce empty diff parsing"""
        diff = b'==== //depot/foo/proj/README#2 ==M== /src/proj/README ====\n'

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/README')
        self.assertEqual(file.origInfo, '//depot/foo/proj/README#2')
        self.assertEqual(file.newFile, '/src/proj/README')
        self.assertEqual(file.newInfo, '')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_binary_diff(self):
        """Testing Perforce binary diff parsing"""
        diff = (b'==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png '
                b'====\nBinary files /tmp/foo and /src/proj/test.png differ\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_deleted_diff(self):
        """Testing Perforce deleted diff parsing"""
        diff = (b'==== //depot/foo/proj/test.png#1 ==D== /src/proj/test.png '
                b'====\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_moved_file_diff(self):
        """Testing Perforce moved file diff parsing"""
        diff = (
            b'Moved from: //depot/foo/proj/test.txt\n'
            b'Moved to: //depot/foo/proj/test2.txt\n'
            b'--- //depot/foo/proj/test.txt  //depot/foo/proj/test.txt#2\n'
            b'+++ //depot/foo/proj/test2.txt  01-02-03 04:05:06\n'
            b'@@ -1 +1,2 @@\n'
            b'-test content\n'
            b'+updated test content\n'
            b'+added info\n'
        )

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.txt')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.txt#2')
        self.assertEqual(file.newFile, '//depot/foo/proj/test2.txt')
        self.assertEqual(file.newInfo, '01-02-03 04:05:06')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertTrue(file.moved)
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_moved_file_diff_no_changes(self):
        """Testing Perforce moved file diff parsing without changes"""
        diff = (b'==== //depot/foo/proj/test.png#5 ==MV== '
                b'//depot/foo/proj/test2.png ====\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#5')
        self.assertEqual(file.newFile, '//depot/foo/proj/test2.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertTrue(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_empty_and_normal_diffs(self):
        """Testing Perforce empty and normal diff parsing"""
        diff1_text = (b'==== //depot/foo/proj/test.png#1 ==A== '
                      b'/src/proj/test.png ====\n')
        diff2_text = (b'--- test.c  //depot/foo/proj/test.c#2\n'
                      b'+++ test.c  01-02-03 04:05:06\n'
                      b'@@ -1 +1,2 @@\n'
                      b'-test content\n'
                      b'+updated test content\n'
                      b'+added info\n')
        diff = diff1_text + diff2_text

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].origFile, '//depot/foo/proj/test.png')
        self.assertEqual(files[0].origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(files[0].newFile, '/src/proj/test.png')
        self.assertEqual(files[0].newInfo, '')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].moved)
        self.assertEqual(files[0].data, diff1_text)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].origFile, 'test.c')
        self.assertEqual(files[1].origInfo, '//depot/foo/proj/test.c#2')
        self.assertEqual(files[1].newFile, 'test.c')
        self.assertEqual(files[1].newInfo, '01-02-03 04:05:06')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].moved)
        self.assertEqual(files[1].data, diff2_text)
        self.assertEqual(files[1].insert_count, 2)
        self.assertEqual(files[1].delete_count, 1)

    def test_diff_file_normalization(self):
        """Testing perforce diff filename normalization"""
        parser = self.tool.get_parser('')
        self.assertEqual(parser.normalize_diff_filename('//depot/test'),
                         '//depot/test')

    def test_unicode_diff(self):
        """Testing Perforce diff parsing with unicode characters"""
        diff = ('--- tést.c  //depot/foo/proj/tést.c#2\n'
                '+++ tést.c  01-02-03 04:05:06\n'
                '@@ -1 +1,2 @@\n'
                '-tést content\n'
                '+updated test content\n'
                '+added info\n').encode('utf-8')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'tést.c')
        self.assertEqual(files[0].origInfo, '//depot/foo/proj/tést.c#2')
        self.assertEqual(files[0].newFile, 'tést.c')
        self.assertEqual(files[0].newInfo, '01-02-03 04:05:06')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].moved)
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 1)


class PerforceStunnelTests(SCMTestCase):
    """Unit tests for perforce running through stunnel.

    Out of the box, Perforce doesn't support any kind of encryption on its
    connections. The recommended setup in this case is to run an stunnel server
    on the perforce server which bounces SSL connections to the normal p4 port.
    One can then start an stunnel on their client machine and connect via a
    localhost: P4PORT.

    For these tests, we set up an stunnel server which will accept secure
    connections and proxy (insecurely) to the public perforce server. We can
    then tell the Perforce SCMTool to connect securely to localhost.
    """

    fixtures = ['test_scmtools']

    def setUp(self):
        super(PerforceStunnelTests, self).setUp()

        if not is_exe_in_path('stunnel'):
            raise nose.SkipTest('stunnel is not installed')

        cert = os.path.join(os.path.dirname(__file__),
                            '..', 'testdata', 'stunnel.pem')
        self.proxy = STunnelProxy(STUNNEL_SERVER, 'public.perforce.com:1666')
        self.proxy.start_server(cert)

        # Find an available port to listen on
        path = 'stunnel:localhost:%d' % self.proxy.port

        self.repository = Repository(name='Perforce.com - secure',
                                     path=path,
                                     username='anonymous',
                                     encoding='none',
                                     tool=Tool.objects.get(name='Perforce'))

        try:
            self.tool = self.repository.get_scmtool()
            self.tool.use_stunnel = True
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')

    def tearDown(self):
        super(PerforceStunnelTests, self).tearDown()

        self.proxy.shutdown()

    def test_changeset(self):
        """Testing PerforceTool.get_changeset with stunnel"""
        desc = self.tool.get_changeset(157)

        self.assertEqual(desc.changenum, 157)
        self.assertEqual(md5(desc.description.encode('utf-8')).hexdigest(),
                         'b7eff0ca252347cc9b09714d07397e64')

        expected_files = [
            '//public/perforce/api/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/api/python/P4Client/p4.py',
            '//public/perforce/api/python/P4Client/review.py',
            '//public/perforce/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/python/P4Client/p4.py',
            '//public/perforce/python/P4Client/review.py',
        ]

        for file, expected in zip_longest(desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(md5(desc.summary.encode('utf-8')).hexdigest(),
                         '99a335676b0e5821ffb2f7469d4d7019')

    def test_get_file(self):
        """Testing PerforceTool.get_file with stunnel"""
        file = self.tool.get_file('//depot/foo', PRE_CREATION)
        self.assertEqual(file, '')

        try:
            file = self.tool.get_file(
                '//public/perforce/api/python/P4Client/p4.py', 1)
        except Exception as e:
            if six.text_type(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise

        self.assertEqual(md5(file).hexdigest(),
                         '227bdd87b052fcad9369e65c7bf23fd0')
