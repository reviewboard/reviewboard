from __future__ import unicode_literals

import mimeparse
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.safestring import SafeText
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard import initialize
from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.mimetypes import (MimetypeHandler,
                                               register_mimetype_handler,
                                               unregister_mimetype_handler)
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.testing import TestCase


class BaseFileAttachmentTestCase(TestCase):
    """Base functionality for FileAttachment test cases."""

    def setUp(self):
        """Set up this test case."""
        initialize()

    def make_uploaded_file(self):
        """Create a return a file to use for mocking in forms."""
        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'trophy.png')
        f = open(filename, 'r')
        uploaded_file = SimpleUploadedFile(f.name, f.read(),
                                           content_type='image/png')
        f.close()

        return uploaded_file

    def make_filediff(self, is_new=False, diffset_history=None,
                      diffset_revision=1, source_filename='file1',
                      dest_filename='file2'):
        """Create and return a FileDiff with the given data."""
        if is_new:
            source_revision = PRE_CREATION
            dest_revision = ''
        else:
            source_revision = '1'
            dest_revision = '2'

        repository = self.create_repository()

        if not diffset_history:
            diffset_history = DiffSetHistory.objects.create(name='testhistory')

        diffset = DiffSet.objects.create(name='test',
                                         revision=diffset_revision,
                                         repository=repository,
                                         history=diffset_history)
        filediff = FileDiff(source_file=source_filename,
                            source_revision=source_revision,
                            dest_file=dest_filename,
                            dest_detail=dest_revision,
                            diffset=diffset,
                            binary=True)
        filediff.save()

        return filediff


