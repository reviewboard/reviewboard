from django.db import models

from django_evolution.errors import CannotSimulate
from django_evolution.mutations import SQLMutation
from django_evolution.tests.base_test_case import EvolutionTestCase


class SQLBaseModel(models.Model):
    char_field = models.CharField(max_length=20)
    int_field = models.IntegerField()


class AddFieldsModel(models.Model):
    char_field = models.CharField(max_length=20)
    int_field = models.IntegerField()
    added_field1 = models.IntegerField(null=True)
    added_field2 = models.IntegerField(null=True)
    added_field3 = models.IntegerField(null=True)


class OrderingTests(EvolutionTestCase):
    """Testing ordering of operations."""
    sql_mapping_key = 'sql_mutation'
    default_base_model = SQLBaseModel

    def test_add_fields_cannot_simulate(self):
        """Testing SQLMutation and adding fields cannot be simulated"""
        self.assertRaisesMessage(
            CannotSimulate,
            'Cannot simulate SQLMutations',
            lambda: self.perform_evolution_tests(
                AddFieldsModel,
                [
                    SQLMutation('first-two-fields', [
                        'ALTER TABLE "tests_testmodel" ADD COLUMN'
                        ' "added_field1" integer NULL;',

                        'ALTER TABLE "tests_testmodel" ADD COLUMN'
                        ' "added_field2" integer NULL;'
                    ]),
                    SQLMutation('third-field', [
                        'ALTER TABLE "tests_testmodel" ADD COLUMN'
                        ' "added_field3" integer NULL;',
                    ])
                ],
                ("In model tests.TestModel:\n"
                 "    Field 'added_field1' has been added\n"
                 "    Field 'added_field3' has been added\n"
                 "    Field 'added_field2' has been added"),
                perform_mutations=False))

    def test_add_fields_simulation_functions(self):
        """Testing SQLMutation and adding fields with simulation functions"""
        def update_first_two(app_label, proj_sig):
            app_sig = proj_sig[app_label]
            model_sig = app_sig['TestModel']
            model_sig['fields']['added_field1'] = {
                'field_type': models.IntegerField,
                'null': True
            }
            model_sig['fields']['added_field2'] = {
                'field_type': models.IntegerField,
                'null': True
            }

        def update_third(app_label, proj_sig):
            app_sig = proj_sig[app_label]
            model_sig = app_sig['TestModel']
            model_sig['fields']['added_field3'] = {
                'field_type': models.IntegerField,
                'null': True
            }

        self.perform_evolution_tests(
            AddFieldsModel,
            [
                SQLMutation(
                    'first-two-fields',
                    self.get_sql_mapping('AddFirstTwoFields').split('\n'),
                    update_first_two),
                SQLMutation(
                    'third-field',
                    self.get_sql_mapping('AddThirdField').split('\n'),
                    update_third),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field1' has been added\n"
             "    Field 'added_field3' has been added\n"
             "    Field 'added_field2' has been added"),
            sql_name='SQLMutationOutput')
