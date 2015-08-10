from datetime import datetime

from django.db import connection, models

from django_evolution.errors import EvolutionException, SimulationFailure
from django_evolution.mutations import AddField, DeleteField
from django_evolution.tests.base_test_case import EvolutionTestCase
from django_evolution.tests.utils import has_index_with_columns


class AddSequenceFieldInitial(object):
    def __init__(self, suffix):
        self.suffix = suffix

    def __call__(self):
        return connection.ops.quote_name('int_field')


class AddAnchor1(models.Model):
    value = models.IntegerField()


class AddAnchor2(models.Model):
    value = models.IntegerField()

    class Meta:
        db_table = 'custom_add_anchor_table'


class AddBaseModel(models.Model):
    char_field = models.CharField(max_length=20)
    int_field = models.IntegerField()


class CustomTableModel(models.Model):
    value = models.IntegerField()
    alt_value = models.CharField(max_length=20)

    class Meta:
        db_table = 'custom_table_name'


class AddFieldTests(EvolutionTestCase):
    """Testing AddField mutations."""
    sql_mapping_key = 'add_field'
    default_base_model = AddBaseModel
    default_extra_models = [
        ('AddAnchor1', AddAnchor1),
        ('AddAnchor2', AddAnchor2),
    ]

    DIFF_TEXT = (
        "In model tests.TestModel:\n"
        "    Field 'added_field' has been added"
    )

    def test_add_non_null_column_no_initial_hinted_raises_exception(self):
        """Testing AddField with non-NULL column, no initial value and
        hinted mutation raises EvolutionException"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField()

        self.assertRaisesMessage(
            EvolutionException,
            ("Cannot use hinted evolution: AddField or ChangeField mutation "
             "for 'TestModel.added_field' in 'tests' requires user-specified "
             "initial value."),
            lambda: self.perform_evolution_tests(
                DestModel,
                [],
                self.DIFF_TEXT,
                [
                    "AddField('TestModel', 'added_field', models.IntegerField,"
                    " initial=<<USER VALUE REQUIRED>>)",
                ],
                None,
                use_hinted_evolutions=True))

    def test_add_non_null_column_no_initial_raises_exception(self):
        """Testing AddField with non-NULL column, no initial value
        raises EvolutionException"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField()

        self.assertRaisesMessage(
            SimulationFailure,
            ("Cannot create new column 'added_field' on 'tests.TestModel' "
             "without a non-null initial value."),
            lambda: self.perform_evolution_tests(
                DestModel,
                [
                    AddField('TestModel', 'added_field', models.IntegerField),
                ],
                self.DIFF_TEXT,
                [
                    "AddField('TestModel', 'added_field', models.IntegerField,"
                    " initial=<<USER VALUE REQUIRED>>)",
                ],
                None))

    def test_add_non_null_column_with_initial(self):
        """Testing AddField with non-NULL column with initial value"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField()

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.IntegerField,
                         initial=1),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>)",
            ],
            'AddNonNullNonCallableColumnModel')

    def test_add_non_null_column_with_callable_initial(self):
        """Testing AddField with non-NULL column with callable initial value"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField()

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.IntegerField,
                         initial=AddSequenceFieldInitial(
                             'AddNonNullCallableColumnModel')),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>)",
            ],
            'AddNonNullCallableColumnModel')

    def tst_add_null_column(self):
        """Testing AddField with NULL column"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField(null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         null=True),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.CharField,"
                " null=True)",
            ],
            'AddNullColumnModel')

    def test_add_null_column_with_initial(self):
        """Testing AddField with NULL column with initial value"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField(null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.IntegerField,
                         initial=1, null=True),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " null=True)"
            ],
            'AddNullColumnWithInitialColumnModel')

    def test_add_with_initial_string(self):
        """Testing AddField with string-based initial value"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.CharField(max_length=10)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial="abc's xyz", max_length=10),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.CharField,"
                " initial=<<USER VALUE REQUIRED>>, max_length=10)"
            ],
            'AddStringColumnModel')

    def test_add_with_blank_initial_string(self):
        """Testing AddField with blank string initial value"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.CharField(max_length=10, blank=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='', max_length=10),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.CharField,"
                " initial=u'', max_length=10)"
            ],
            'AddBlankStringColumnModel')

    def test_add_datetime_field(self):
        """Testing AddField with DateTimeField"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.DateTimeField()

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.DateTimeField,
                         initial=datetime(2007, 12, 13, 16, 42, 0)),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.DateTimeField,"
                " initial=<<USER VALUE REQUIRED>>)",
            ],
            'AddDateColumnModel')

    def test_add_with_default(self):
        """Testing AddField with default value"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField(default=42)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.IntegerField,
                         initial=42),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " initial=42)",
            ],
            'AddDefaultColumnModel')

    def test_add_boolean_field_with_different_initial(self):
        """Testing AddField with BooleanField and initial value different from
        model definition
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.BooleanField(default=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.BooleanField,
                         initial=False),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.BooleanField,"
                " initial=True)",
            ],
            'AddMismatchInitialBoolColumnModel')

    def test_add_with_empty_string_default(self):
        """Testing AddField with empty string as default value"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.CharField(max_length=20, default='')

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.CharField,
                         initial='', max_length=20),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.CharField,"
                " initial=u'', max_length=20)",
            ],
            'AddEmptyStringDefaultColumnModel')

    def test_add_with_custom_column_name(self):
        """Testing AddField with custom column name"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField(db_column='non-default_column',
                                              null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.IntegerField,
                         null=True, db_column='non-default_column'),
            ],
            self.DIFF_TEXT,
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " null=True, db_column='non-default_column')",
            ],
            'NonDefaultColumnModel')

    def test_add_with_custom_table_name(self):
        """Testing AddField with custom table name"""
        class DestModel(models.Model):
            value = models.IntegerField()
            alt_value = models.CharField(max_length=20)
            added_field = models.IntegerField(null=True)

            class Meta:
                db_table = 'custom_table_name'

        self.set_base_model(CustomTableModel, name='CustomTableModel')

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('CustomTableModel', 'added_field',
                         models.IntegerField, null=True),
            ],
            ("In model tests.CustomTableModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('CustomTableModel', 'added_field',"
                " models.IntegerField, null=True)",
            ],
            'AddColumnCustomTableModel',
            model_name='CustomTableModel')

    def test_add_primary_key_with_delete_old_fails(self):
        """Testing AddField with primary key and deleting old key fails"""
        class DestModel(models.Model):
            my_primary_key = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()

        self.assertRaisesMessage(
            SimulationFailure,
            'Cannot delete a primary key.',
            lambda: self.perform_evolution_tests(
                DestModel,
                [
                    AddField(
                        'TestModel', 'my_primary_key', models.AutoField,
                        initial=AddSequenceFieldInitial('AddPrimaryKeyModel'),
                        primary_key=True),
                    DeleteField('TestModel', 'id'),
                ],
                ("In model tests.TestModel:\n"
                 "    Field 'my_primary_key' has been added\n"
                 "    Field 'id' has been deleted"),
                [
                    "AddField('TestModel', 'my_primary_key', models.AutoField,"
                    " initial=<<USER VALUE REQUIRED>>, primary_key=True)",

                    "DeleteField('TestModel', 'id')",
                ],
                None))

    def test_add_indexed_column(self):
        """Testing AddField with indexed column"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            add_field = models.IntegerField(db_index=True, null=True)

        self.assertFalse(has_index_with_columns(
            self.database_sig, 'tests_testmodel', ['add_field']))

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'add_field', models.IntegerField,
                         null=True, db_index=True),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'add_field' has been added"),
            [
                "AddField('TestModel', 'add_field', models.IntegerField,"
                " null=True, db_index=True)",
            ],
            'AddIndexedColumnModel')

        self.assertTrue(has_index_with_columns(
            self.test_database_sig, 'tests_testmodel', ['add_field']))

    def test_add_unique_column(self):
        """Testing AddField with unique column"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField(unique=True, null=True)

        self.assertFalse(has_index_with_columns(
            self.database_sig, 'tests_testmodel', ['added_field']))

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.IntegerField,
                         unique=True, null=True),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " unique=True, null=True)",
            ],
            'AddUniqueColumnModel')

        self.assertTrue(has_index_with_columns(
            self.test_database_sig, 'tests_testmodel', ['added_field']))

    def test_add_unique_indexed_column(self):
        """Testing AddField with unique indexed column"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.IntegerField(unique=True, db_index=True,
                                              null=True)

        self.assertFalse(has_index_with_columns(
            self.database_sig, 'tests_testmodel', ['added_field'],
            unique=True))

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.IntegerField,
                         unique=True, null=True, db_index=True),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.IntegerField,"
                " unique=True, null=True, db_index=True)",
            ],
            'AddUniqueIndexedModel')

        self.assertTrue(has_index_with_columns(
            self.test_database_sig, 'tests_testmodel', ['added_field'],
            unique=True))

    def test_add_foreign_key(self):
        """Testing AddField with ForeignKey"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.ForeignKey(AddAnchor1, null=True)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.ForeignKey,
                         null=True, related_model='tests.AddAnchor1'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.ForeignKey,"
                " null=True, related_model='tests.AddAnchor1')",
            ],
            'AddForeignKeyModel')

    def test_add_many_to_many_field(self):
        """Testing AddField with ManyToManyField"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.ManyToManyField(AddAnchor1)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.ManyToManyField,
                         related_model='tests.AddAnchor1'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.ManyToManyField,"
                " related_model='tests.AddAnchor1')",
            ],
            'AddManyToManyDatabaseTableModel')

    def test_add_many_to_many_field_custom_table_name(self):
        """Testing AddField with ManyToManyField and custom table name"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.ManyToManyField(AddAnchor2)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.ManyToManyField,
                         related_model='tests.AddAnchor2'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.ManyToManyField,"
                " related_model='tests.AddAnchor2')",
            ],
            'AddManyToManyNonDefaultDatabaseTableModel')

    def test_add_many_to_many_field_to_self(self):
        """Testing AddField with ManyToManyField to self"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.ManyToManyField('self')

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.ManyToManyField,
                         related_model='tests.TestModel'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.ManyToManyField,"
                " related_model='tests.TestModel')",
            ],
            'AddManyToManySelf')

    def test_add_with_custom_database(self):
        """Testing AddField with custom database"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.ForeignKey(AddAnchor1, null=True)

        self.set_base_model(
            self.default_base_model,
            extra_models=self.default_extra_models,
            db_name='db_multi')

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.ForeignKey,
                         null=True, related_model='tests.AddAnchor1'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.ForeignKey,"
                " null=True, related_model='tests.AddAnchor1')",
            ],
            'AddForeignKeyModel',
            db_name='db_multi')

    def test_add_many_to_many_field_and_custom_database(self):
        """Testing AddField with ManyToManyField and custom database"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            added_field = models.ManyToManyField(AddAnchor1)

        self.perform_evolution_tests(
            DestModel,
            [
                AddField('TestModel', 'added_field', models.ManyToManyField,
                         related_model='tests.AddAnchor1'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'added_field' has been added"),
            [
                "AddField('TestModel', 'added_field', models.ManyToManyField,"
                " related_model='tests.AddAnchor1')",
            ],
            'AddManyToManyDatabaseTableModel',
            db_name='db_multi')
