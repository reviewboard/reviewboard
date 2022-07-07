"""Unit tests for the SCMTools registry."""

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError
from djblets.testing.decorators import add_fixtures

from reviewboard.scmtools import scmtools_registry
from reviewboard.scmtools.core import SCMTool
from reviewboard.scmtools.models import Tool
from reviewboard.scmtools.registry import logger
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

    def test_register(self):
        """Testing SCMToolRegistry.register"""
        scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

        with self.assertRaises(AlreadyRegisteredError):
            scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

    def test_register_creates_tools(self):
        """Testing SCMToolRegistry.register creates Tool entries"""
        scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

        tool = Tool.objects.get(name='Dummy')
        self.assertEqual(
            tool.class_name,
            'reviewboard.scmtools.tests.test_registry.DummySCMTool')

    def test_lookup(self):
        """Testing SCMToolRegistry look-up operations"""
        scmtools_registry.register(SCMToolRegistryTests.DummySCMTool)

        self.assertEqual(scmtools_registry.get_by_id('dummy-scmtool'),
                         SCMToolRegistryTests.DummySCMTool)
        self.assertEqual(
            scmtools_registry.get_by_class_name(
                'reviewboard.scmtools.tests.test_registry.DummySCMTool'),
            SCMToolRegistryTests.DummySCMTool)

    @add_fixtures(['test_scmtools'])
    def test_populate_db_with_conflicting_tools(self):
        """Testing SCMToolRegistry.populate_db with conflicting Tool entries"""
        git = Tool.objects.get(name='Git')
        perforce = Tool.objects.get(name='Perforce')

        git.name = 'Git!'
        git.save(update_fields=('name',))

        perforce.class_name = 'reviewboard.scmtools.XXXOtherPerforceTool'
        perforce.save(update_fields=('class_name',))

        with self.assertLogs(logger=logger) as log_ctx:
            scmtools_registry.populate_db()

        self.assertEqual(len(log_ctx.records), 3)
        self.assertEqual(
            log_ctx.records[0].getMessage(),
            "Tool ID %s (name='Git!', "
            "class_name='reviewboard.scmtools.git.GitTool') conflicts with "
            "SCMTool 'git' (name='Git', "
            "class_name='reviewboard.scmtools.git.GitTool')"
            % git.pk)
        self.assertEqual(
            log_ctx.records[1].getMessage(),
            "Tool ID %s (name='Perforce', "
            "class_name='reviewboard.scmtools.XXXOtherPerforceTool') "
            "conflicts with SCMTool 'perforce' (name='Perforce', "
            "class_name='reviewboard.scmtools.perforce.PerforceTool')"
            % perforce.pk)
        self.assertEqual(
            log_ctx.records[2].getMessage(),
            "SCMTool 'reviewboard.scmtools.XXXOtherPerforceTool' in the "
            "scmtools_tool table could not be loaded: Module "
            "\"reviewboard.scmtools\" does not define a "
            "\"XXXOtherPerforceTool\" SCM Tool")