class FileAttachmentTests(BaseFileAttachmentTestCase):
    """Tests for the FileAttachment model."""

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file(self):
        """Testing uploading a file attachment"""
        review_request = self.create_review_request(publish=True)

        file = self.make_uploaded_file()
        form = UploadFileForm(review_request, files={
            'path': file,
        })
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        self.assertTrue(os.path.basename(file_attachment.file.name).endswith(
            '__trophy.png'))
        self.assertEqual(file_attachment.mimetype, 'image/png')

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_with_history(self):
        """Testing uploading a file attachment to an existing
        FileAttachmentHistory
        """
        review_request_1 = self.create_review_request(publish=True)
        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request_1.file_attachment_histories.add(history)

        file = self.make_uploaded_file()
        form = UploadFileForm(review_request_1,
                              data={'attachment_history': history.pk},
                              files={'path': file})
        self.assertTrue(form.is_valid())
        form.create()

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_with_history_mismatch(self):
        """Testing uploading a file attachment to an existing
        FileAttachmentHistory with a mismatched review request
        """
        review_request_1 = self.create_review_request(publish=True)
        review_request_2 = self.create_review_request(publish=True)

        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request_1.file_attachment_histories.add(history)

        form = UploadFileForm(review_request_2,
                              data={'attachment_history': history.pk},
                              files={'path': file})
        self.assertFalse(form.is_valid())

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_revisions(self):
        """Testing uploading multiple revisions of a file"""
        review_request = self.create_review_request(publish=True)
        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request.file_attachment_histories.add(history)
        file = self.make_uploaded_file()

        # Add a file with the given history
        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 1)
        self.assertEqual(history.latest_revision, 1)
        self.assertEqual(history.display_position, 0)

        review_request.get_draft().publish()

        # Post an update
        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 2)
        self.assertEqual(history.latest_revision, 2)
        self.assertEqual(history.display_position, 0)

        review_request.get_draft().publish()

        # Post two updates without publishing the draft in between
        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 3)
        self.assertEqual(history.latest_revision, 3)
        self.assertEqual(history.display_position, 0)

        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 3)
        self.assertEqual(history.latest_revision, 3)
        self.assertEqual(history.display_position, 0)

        # Add another (unrelated) file to check display position
        form = UploadFileForm(review_request,
                              files={'path': file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        self.assertEqual(file_attachment.attachment_revision, 1)
        self.assertEqual(file_attachment.attachment_history.latest_revision, 1)
        self.assertEqual(file_attachment.attachment_history.display_position,
                         1)

    def test_is_from_diff_with_no_association(self):
        """Testing FileAttachment.is_from_diff with standard attachment"""
        file_attachment = FileAttachment()

        self.assertFalse(file_attachment.is_from_diff)

    @add_fixtures(['test_scmtools'])
    def test_is_from_diff_with_repository(self):
        """Testing FileAttachment.is_from_diff with repository association"""
        repository = self.create_repository()
        file_attachment = FileAttachment(repository=repository)

        self.assertTrue(file_attachment.is_from_diff)

    @add_fixtures(['test_scmtools'])
    def test_is_from_diff_with_filediff(self):
        """Testing FileAttachment.is_from_diff with filediff association"""
        filediff = self.make_filediff()
        file_attachment = FileAttachment(added_in_filediff=filediff)

        self.assertTrue(file_attachment.is_from_diff)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_utf16_thumbnail(self):
        """Testing file attachment thumbnail generation for UTF-16 files"""
        filename = os.path.join(os.path.dirname(__file__),
                                'testdata', 'utf-16.txt')
        with open(filename) as f:
            review_request = self.create_review_request(publish=True)

            file = SimpleUploadedFile(
                f.name,
                f.read(),
                content_type='text/plain;charset=utf-16le')
            form = UploadFileForm(review_request, files={'path': file})
            form.is_valid()

            file_attachment = form.create()

            self.assertEqual(
                file_attachment.thumbnail,
                '<div class="file-thumbnail"> <div class="file-thumbnail-clipp'
                'ed"><pre>UTF-16le encoded sample plain-text file</pre><pre>'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e</pre>'
                '<pre></pre><pre>Markus Kuhn [\u02c8ma\u02b3k\u028as ku\u02d0'
                'n] &lt;http://www.cl.cam.ac.uk/~mgk25/&gt; \u2014 2002-07-25'
                '</pre><pre></pre><pre></pre><pre>The ASCII compatible UTF-8 '
                'encoding used in this plain-text file</pre><pre>is defined '
                'in Unicode, ISO 10646-1, and RFC 2279.</pre><pre></pre><pre>'
                '</pre><pre>Using Unicode/UTF-8, you can write in emails and '
                'source code things such as</pre><pre></pre><pre>Mathematics '
                'and sciences:</pre><pre></pre><pre>  \u222e E\u22c5da = Q,  '
                'n \u2192 \u221e, \u2211 f(i) = \u220f g(i),      \u23a7\u23a1'
                '\u239b\u250c\u2500\u2500\u2500\u2500\u2500\u2510\u239e\u23a4'
                '\u23ab</pre><pre>                                           '
                ' \u23aa\u23a2\u239c\u2502a\xb2+b\xb3 \u239f\u23a5\u23aa'
                '</pre><pre>  \u2200x\u2208</pre></div></div>')


class MimetypeTest(MimetypeHandler):
    """Handler for all test mimetypes."""

    supported_mimetypes = ['test/*']


class TestAbcMimetype(MimetypeHandler):
    """Handler for the test/abc mimetype."""

    supported_mimetypes = ['test/abc']


class TestXmlMimetype(MimetypeHandler):
    """Handler for the test/xml mimetype."""

    supported_mimetypes = ['test/xml']


class Test2AbcXmlMimetype(MimetypeHandler):
    """Handler for the test/abc+xml mimetype."""

    supported_mimetypes = ['test2/abc+xml']


class StarDefMimetype(MimetypeHandler):
    """Handler for all /def mimetypes."""

    supported_mimetypes = ['*/def']


class StarAbcDefMimetype(MimetypeHandler):
    """Handler for all /abc+def mimetypes."""

    supported_mimetypes = ['*/abc+def']


class Test3XmlMimetype(MimetypeHandler):
    """Handler for the test3/xml mimetype."""

    supported_mimetypes = ['test3/xml']


class Test3AbcXmlMimetype(MimetypeHandler):
    """Handler for the test3/abc+xml mimetype."""

    supported_mimetypes = ['test3/abc+xml']


class Test3StarMimetype(MimetypeHandler):
    """Handler for all test3 mimetypes."""

    supported_mimetypes = ['test3/*']


class MimetypeHandlerTests(TestCase):
    """Tests for mimetype handlers."""

    def setUp(self):
        """Set up this test case."""
        super(MimetypeHandlerTests, self).setUp()

        # Register test cases in same order as they are defined
        # in this test
        register_mimetype_handler(MimetypeTest)
        register_mimetype_handler(TestAbcMimetype)
        register_mimetype_handler(TestXmlMimetype)
        register_mimetype_handler(Test2AbcXmlMimetype)
        register_mimetype_handler(StarDefMimetype)
        register_mimetype_handler(StarAbcDefMimetype)
        register_mimetype_handler(Test3XmlMimetype)
        register_mimetype_handler(Test3AbcXmlMimetype)
        register_mimetype_handler(Test3StarMimetype)

    def tearDown(self):
        """Tear down this test case."""
        super(MimetypeHandlerTests, self).tearDown()

        # Unregister test cases in same order as they are defined
        # in this test
        unregister_mimetype_handler(MimetypeTest)
        unregister_mimetype_handler(TestAbcMimetype)
        unregister_mimetype_handler(TestXmlMimetype)
        unregister_mimetype_handler(Test2AbcXmlMimetype)
        unregister_mimetype_handler(StarDefMimetype)
        unregister_mimetype_handler(StarAbcDefMimetype)
        unregister_mimetype_handler(Test3XmlMimetype)
        unregister_mimetype_handler(Test3AbcXmlMimetype)
        unregister_mimetype_handler(Test3StarMimetype)

    def _handler_for(self, mimetype):
        mt = mimeparse.parse_mime_type(mimetype)
        score, handler = MimetypeHandler.get_best_handler(mt)
        return handler

    def test_handler_factory(self):
        """Testing matching of factory method for mimetype handlers"""
        # Exact Match
        self.assertEqual(self._handler_for("test/abc"), TestAbcMimetype)
        self.assertEqual(self._handler_for("test2/abc+xml"),
                         Test2AbcXmlMimetype)
        # Handle vendor-specific match
        self.assertEqual(self._handler_for("test/abc+xml"), TestXmlMimetype)
        self.assertEqual(self._handler_for("test2/xml"), Test2AbcXmlMimetype)
        # Nearest-match for non-matching subtype
        self.assertEqual(self._handler_for("test2/baz"), Test2AbcXmlMimetype)
        self.assertEqual(self._handler_for("foo/bar"), StarDefMimetype)

    def test_handler_factory_precedence(self):
        """Testing precedence of factory method for mimetype handlers"""
        self.assertEqual(self._handler_for("test2/def"), StarDefMimetype)
        self.assertEqual(self._handler_for("test3/abc+xml"),
                         Test3AbcXmlMimetype)
        self.assertEqual(self._handler_for("test3/xml"), Test3XmlMimetype)
        self.assertEqual(self._handler_for("foo/abc+def"), StarAbcDefMimetype)
        self.assertEqual(self._handler_for("foo/def"), StarDefMimetype)
        # Left match and Wildcard should trump Left Wildcard and match
        self.assertEqual(self._handler_for("test/def"), MimetypeTest)


class FileAttachmentManagerTests(BaseFileAttachmentTestCase):
    """Tests for FileAttachmentManager."""

    fixtures = ['test_scmtools']

    def test_create_from_filediff_with_new_and_modified_true(self):
        """Testing FileAttachmentManager.create_from_filediff
        with new FileDiff and modified=True
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')
        self.assertEqual(file_attachment.repository_id, None)
        self.assertEqual(file_attachment.repo_path, None)
        self.assertEqual(file_attachment.repo_revision, None)
        self.assertEqual(file_attachment.added_in_filediff, filediff)

    def test_create_from_filediff_with_new_and_modified_false(self):
        """Testing FileAttachmentManager.create_from_filediff
        with new FileDiff and modified=False
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        self.assertRaises(
            AssertionError,
            FileAttachment.objects.create_from_filediff,
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png',
            from_modified=False)

    def test_create_from_filediff_with_existing_and_modified_true(self):
        """Testing FileAttachmentManager.create_from_filediff
        with existing FileDiff and modified=True
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')
        self.assertEqual(file_attachment.repository,
                         filediff.diffset.repository)
        self.assertEqual(file_attachment.repo_path, filediff.dest_file)
        self.assertEqual(file_attachment.repo_revision, filediff.dest_detail)
        self.assertEqual(file_attachment.added_in_filediff_id, None)

    def test_create_from_filediff_with_existing_and_modified_false(self):
        """Testing FileAttachmentManager.create_from_filediff
        with existing FileDiff and modified=False
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png',
            from_modified=False)
        self.assertEqual(file_attachment.repository,
                         filediff.diffset.repository)
        self.assertEqual(file_attachment.repo_path, filediff.source_file)
        self.assertEqual(file_attachment.repo_revision,
                         filediff.source_revision)
        self.assertEqual(file_attachment.added_in_filediff_id, None)

    def test_get_for_filediff_with_new_and_modified_true(self):
        """Testing FileAttachmentManager.get_for_filediff
        with new FileDiff and modified=True
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=True),
            file_attachment)

    def test_get_for_filediff_with_new_and_modified_false(self):
        """Testing FileAttachmentManager.get_for_filediff
        with new FileDiff and modified=False
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=False),
            None)

    def test_get_for_filediff_with_existing_and_modified_true(self):
        """Testing FileAttachmentManager.get_for_filediff
        with existing FileDiff and modified=True
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=True),
            file_attachment)

    def test_get_for_filediff_with_existing_and_modified_false(self):
        """Testing FileAttachmentManager.get_for_filediff
        with existing FileDiff and modified=False
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png',
            from_modified=False)

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=False),
            file_attachment)


