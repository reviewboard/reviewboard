from django.db import models

from django_evolution.mutations import (AddField, ChangeField, DeleteField,
                                        RenameField, SQLMutation)
from django_evolution.tests.base_test_case import EvolutionTestCase


class BaseModel(models.Model):
    my_id = models.AutoField(primary_key=True)
    char_field = models.CharField(max_length=20)


class PreprocessingTests(EvolutionTestCase):
    """Testing pre-processing of mutations."""
    sql_mapping_key = 'preprocessing'
    default_base_model = BaseModel

    def test_add_delete_field(self):
        """Testing pre-processing AddField + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='', max_length=20),
                DeleteField('TestModel', 'added_field'),
            ],
            '',
            [],
            'noop',
            expect_noop=True)

    def test_add_delete_add_field(self):
        """Testing pre-processing AddField + DeleteField + AddField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            added_field = models.IntegerField()

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='', max_length=20),
                DeleteField('TestModel', 'added_field'),
                AddField('TestModel', 'added_field', models.IntegerField,
                         initial=42)
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>)",
            ],
            'add_delete_add_field')

    def test_add_delete_add_rename_field(self):
        """Testing pre-processing AddField + DeleteField + AddField +
        RenameField
        """
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            renamed_field = models.IntegerField()

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='', max_length=20),
                DeleteField('TestModel', 'added_field'),
                AddField('TestModel', 'added_field', models.IntegerField,
                         initial=42),
                RenameField('TestModel', 'added_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added"),
            [
                "AddField('TestModel', 'renamed_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>)",
            ],
            'add_delete_add_rename_field')

    def test_add_change_field(self):
        """Testing pre-processing AddField + ChangeField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            added_field = models.CharField(max_length=50, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                ChangeField('TestModel', 'added_field', null=True,
                            initial='bar', max_length=50),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.CharField,"
                " max_length=50, null=True)",
            ],
            'add_change_field')

    def test_add_change_change_field(self):
        """Testing pre-processing AddField + ChangeField + ChangeField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            added_field = models.CharField(max_length=50, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                ChangeField('TestModel', 'added_field', null=True,
                            initial='bar', max_length=30),
                ChangeField('TestModel', 'added_field',
                            initial='bar', max_length=50),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.CharField,"
                " max_length=50, null=True)",
            ],
            'add_change_field')

    def test_add_change_delete_field(self):
        """Testing pre-processing AddField + ChangeField + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                ChangeField('TestModel', 'added_field', null=True),
                DeleteField('TestModel', 'added_field'),
            ],
            '',
            [],
            'noop',
            expect_noop=True)

    def test_add_change_rename_field(self):
        """Testing pre-processing AddField + ChangeField + RenameField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            renamed_field = models.CharField(max_length=50, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                ChangeField('TestModel', 'added_field', null=True,
                            initial='bar', max_length=50),
                RenameField('TestModel', 'added_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " max_length=50, null=True)",
            ],
            'add_change_rename_field')

    def test_add_rename_change_field(self):
        """Testing pre-processing AddField + RenameField + ChangeField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            renamed_field = models.CharField(max_length=50, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                RenameField('TestModel', 'added_field', 'renamed_field'),
                ChangeField('TestModel', 'renamed_field', null=True,
                            initial='bar', max_length=50),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " max_length=50, null=True)",
            ],
            'add_rename_change_field')

    def test_add_rename_change_rename_change_field(self):
        """Testing pre-processing AddField + RenameField + ChangeField +
        RenameField + ChangeField
        """
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            renamed_field = models.CharField(max_length=50, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                RenameField('TestModel', 'added_field', 'foo_field'),
                ChangeField('TestModel', 'foo_field', null=True),
                RenameField('TestModel', 'foo_field', 'renamed_field'),
                ChangeField('TestModel', 'renamed_field', max_length=50),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " max_length=50, null=True)",
            ],
            'add_rename_change_rename_change_field')

    def test_add_rename_delete(self):
        """Testing pre-processing AddField + RenameField + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                RenameField('TestModel', 'added_field', 'renamed_field'),
                DeleteField('TestModel', 'renamed_field'),
            ],
            '',
            [],
            'noop',
            expect_noop=True)

    def test_add_sql_delete(self):
        """Testing pre-processing AddField + SQLMutation + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='foo', max_length=20),
                SQLMutation('dummy-sql',
                            ['-- Comment --'],
                            lambda app_label, proj_sig: None),
                DeleteField('TestModel', 'added_field'),
            ],
            '',
            [
                "DeleteField('TestModel', 'char_field')",
            ],
            'add_sql_delete',
            expect_noop=True)

    def test_change_delete_field(self):
        """Testing pre-processing ChangeField + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)

        self.perform_evolution_tests(
            DestModel,
            [
                ChangeField('TestModel', 'char_field', null=True),
                DeleteField('TestModel', 'char_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'char_field' has been deleted"),
            [
                "DeleteField('TestModel', 'char_field')",
            ],
            'delete_char_field')

    def test_change_rename_field(self):
        """Testing pre-processing ChangeField + RenameField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            renamed_field = models.CharField(max_length=20, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                ChangeField('TestModel', 'char_field', null=True),
                RenameField('TestModel', 'char_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'char_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " max_length=20, null=True)",

                "DeleteField('TestModel', 'char_field')",
            ],
            'change_rename_field')

    def test_change_rename_change_rename_field(self):
        """Testing pre-processing ChangeField + RenameField + ChangeField +
        RenameField
        """
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            renamed_field = models.CharField(max_length=30, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                ChangeField('TestModel', 'char_field', max_length=30),
                RenameField('TestModel', 'char_field', 'foo_field'),
                ChangeField('TestModel', 'foo_field', null=True),
                RenameField('TestModel', 'foo_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'char_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " max_length=30, null=True)",

                "DeleteField('TestModel', 'char_field')",
            ],
            'change_rename_change_rename_field')

    def test_change_rename_delete_field(self):
        """Testing pre-processing ChangeField + RenameField + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)

        self.perform_evolution_tests(
            DestModel,
            [
                ChangeField('TestModel', 'char_field', null=True),
                RenameField('TestModel', 'char_field', 'renamed_field'),
                DeleteField('TestModel', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'char_field' has been deleted"),
            [
                "DeleteField('TestModel', 'char_field')",
            ],
            'delete_char_field')

    def test_rename_add_field(self):
        """Testing pre-processing RenameField + AddField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            renamed_field = models.CharField(max_length=20)
            char_field = models.CharField(max_length=50, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'char_field', 'renamed_field'),
                AddField('TestModel', 'char_field', models.CharField,
                         max_length=50, null=True),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    In field 'char_field':\n"
             "        Property 'max_length' has changed\n"
             "        Property 'null' has changed"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " initial=<<USER VALUE REQUIRED>>, max_length=20)",

                "ChangeField('TestModel', 'char_field', initial=None,"
                " max_length=50, null=True)",
            ],
            'rename_add_field')

    def test_rename_delete_field(self):
        """Testing pre-processing RenameField + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'char_field', 'renamed_field'),
                DeleteField('TestModel', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'char_field' has been deleted"),
            [
                "DeleteField('TestModel', 'char_field')",
            ],
            'delete_char_field')

    def test_rename_change_delete_field(self):
        """Testing pre-processing RenameField + ChangeField + DeleteField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'char_field', 'renamed_field'),
                ChangeField('TestModel', 'renamed_field', null=True),
                DeleteField('TestModel', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'char_field' has been deleted"),
            [
                "DeleteField('TestModel', 'char_field')",
            ],
            'delete_char_field')

    def test_rename_change_rename_change_field(self):
        """Testing pre-processing RenameField + ChangeField + RenameField +
        ChangeField
        """
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            renamed_field = models.CharField(max_length=50, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'char_field', 'foo_field'),
                ChangeField('TestModel', 'foo_field', max_length=30,
                            null=True),
                RenameField('TestModel', 'foo_field', 'renamed_field'),
                ChangeField('TestModel', 'renamed_field', max_length=50),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'char_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " max_length=50, null=True)",

                "DeleteField('TestModel', 'char_field')",
            ],
            'rename_change_rename_change_field')

    def test_rename_rename_field(self):
        """Testing pre-processing RenameField + RenameField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            renamed_field = models.CharField(max_length=20)

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'char_field', 'foo_field'),
                RenameField('TestModel', 'foo_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'char_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.CharField,"
                " initial=<<USER VALUE REQUIRED>>, max_length=20)",

                "DeleteField('TestModel', 'char_field')",
            ],
            'rename_rename_field')
