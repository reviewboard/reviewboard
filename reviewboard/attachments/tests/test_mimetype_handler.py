"""Unit tests for reviewboard.attachments.mimetypes.MimetypeHandler.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

import kgb
import mimeparse

from django.contrib.auth.models import User

from reviewboard.attachments.mimetypes import (MimetypeHandler,
                                               register_mimetype_handler,
                                               score_match,
                                               unregister_mimetype_handler)
from reviewboard.attachments.tests.base import BaseFileAttachmentTestCase
from reviewboard.testing import TestCase


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


class MimetypeHandlerTests(TestCase):
    """Unit tests for reviewboard.attachments.mimetypes.MimetypeHandler.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

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

    def test_mimetype_match_scoring(self):
        """Testing score_match for different mimetype patterns"""
        def assert_score(pattern, test, score):
            self.assertAlmostEqual(
                score_match(mimeparse.parse_mime_type(pattern),
                            mimeparse.parse_mime_type(test)),
                score)

        assert_score('application/reviewboard+x-pdf',
                     'application/reviewboard+x-pdf', 2.0)
        assert_score('application/x-pdf', 'application/x-pdf', 1.9)
        assert_score('text/*', 'text/plain', 1.8)
        assert_score('*/reviewboard+plain', 'text/reviewboard+plain', 1.7)
        assert_score('*/plain', 'text/plain', 1.6)
        assert_score('application/x-javascript', 'application/x-pdf', 0)


class SandboxTests(kgb.SpyAgency, BaseFileAttachmentTestCase):
    """Unit tests for MimetypeHandler sandboxing.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    def setUp(self):
        """Set up this test case."""
        super(SandboxTests, self).setUp()

        register_mimetype_handler(SandboxMimetypeHandler)

        user = User.objects.create_user(username='reviewboard',
                                        password='password',
                                        email='reviewboard@example.com')

        review_request = self.create_review_request(submitter=user)
        self.file_attachment = self.create_file_attachment(
            review_request=review_request)

    def tearDown(self):
        """Tear down this test case."""
        super(SandboxTests, self).tearDown()

        unregister_mimetype_handler(SandboxMimetypeHandler)

    def test_get_thumbnail(self):
        """Testing FileAttachment sandboxes MimetypeHandler.get_thumbnail"""
        self.spy_on(SandboxMimetypeHandler.get_thumbnail,
                    owner=SandboxMimetypeHandler)

        self.file_attachment.thumbnail
        self.assertTrue(SandboxMimetypeHandler.get_thumbnail.called)

    def test_set_thumbnail(self):
        """Testing FileAttachment sandboxes MimetypeHandler.set_thumbnail"""
        self.spy_on(SandboxMimetypeHandler.set_thumbnail,
                    owner=SandboxMimetypeHandler)

        self.file_attachment.thumbnail = None
        self.assertTrue(SandboxMimetypeHandler.set_thumbnail.called)

    def test_get_icon_url(self):
        """Testing FileAttachment sandboxes MimetypeHandler.get_icon_url"""
        self.spy_on(SandboxMimetypeHandler.get_icon_url,
                    owner=SandboxMimetypeHandler)

        self.file_attachment.icon_url
        self.assertTrue(SandboxMimetypeHandler.get_icon_url.called)
