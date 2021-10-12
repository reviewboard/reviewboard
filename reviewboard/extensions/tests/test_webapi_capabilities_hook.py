"""Unit tests for reviewboard.extensions.hooks.WebAPICapabilitiesHook."""

from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import WebAPICapabilitiesHook
from reviewboard.extensions.tests.testcases import ExtensionHookTestCaseMixin
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import root_item_mimetype
from reviewboard.webapi.tests.urls import get_root_url


class WebAPICapabilitiesExtension(Extension):
    metadata = {
        'Name': 'Web API Capabilities Extension',
    }


class WebAPICapabilitiesHookTests(ExtensionHookTestCaseMixin,
                                  BaseWebAPITestCase):
    """Testing WebAPICapabilitiesHook."""

    extension_class = WebAPICapabilitiesExtension

    def setUp(self):
        super(WebAPICapabilitiesHookTests, self).setUp()

        self.old_extension_id = self.extension.id
        self.url = get_root_url()

    def tearDown(self):
        self.extension.id = self.old_extension_id

        super(WebAPICapabilitiesHookTests, self).tearDown()

    def test_register(self):
        """Testing WebAPICapabilitiesHook initializing"""
        WebAPICapabilitiesHook(
            extension=self.extension,
            caps={
                'sandboxed': True,
                'thorough': True,
            })

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertIn(self.extension.id, caps)

        extension_caps = caps[self.extension.id]
        self.assertTrue(extension_caps['sandboxed'])
        self.assertTrue(extension_caps['thorough'])

    def test_register_fails_no_id(self):
        """Testing WebAPICapabilitiesHook initializing with ID of None"""
        self.extension.id = None

        expected_message = \
            'The capabilities_id attribute must not be None'

        with self.assertRaisesMessage(ValueError, expected_message):
            WebAPICapabilitiesHook(self.extension, {
                'sandboxed': True,
                'thorough': True,
            })

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertNotIn(self.extension.id, caps)
        self.assertNotIn(None, caps)

    def test_register_fails_default_capability(self):
        """Testing WebAPICapabilitiesHook initializing with default key"""
        self.extension.id = 'diffs'

        expected_message = \
            '"diffs" is reserved for the default set of capabilities'

        with self.assertRaisesMessage(KeyError, expected_message):
            WebAPICapabilitiesHook(self.extension, {
                'base_commit_ids': False,
                'moved_files': False,
            })

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertIn('diffs', caps)

        diffs_caps = caps['diffs']
        self.assertTrue(diffs_caps['base_commit_ids'])
        self.assertTrue(diffs_caps['moved_files'])

    def test_unregister(self):
        """Testing WebAPICapabilitiesHook uninitializing"""
        hook = WebAPICapabilitiesHook(
            extension=self.extension,
            caps={
                'sandboxed': True,
                'thorough': True,
            })

        hook.disable_hook()

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertNotIn(self.extension.id, caps)
