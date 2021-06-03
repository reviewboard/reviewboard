"""Unit tests for reviewboard.extensions.hooks.WebAPICapabilitiesHook."""

from __future__ import unicode_literals

from djblets.extensions.models import RegisteredExtension

from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import WebAPICapabilitiesHook
from reviewboard.extensions.tests.testcases import ExtensionManagerMixin
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import root_item_mimetype
from reviewboard.webapi.tests.urls import get_root_url


class WebAPICapabilitiesExtension(Extension):
    registration = RegisteredExtension()
    metadata = {
        'Name': 'Web API Capabilities Extension',
    }
    id = 'WebAPICapabilitiesExtension'

    def __init__(self, *args, **kwargs):
        super(WebAPICapabilitiesExtension, self).__init__(*args, **kwargs)


class WebAPICapabilitiesHookTests(ExtensionManagerMixin, BaseWebAPITestCase):
    """Testing WebAPICapabilitiesHook."""

    def setUp(self):
        super(WebAPICapabilitiesHookTests, self).setUp()

        self.extension = WebAPICapabilitiesExtension(
            extension_manager=self.manager)
        self.url = get_root_url()

    def tearDown(self):
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
        self.assertIn('WebAPICapabilitiesExtension', caps)

        extension_caps = caps[self.extension.id]
        self.assertTrue(extension_caps['sandboxed'])
        self.assertTrue(extension_caps['thorough'])

        self.extension.shutdown()

    def test_register_fails_no_id(self):
        """Testing WebAPICapabilitiesHook initializing with ID of None"""
        self.extension.id = None

        self.assertRaisesMessage(
            ValueError,
            'The capabilities_id attribute must not be None',
            WebAPICapabilitiesHook,
            self.extension,
            {
                'sandboxed': True,
                'thorough': True,
            })

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertNotIn('WebAPICapabilitiesExtension', caps)
        self.assertNotIn(None, caps)

        # Note that the hook failed to enable, so there's no need to test
        # shutdown().

    def test_register_fails_default_capability(self):
        """Testing WebAPICapabilitiesHook initializing with default key"""
        self.extension.id = 'diffs'

        self.assertRaisesMessage(
            KeyError,
            '"diffs" is reserved for the default set of capabilities',
            WebAPICapabilitiesHook,
            self.extension,
            {
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

        # Note that the hook failed to enable, so there's no need to test
        # shutdown().

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
        self.assertNotIn('WebAPICapabilitiesExtension', caps)

        self.extension.shutdown()
