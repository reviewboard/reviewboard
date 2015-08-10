from django.db import models

from django_evolution.mutations import RenameModel
from django_evolution.tests.base_test_case import EvolutionTestCase


class RenameModelBaseModel(models.Model):
    char_field = models.CharField(max_length=20)
    int_field = models.IntegerField()


class RenameModelTests(EvolutionTestCase):
    """Unit tests for RenameModel mutations."""
    sql_mapping_key = 'rename_model'
    default_base_model = RenameModelBaseModel

    def test_rename(self):
        """Testing RenameModel with changed db_table"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()

        self.perform_evolution_tests(
            DestModel,
            [
                RenameModel('TestModel', 'DestModel',
                            db_table='tests_destmodel'),
            ],
            "The model tests.TestModel has been deleted",
            [
                "DeleteModel('TestModel')",
            ],
            'RenameModel',
            model_name='DestModel')

    def test_rename_unchanged_db_table(self):
        """Testing RenameModel with unchanged db_table"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()

            class Meta:
                db_table = 'tests_testmodel'

        self.perform_evolution_tests(
            DestModel,
            [
                RenameModel('TestModel', 'DestModel',
                            db_table='tests_testmodel'),
            ],
            "The model tests.TestModel has been deleted",
            [
                "DeleteModel('TestModel')",
            ],
            'RenameModelSameTable',
            model_name='DestModel')

    def test_rename_updates_foreign_key_refs(self):
        """Testing RenameModel updates ForeignKey references in signature"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()

        class RefModel(models.Model):
            my_ref = models.ForeignKey(RenameModelBaseModel)

        self.set_base_model(self.default_base_model,
                            pre_extra_models=[('RefModel', RefModel)])

        end, end_sig = self.make_end_signatures(DestModel, 'DestModel')
        end_sig['tests']['RefModel']['fields']['my_ref']['related_model'] = \
            'tests.DestModel'

        self.perform_evolution_tests(
            DestModel,
            [
                RenameModel('TestModel', 'DestModel',
                            db_table='tests_destmodel'),
            ],
            ("The model tests.TestModel has been deleted\n"
             "In model tests.RefModel:\n"
             "    In field 'my_ref':\n"
             "        Property 'related_model' has changed"),
            [
                "ChangeField('RefModel', 'my_ref', initial=None,"
                " related_model='tests.DestModel')",
                "DeleteModel('TestModel')",
            ],
            'RenameModelForeignKeys',
            end=end,
            end_sig=end_sig)

    def test_rename_updates_foreign_key_refs_unchanged_db_table(self):
        """Testing RenameModel updates ForeignKey references in signature
        and unchanged db_table
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()

            class Meta:
                db_table = 'tests_testmodel'

        class RefModel(models.Model):
            my_ref = models.ForeignKey(RenameModelBaseModel)

        self.set_base_model(self.default_base_model,
                            pre_extra_models=[('RefModel', RefModel)])

        end, end_sig = self.make_end_signatures(DestModel, 'DestModel')
        end_sig['tests']['RefModel']['fields']['my_ref']['related_model'] = \
            'tests.DestModel'

        self.perform_evolution_tests(
            DestModel,
            [
                RenameModel('TestModel', 'DestModel',
                            db_table='tests_testmodel'),
            ],
            ("The model tests.TestModel has been deleted\n"
             "In model tests.RefModel:\n"
             "    In field 'my_ref':\n"
             "        Property 'related_model' has changed"),
            [
                "ChangeField('RefModel', 'my_ref', initial=None,"
                " related_model='tests.DestModel')",
                "DeleteModel('TestModel')",
            ],
            'RenameModelForeignKeysSameTable',
            end=end,
            end_sig=end_sig)

    def test_rename_updates_m2m_refs(self):
        """Testing RenameModel updates ManyToManyField references in
        signature and changed db_table
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()

        class RefModel(models.Model):
            my_ref = models.ManyToManyField(RenameModelBaseModel)

        self.set_base_model(self.default_base_model,
                            pre_extra_models=[('RefModel', RefModel)])

        end, end_sig = self.make_end_signatures(DestModel, 'DestModel')
        end_sig['tests']['RefModel']['fields']['my_ref']['related_model'] = \
            'tests.DestModel'

        self.perform_evolution_tests(
            DestModel,
            [
                RenameModel('TestModel', 'DestModel',
                            db_table='tests_destmodel'),
            ],
            ("The model tests.TestModel has been deleted\n"
             "In model tests.RefModel:\n"
             "    In field 'my_ref':\n"
             "        Property 'related_model' has changed"),
            [
                "ChangeField('RefModel', 'my_ref', initial=None,"
                " related_model='tests.DestModel')",
                "DeleteModel('TestModel')",
            ],
            'RenameModelManyToManyField',
            end=end,
            end_sig=end_sig)

    def test_rename_updates_m2m_refs_unchanged_db_table(self):
        """Testing RenameModel updates ManyToManyField references in
        signature and unchanged db_table
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()

            class Meta:
                db_table = 'tests_testmodel'

        class RefModel(models.Model):
            my_ref = models.ManyToManyField(RenameModelBaseModel)

        self.set_base_model(self.default_base_model,
                            pre_extra_models=[('RefModel', RefModel)])

        end, end_sig = self.make_end_signatures(DestModel, 'DestModel')
        end_sig['tests']['RefModel']['fields']['my_ref']['related_model'] = \
            'tests.DestModel'

        self.perform_evolution_tests(
            DestModel,
            [
                RenameModel('TestModel', 'DestModel',
                            db_table='tests_testmodel'),
            ],
            ("The model tests.TestModel has been deleted\n"
             "In model tests.RefModel:\n"
             "    In field 'my_ref':\n"
             "        Property 'related_model' has changed"),
            [
                "ChangeField('RefModel', 'my_ref', initial=None,"
                " related_model='tests.DestModel')",
                "DeleteModel('TestModel')",
            ],
            'RenameModelManyToManyFieldSameTable',
            end=end,
            end_sig=end_sig)
