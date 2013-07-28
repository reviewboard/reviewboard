import mimeparse
import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.mimetypes import MimetypeHandler, \
                                              register_mimetype_handler, \
                                              unregister_mimetype_handler
from reviewboard.reviews.models import ReviewRequest


class FileAttachmentTests(TestCase):
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def test_upload_file(self):
        """Testing uploading a file attachment."""
        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'trophy.png')
        f = open(filename, 'r')
        file = SimpleUploadedFile(f.name, f.read(), content_type='image/png')
        f.close()

        form = UploadFileForm(files={
            'path': file,
        })
        form.is_valid()
        print form.errors
        self.assertTrue(form.is_valid())

        review_request = ReviewRequest.objects.get(pk=1)
        file_attachment = form.create(file, review_request)
        self.assertTrue(os.path.basename(file_attachment.file.name).endswith(
            '__trophy.png'))
        self.assertEqual(file_attachment.mimetype, 'image/png')


class MimetypeTest(MimetypeHandler):
    supported_mimetypes = ['test/*']


class TestAbcMimetype(MimetypeHandler):
    supported_mimetypes = ['test/abc']


class TestXmlMimetype(MimetypeHandler):
    supported_mimetypes = ['test/xml']


class Test2AbcXmlMimetype(MimetypeHandler):
    supported_mimetypes = ['test2/abc+xml']


class StarDefMimetype(MimetypeHandler):
    supported_mimetypes = ['*/def']


class StarAbcDefMimetype(MimetypeHandler):
    supported_mimetypes = ['*/abc+def']


class Test3XmlMimetype(MimetypeHandler):
    supported_mimetypes = ['test3/xml']


class Test3AbcXmlMimetype(MimetypeHandler):
    supported_mimetypes = ['test3/abc+xml']


class Test3StarMimetype(MimetypeHandler):
    supported_mimetypes = ['test3/*']


class MimetypeHandlerTests(TestCase):
    def setUp(self):
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
        """Testing matching of factory method for mimetype handlers."""
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
        """Testing precedence of factory method for mimetype handlers."""
        self.assertEqual(self._handler_for("test2/def"), StarDefMimetype)
        self.assertEqual(self._handler_for("test3/abc+xml"),
                         Test3AbcXmlMimetype)
        self.assertEqual(self._handler_for("test3/xml"), Test3XmlMimetype)
        self.assertEqual(self._handler_for("foo/abc+def"), StarAbcDefMimetype)
        self.assertEqual(self._handler_for("foo/def"), StarDefMimetype)
        # Left match and Wildcard should trump Left Wildcard and match
        self.assertEqual(self._handler_for("test/def"), MimetypeTest)
