"""Unit tests for reviewboard.extensions.hooks.SCMToolHook."""

from reviewboard.extensions.hooks import SCMToolHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.scmtools import scmtools_registry
from reviewboard.scmtools.core import SCMTool


class TestSCMTool(SCMTool):
    name = 'Dummy'
    scmtool_id = 'dummy-scmtool'


class TestSCMToolNoID(SCMTool):
    name = 'Dummy'
    scmtool_id = None


class SCMToolHookTests(BaseExtensionHookTestCase):
    """Testing SCMToolHook."""

    def test_register(self):
        """Testing SCMToolHook initializing"""
        hook = SCMToolHook(self.extension, TestSCMTool)

        self.assertIs(scmtools_registry.get_by_id('dummy-scmtool'),
                      TestSCMTool)

        hook.disable_hook()

    def test_register_without_scmtool_id(self):
        """Testing SCMToolHook initializing without scmtool_id"""
        message = 'TestSCMToolNoID.scmtool_id must be set.'

        with self.assertRaisesMessage(ValueError, message):
            SCMToolHook(self.extension, TestSCMToolNoID)

    def test_unregister(self):
        """Testing SCMToolHook uninitializing"""
        hook = SCMToolHook(self.extension, TestSCMTool)
        hook.disable_hook()

        self.assertIsNone(scmtools_registry.get_by_id('dummy-scmtool'))