class DiffViewerFileAttachmentTests(BaseFileAttachmentTestCase):
    """Tests for inline diff file attachments in the diff viewer."""

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def setUp(self):
        """Set up this test case."""
        super(DiffViewerFileAttachmentTests, self).setUp()

        # The diff viewer's caching breaks the result of these tests,
        # so be sure we clear before each one.
        cache.clear()

    def test_added_file(self):
        """Testing inline diff file attachments with newly added files"""
        # Set up the initial state.
        user = User.objects.get(username='doc')
        review_request = ReviewRequest.objects.create(user, None)
        filediff = self.make_filediff(
            is_new=True,
            diffset_history=review_request.diffset_history)

        # Create a diff file attachment to be displayed inline.
        diff_file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            filename='my-file',
            file=self.make_uploaded_file(),
            mimetype='image/png')
        review_request.file_attachments.add(diff_file_attachment)
        review_request.publish(user)

        # Load the diff viewer.
        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/diff/1/fragment/%s/'
                                   % (review_request.pk, filediff.pk))
        self.assertEqual(response.status_code, 200)

        # The file attachment should appear as the right-hand side
        # file attachment in the diff viewer.
        self.assertEqual(response.context['orig_diff_file_attachment'], None)
        self.assertEqual(response.context['modified_diff_file_attachment'],
                         diff_file_attachment)

    def test_modified_file(self):
        """Testing inline diff file attachments with modified files"""
        # Set up the initial state.
        user = User.objects.get(username='doc')
        review_request = ReviewRequest.objects.create(user, None)
        filediff = self.make_filediff(
            is_new=False,
            diffset_history=review_request.diffset_history)
        self.assertFalse(filediff.is_new)

        # Create diff file attachments to be displayed inline.
        uploaded_file = self.make_uploaded_file()

        orig_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            filename='my-file',
            file=uploaded_file,
            mimetype='image/png',
            from_modified=False)
        modified_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            filename='my-file',
            file=uploaded_file,
            mimetype='image/png')
        review_request.file_attachments.add(orig_attachment)
        review_request.file_attachments.add(modified_attachment)
        review_request.publish(user)

        # Load the diff viewer.
        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/diff/1/fragment/%s/'
                                   % (review_request.pk, filediff.pk))
        self.assertEqual(response.status_code, 200)

        # The file attachment should appear as the right-hand side
        # file attachment in the diff viewer.
        self.assertEqual(response.context['orig_diff_file_attachment'],
                         orig_attachment)
        self.assertEqual(response.context['modified_diff_file_attachment'],
                         modified_attachment)


