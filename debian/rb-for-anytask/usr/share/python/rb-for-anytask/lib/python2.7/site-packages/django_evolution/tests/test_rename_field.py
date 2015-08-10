from django.db import models

from django_evolution.mutations import RenameField
from django_evolution.tests.base_test_case import EvolutionTestCase


class RenameAnchor1(models.Model):
    value = models.IntegerField()


class RenameAnchor2(models.Model):
    value = models.IntegerField()

    class Meta:
        db_table = 'custom_rename_anchor_table'


class RenameAnchor3(models.Model):
    value = models.IntegerField()


class RenameFieldBaseModel(models.Model):
    char_field = models.CharField(max_length=20)
    int_field = models.IntegerField()
    int_field_named = models.IntegerField(db_column='custom_db_col_name')
    int_field_named_indexed = models.IntegerField(
        db_column='custom_db_col_name_indexed',
        db_index=True)
    fk_field = models.ForeignKey(RenameAnchor1)
    m2m_field = models.ManyToManyField(RenameAnchor2)
    m2m_field_named = models.ManyToManyField(
        RenameAnchor3, db_table='non-default_db_table')


class CustomRenameTableModel(models.Model):
    value = models.IntegerField()
    alt_value = models.CharField(max_length=20)

    class Meta:
        db_table = 'custom_rename_table_name'


