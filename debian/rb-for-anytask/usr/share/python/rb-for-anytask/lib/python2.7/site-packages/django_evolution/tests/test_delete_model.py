from django.db import models

from django_evolution.mutations import DeleteModel
from django_evolution.tests.base_test_case import EvolutionTestCase


class DeleteModelAnchor(models.Model):
    value = models.IntegerField()


class DeleteModelTests(EvolutionTestCase):
    """Testing DeleteModel mutations."""
    sql_mapping_key = 'delete_model'

    def test_delete_model(self):
        """Testing DeleteModel"""
        class BasicModel(models.Model):
            value = models.IntegerField()

        self.set_base_model(BasicModel, 'BasicModel')

        end_sig = self.copy_sig(self.start_sig)
        end = self.copy_models(self.start)

        end_sig['tests'].pop('BasicModel')
        end.pop('basicmodel')

        self.perform_evolution_tests(
            None,
            [
                DeleteModel('BasicModel'),
            ],
            'The model tests.BasicModel has been deleted',
            [
                "DeleteModel('BasicModel')",
            ],
            'BasicModel',
            end_sig=end_sig,
            end=end)

    def test_delete_model_with_m2m_field(self):
        """Testing DeleteModel with a model containing a ManyToManyField"""
        class BasicWithM2MModel(models.Model):
            value = models.IntegerField()
            m2m = models.ManyToManyField(DeleteModelAnchor)

        self.set_base_model(
            BasicWithM2MModel,
            name='BasicWithM2MModel',
            extra_models=[('DeleteModelAnchor', DeleteModelAnchor)])

        end_sig = self.copy_sig(self.start_sig)
        end = self.copy_models(self.start)

        end_sig['tests'].pop('BasicWithM2MModel')
        end.pop('basicwithm2mmodel')

        self.perform_evolution_tests(
            None,
            [
                DeleteModel('BasicWithM2MModel'),
            ],
            'The model tests.BasicWithM2MModel has been deleted',
            [
                "DeleteModel('BasicWithM2MModel')",
            ],
            'BasicWithM2MModel',
            end_sig=end_sig,
            end=end)

    def test_delete_model_with_custom_table(self):
        """Testing DeleteModel with a model and custom table name"""
        class CustomTableModel(models.Model):
            value = models.IntegerField()

            class Meta:
                db_table = 'custom_table_name'

        self.set_base_model(CustomTableModel, 'CustomTableModel')

        end_sig = self.copy_sig(self.start_sig)
        end = self.copy_models(self.start)

        end_sig['tests'].pop('CustomTableModel')
        end.pop('customtablemodel')

        self.perform_evolution_tests(
            None,
            [
                DeleteModel('CustomTableModel'),
            ],
            'The model tests.CustomTableModel has been deleted',
            [
                "DeleteModel('CustomTableModel')",
            ],
            'CustomTableModel',
            end_sig=end_sig,
            end=end)

    def test_delete_model_with_custom_table_and_m2m_field(self):
        """Testing DeleteModel with a model and custom table name and
        ManyToManyField
        """
        class CustomTableWithM2MModel(models.Model):
            value = models.IntegerField()
            m2m = models.ManyToManyField(DeleteModelAnchor)

            class Meta:
                db_table = 'another_custom_table_name'

        self.set_base_model(
            CustomTableWithM2MModel,
            name='CustomTableWithM2MModel',
            extra_models=[('DeleteModelAnchor', DeleteModelAnchor)])

        end_sig = self.copy_sig(self.start_sig)
        end = self.copy_models(self.start)

        end_sig['tests'].pop('CustomTableWithM2MModel')
        end.pop('customtablewithm2mmodel')

        self.perform_evolution_tests(
            None,
            [
                DeleteModel('CustomTableWithM2MModel'),
            ],
            'The model tests.CustomTableWithM2MModel has been deleted',
            [
                "DeleteModel('CustomTableWithM2MModel')",
            ],
            'CustomTableWithM2MModel',
            end_sig=end_sig,
            end=end)

    def test_delete_model_with_custom_database(self):
        """Testing DeleteModel with custom database"""
        class BasicModel(models.Model):
            value = models.IntegerField()

        self.set_base_model(BasicModel, 'BasicModel', db_name='db_multi')

        end_sig = self.copy_sig(self.start_sig)
        end = self.copy_models(self.start)

        end_sig['tests'].pop('BasicModel')
        end.pop('basicmodel')

        self.perform_evolution_tests(
            None,
            [
                DeleteModel('BasicModel'),
            ],
            'The model tests.BasicModel has been deleted',
            [
                "DeleteModel('BasicModel')",
            ],
            'BasicModel',
            end_sig=end_sig,
            end=end,
            db_name='db_multi')
