"""Unit tests for the SCMTools registry."""

from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError
from djblets.testing.decorators import add_fixtures

from reviewboard.scmtools import scmtools_registry
from reviewboard.scmtools.core import SCMTool
from reviewboard.scmtools.models import Tool
from reviewboard.scmtools.registry import logger
from reviewboard.testing import TestCase


class DummySCMTool(SCMTool):
    name = 'Dummy'
    scmtool_id = 'dummy-scmtool'


class DummySCMToolWithLookupName(SCMTool):
    name = 'New Dummy'
    lookup_name = 'Old Dummy'
    scmtool_id = 'lookup-dummy-scmtool'


class SCMToolRegistryTests(TestCase):
    """Unit tests for the SCMTools registry."""

    def tearDown(self):
        """Tear down the test suite."""
        super().tearDown()

        for scmtool_id in ('dummy-scmtool', 'lookup-dummy-scmtool'):
            try:
                scmtools_registry.unregister_by_attr('scmtool_id', scmtool_id)
            except ItemLookupError:
                pass

    def test_register(self):
        """Testing SCMToolRegistry.register"""
        scmtools_registry.register(DummySCMTool)

        with self.assertRaises(AlreadyRegisteredError):
            scmtools_registry.register(DummySCMTool)

    def test_register_creates_tools(self):
        """Testing SCMToolRegistry.register creates Tool entries"""
        scmtools_registry.register(DummySCMTool)

        tool = Tool.objects.get(name='Dummy')
        self.assertEqual(
            tool.class_name,
            'reviewboard.scmtools.tests.test_registry.DummySCMTool')

    def test_register_with_lookup_name(self):
        """Testing SCMToolRegistry.register creates Tool entries with Legacy DB
        name
        """
        scmtools_registry.register(DummySCMToolWithLookupName)

        tool = Tool.objects.get(name='Old Dummy')
        self.assertEqual(
            tool.class_name,
            'reviewboard.scmtools.tests.test_registry.'
            'DummySCMToolWithLookupName')

        self.assertFalse(Tool.objects.filter(name='New Dummy').exists())

    def test_lookup(self):
        """Testing SCMToolRegistry look-up operations"""
        scmtools_registry.register(DummySCMTool)

        self.assertIs(scmtools_registry.get_by_id('dummy-scmtool'),
                      DummySCMTool)
        self.assertIs(scmtools_registry.get_by_name('Dummy'),
                      DummySCMTool)
        self.assertIs(
            scmtools_registry.get_by_class_name(
                'reviewboard.scmtools.tests.test_registry.DummySCMTool'),
            DummySCMTool)

    def test_lookup_with_lookup_name(self):
        """Testing SCMToolRegistry look-up operations with
        SCMTool.lookup_name
        """
        scmtools_registry.register(DummySCMToolWithLookupName)

        self.assertIs(
            scmtools_registry.get_by_id('lookup-dummy-scmtool'),
            DummySCMToolWithLookupName)
        self.assertIs(
            scmtools_registry.get_by_name('Old Dummy'),
            DummySCMToolWithLookupName)
        self.assertIsNone(scmtools_registry.get_by_name('New Dummy'))
        self.assertIs(
            scmtools_registry.get_by_class_name(
                'reviewboard.scmtools.tests.test_registry.'
                'DummySCMToolWithLookupName'),
            DummySCMToolWithLookupName)

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

        self.assertEqual(len(log_ctx.records), 2)
        self.assertEqual(
            log_ctx.records[0].getMessage(),
            "Tool ID %s (name='Git!', "
            "class_name='reviewboard.scmtools.git.GitTool') conflicts with "
            "SCMTool 'git' (lookup_name='Git', "
            "class_name='reviewboard.scmtools.git.GitTool')"
            % git.pk)
        self.assertEqual(
            log_ctx.records[1].getMessage(),
            "Tool ID %s (name='Perforce', "
            "class_name='reviewboard.scmtools.XXXOtherPerforceTool') "
            "conflicts with SCMTool 'perforce' (lookup_name='Perforce', "
            "class_name='reviewboard.scmtools.perforce.PerforceTool')"
            % perforce.pk)