class RenameFieldTests(EvolutionTestCase):
    """Unit tests for RenameField mutations."""
    sql_mapping_key = 'rename_field'
    default_base_model = RenameFieldBaseModel
    default_extra_models = [
        ('RenameAnchor1', RenameAnchor1),
        ('RenameAnchor2', RenameAnchor2),
        ('RenameAnchor3', RenameAnchor3),
    ]

    def test_rename(self):
        """Testing RenameField"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            renamed_field = models.IntegerField()
            int_field_named = models.IntegerField(
                db_column='custom_db_col_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'int_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'int_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>)",

                "DeleteField('TestModel', 'int_field')",
            ],
            'RenameColumnModel')

    def test_rename_with_custom_table_non_m2m_ignored(self):
        """Testing RenameField with custom table name for non-ManyToManyField
        is ignored
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            renamed_field = models.IntegerField()
            int_field_named = models.IntegerField(
                db_column='custom_db_col_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'int_field', 'renamed_field',
                            db_table='ignored_db-table'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'int_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>)",

                "DeleteField('TestModel', 'int_field')",
            ],
            'RenameColumnWithTableNameModel')

    def test_rename_with_primary_key(self):
        """Testing RenameField with primary key"""
        class DestModel(models.Model):
            my_pk_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field_named = models.IntegerField(
                db_column='custom_db_col_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'id', 'my_pk_id'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'my_pk_id' has been added\n"
             "    Field 'id' has been deleted"),
            [
                "AddField('TestModel', 'my_pk_id', models.AutoField,"
                " initial=<<USER VALUE REQUIRED>>, primary_key=True)",

                "DeleteField('TestModel', 'id')",
            ],
            'RenamePrimaryKeyColumnModel')

    def test_rename_with_foreign_key(self):
        """Testing RenameField with ForeignKey"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field_named = models.IntegerField(
                db_column='custom_db_col_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            renamed_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'fk_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'fk_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.ForeignKey,"
                " initial=<<USER VALUE REQUIRED>>,"
                " related_model='tests.RenameAnchor1')",

                "DeleteField('TestModel', 'fk_field')",
            ],
            perform_mutations=False)

    def test_rename_with_custom_column_name(self):
        """Testing RenameField with custom column name"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            renamed_field = models.IntegerField()
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'int_field_named', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'int_field_named' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>)",

                "DeleteField('TestModel', 'int_field_named')",
            ],
            'RenameNonDefaultColumnNameModel')

    def test_rename_custom_column_name_to_new_custom_name(self):
        """Testing RenameField with custom column name to a new custom column
        name
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            renamed_field = models.IntegerField(
                db_column='non-default_column_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'int_field_named', 'renamed_field',
                            db_column='non-default_column_name'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'int_field_named' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>,"
                " db_column='non-default_column_name')",

                "DeleteField('TestModel', 'int_field_named')",
            ],
            'RenameNonDefaultColumnNameToNonDefaultNameModel')

    def test_rename_with_custom_column_and_table_names(self):
        """Testing RenameField with custom column and ignored
        custom table name
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            renamed_field = models.IntegerField(
                db_column='non-default_column_name2')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'int_field_named', 'renamed_field',
                            db_column='non-default_column_name2',
                            db_table='custom_ignored_db-table'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'int_field_named' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field', models.IntegerField,"
                " initial=<<USER VALUE REQUIRED>>,"
                " db_column='non-default_column_name2')",

                "DeleteField('TestModel', 'int_field_named')",
            ],
            'RenameNonDefaultColumnNameToNonDefaultNameAndTableModel')

    def test_rename_in_custom_table_name(self):
        """Testing RenameField with custom table name"""
        class DestModel(models.Model):
            renamed_field = models.IntegerField()
            alt_value = models.CharField(max_length=20)

            class Meta:
                db_table = 'custom_rename_table_name'

        self.set_base_model(CustomRenameTableModel,
                            name='CustomRenameTableModel')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('CustomRenameTableModel', 'value',
                            'renamed_field'),
            ],
            ("In model tests.CustomRenameTableModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'value' has been deleted"),
            [
                "AddField('CustomRenameTableModel', 'renamed_field',"
                " models.IntegerField, initial=<<USER VALUE REQUIRED>>)",

                "DeleteField('CustomRenameTableModel', 'value')",
            ],
            'RenameColumnCustomTableModel',
            model_name='CustomRenameTableModel')

    def test_rename_m2m_table(self):
        """Testing RenameField with renaming ManyToManyField table name"""
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field_named = models.IntegerField(
                db_column='custom_db_col_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            renamed_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'm2m_field', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'm2m_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field',"
                " models.ManyToManyField,"
                " related_model='tests.RenameAnchor2')",

                "DeleteField('TestModel', 'm2m_field')",
            ],
            'RenameManyToManyTableModel')

    def test_rename_m2m_db_column_ignored(self):
        """Testing RenameField with renaming ManyToManyField db_column is
        ignored
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field_named = models.IntegerField(
                db_column='custom_db_col_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            renamed_field = models.ManyToManyField(RenameAnchor2)
            m2m_field_named = models.ManyToManyField(
                RenameAnchor3, db_table='non-default_db_table')

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'm2m_field', 'renamed_field',
                            db_column='ignored_db-column'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'm2m_field' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field',"
                " models.ManyToManyField,"
                " related_model='tests.RenameAnchor2')",

                "DeleteField('TestModel', 'm2m_field')",
            ],
            'RenameManyToManyTableWithColumnNameModel')

    def test_rename_m2m_custom_table_name_to_default(self):
        """Testing RenameField with renaming ManyToManyField custom table
        name to default name
        """
        class DestModel(models.Model):
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field_named = models.IntegerField(
                db_column='custom_db_col_name')
            int_field_named_indexed = models.IntegerField(
                db_column='custom_db_col_name_indexed', db_index=True)
            fk_field = models.ForeignKey(RenameAnchor1)
            m2m_field = models.ManyToManyField(RenameAnchor2)
            renamed_field = models.ManyToManyField(
                RenameAnchor3)

        self.perform_evolution_tests(
            DestModel,
            [
                RenameField('TestModel', 'm2m_field_named', 'renamed_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'renamed_field' has been added\n"
             "    Field 'm2m_field_named' has been deleted"),
            [
                "AddField('TestModel', 'renamed_field',"
                " models.ManyToManyField,"
                " related_model='tests.RenameAnchor3')",

                "DeleteField('TestModel', 'm2m_field_named')",
            ],
            'RenameNonDefaultManyToManyTableModel')