class SandboxMimetypeHandler(MimetypeHandler):
    """Handler for image/png mimetypes, used for testing sandboxing."""

    supported_mimetypes = ['image/png']

    def get_icon_url(self):
        """Raise an exception to test sandboxing."""
        raise Exception

    def get_thumbnail(self):
        """Raise an exception to test sandboxing."""
        raise Exception

    def set_thumbnail(self, data):
        """Raise an exception to test sandboxing."""
        raise Exception


class SandboxTests(SpyAgency, BaseFileAttachmentTestCase):
    """Testing MimetypeHandler sandboxing."""

    def setUp(self):
        """Set up this test case."""
        super(SandboxTests, self).setUp()

        register_mimetype_handler(SandboxMimetypeHandler)

        user = User.objects.create(username='reviewboard',
                                   password='password', email='')

        review_request = self.create_review_request(submitter=user)
        self.file_attachment = self.create_file_attachment(
            review_request=review_request)

    def tearDown(self):
        """Tear down this test case."""
        super(SandboxTests, self).tearDown()

        unregister_mimetype_handler(SandboxMimetypeHandler)

    def test_get_thumbnail(self):
        """Testing FileAttachment sandboxes MimetypeHandler.get_thumbnail"""
        self.spy_on(SandboxMimetypeHandler.get_thumbnail)

        self.file_attachment.thumbnail
        self.assertTrue(SandboxMimetypeHandler.get_thumbnail.called)

    def test_set_thumbnail(self):
        """Testing FileAttachment sandboxes MimetypeHandler.set_thumbnail"""
        self.spy_on(SandboxMimetypeHandler.set_thumbnail)

        self.file_attachment.thumbnail = None
        self.assertTrue(SandboxMimetypeHandler.set_thumbnail.called)

    def test_get_icon_url(self):
        """Testing FileAttachment sandboxes MimetypeHandler.get_icon_url"""
        self.spy_on(SandboxMimetypeHandler.get_icon_url)

        self.file_attachment.icon_url
        self.assertTrue(SandboxMimetypeHandler.get_icon_url.called)


class TextMimetypeTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.attachments.mimetypes.TextMimetype."""

    fixtures = ['test_users']

    def setUp(self):
        uploaded_file = SimpleUploadedFile(
            'test.txt',
            b'<p>This is a test</p>',
            content_type='text/plain')

        review_request = self.create_review_request(publish=True)

        form = UploadFileForm(review_request, files={
            'path': uploaded_file,
        })
        self.assertTrue(form.is_valid())

        self.file_attachment = form.create()

    def test_get_thumbnail_uncached_is_safe_text(self):
        """Testing TextMimetype.get_thumbnail string type is SafeText
        without cached thumbnail
        """
        thumbnail = self.file_attachment.thumbnail

        self.assertIsInstance(thumbnail, SafeText)

    def test_get_thumbnail_cached_is_safe_text(self):
        """Testing TextMimetype.get_thumbnail string type is SafeText with
        cached thumbnail
        """
        # Django's in-memory cache won't mangle the string types, so we can't
        # rely on just calling thumbnail twice. We have to fake it, so that
        # that we simulate the real-world behavior of getting a raw string
        # back out of a real cache.
        self.spy_on(self.file_attachment.mimetype_handler._generate_thumbnail,
                    call_fake=lambda self: '<div>My thumbnail</div>')

        thumbnail = self.file_attachment.thumbnail

        self.assertIsInstance(thumbnail, SafeText)
