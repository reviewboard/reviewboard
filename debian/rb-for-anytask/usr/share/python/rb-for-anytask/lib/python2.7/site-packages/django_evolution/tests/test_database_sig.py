from django.test.testcases import TestCase

from django_evolution.db import EvolutionOperationsMulti
from django_evolution.models import Evolution
from django_evolution.signature import create_database_sig


class DatabaseSigTests(TestCase):
    """Testing database signatures."""
    def setUp(self):
        self.database_sig = create_database_sig('default')
        self.evolver = EvolutionOperationsMulti('default').get_evolver()

    def test_initial_state(self):
        """Testing initial state of database_sig"""
        tables = self.database_sig.keys()

        # Check that a few known tables are in the list, to make sure
        # the scan worked.
        self.assertTrue('auth_permission' in tables)
        self.assertTrue('auth_user' in tables)
        self.assertTrue('django_evolution' in tables)
        self.assertTrue('django_project_version' in tables)

        self.assertTrue('indexes' in self.database_sig['django_evolution'])

        # Check the Evolution model
        index_name = self.evolver.get_default_index_name(
            Evolution._meta.db_table, Evolution._meta.get_field('version'))
        indexes = self.database_sig['django_evolution']['indexes']

        self.assertTrue(index_name in indexes)
        self.assertEqual(
            indexes[index_name],
            {
                'unique': False,
                'columns': ['version_id'],
            })
