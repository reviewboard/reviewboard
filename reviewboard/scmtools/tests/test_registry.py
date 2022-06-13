"""Unit tests for the SCMTools registry."""

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError

from reviewboard.scmtools import scmtools_registry
from reviewboard.scmtools.core import SCMTool
from reviewboard.scmtools.models import Tool
from reviewboard.testing import TestCase


class SCMToolRegistryTests(TestCase):
    """Unit tests for the SCMTools registry."""

    class DummySCMTool(SCMTool):
        name = 'Dummy'
        scmtool_id = 'dummy-scmtool'

    def tearDown(self):
        """Tear down the test suite."""
        super(SCMToolRegistryTests, self).tearDown()

        try:
            scmtools_registry.unregister_by_attr('scmtool_id', 'dummy-scmtool')
        except ItemLookupError:
            pass

    def test_registration(self):
        """Testing SCMTool registration."""
        scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

        with self.assertRaises(AlreadyRegisteredError):
            scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

    def test_tool_creation(self):
        """Testing creation of Tool entry during registration."""
        scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

        tool = Tool.objects.get(name='Dummy')
        self.assertEqual(
            tool.class_name,
            'reviewboard.scmtools.tests.test_registry.DummySCMTool')

    def test_lookup(self):
        """Testing SCMTool registry look-up operations."""
        scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

        self.assertEqual(scmtools_registry.get_by_id('dummy-scmtool'),
                         SCMToolRegistryTests.DummySCMTool)
        self.assertEqual(
            scmtools_registry.get_by_class_name(
                'reviewboard.scmtools.tests.test_registry.DummySCMTool'),
            SCMToolRegistryTests.DummySCMTool)
