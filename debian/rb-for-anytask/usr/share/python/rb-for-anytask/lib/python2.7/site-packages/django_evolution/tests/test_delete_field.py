from django.db import models

from django_evolution.mutations import DeleteField
from django_evolution.tests.base_test_case import EvolutionTestCase


class DeleteAnchor1(models.Model):
    value = models.IntegerField()


class DeleteAnchor2(models.Model):
    value = models.IntegerField()


class DeleteAnchor3(models.Model):
    value = models.IntegerField()


class DeleteAnchor4(models.Model):
    value = models.IntegerField()


class DeleteBaseModel(models.Model):
    my_id = models.AutoField(primary_key=True)
    char_field = models.CharField(max_length=20)
    int_field = models.IntegerField()
    int_field2 = models.IntegerField(db_column='non-default_db_column')
    int_field3 = models.IntegerField(unique=True)
    fk_field1 = models.ForeignKey(DeleteAnchor1)
    m2m_field1 = models.ManyToManyField(DeleteAnchor3)
    m2m_field2 = models.ManyToManyField(DeleteAnchor4,
                                        db_table='non-default_m2m_table')


class CustomTableModel(models.Model):
    value = models.IntegerField()
    alt_value = models.CharField(max_length=20)

    class Meta:
        db_table = 'custom_table_name'


class DeleteFieldTests(EvolutionTestCase):
    """Testing DeleteField mutations."""
    sql_mapping_key = 'delete_field'
    default_base_model = DeleteBaseModel
    default_extra_models = [
        ('DeleteAnchor1', DeleteAnchor1),
        ('DeleteAnchor2', DeleteAnchor2),
        ('DeleteAnchor3', DeleteAnchor3),
        ('DeleteAnchor4', DeleteAnchor4),
    ]

    def test_delete(self):
        """Testing DeleteField with a typical column"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field2 = models.IntegerField(db_column='non-default_db_column')
            int_field3 = models.IntegerField(unique=True)
            fk_field1 = models.ForeignKey(DeleteAnchor1)
            m2m_field1 = models.ManyToManyField(DeleteAnchor3)
            m2m_field2 = models.ManyToManyField(
                DeleteAnchor4,
                db_table='non-default_m2m_table')

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('TestModel', 'int_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'int_field' has been deleted"),
            [
                "DeleteField('TestModel', 'int_field')",
            ],
            'DefaultNamedColumnModel')

    def test_delete_with_custom_column_name(self):
        """Testing DeleteField with custom column name"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field3 = models.IntegerField(unique=True)
            fk_field1 = models.ForeignKey(DeleteAnchor1)
            m2m_field1 = models.ManyToManyField(DeleteAnchor3)
            m2m_field2 = models.ManyToManyField(
                DeleteAnchor4,
                db_table='non-default_m2m_table')

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('TestModel', 'int_field2'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'int_field2' has been deleted"),
            [
                "DeleteField('TestModel', 'int_field2')",
            ],
            'NonDefaultNamedColumnModel')

    def test_delete_with_unique(self):
        """Testing DeleteField with unique=True"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field2 = models.IntegerField(db_column='non-default_db_column')
            fk_field1 = models.ForeignKey(DeleteAnchor1)
            m2m_field1 = models.ManyToManyField(DeleteAnchor3)
            m2m_field2 = models.ManyToManyField(
                DeleteAnchor4,
                db_table='non-default_m2m_table')

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('TestModel', 'int_field3'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'int_field3' has been deleted"),
            [
                "DeleteField('TestModel', 'int_field3')",
            ],
            'ConstrainedColumnModel')

    def test_delete_many_to_many_field(self):
        """Testing DeleteField with ManyToManyField"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field2 = models.IntegerField(db_column='non-default_db_column')
            int_field3 = models.IntegerField(unique=True)
            fk_field1 = models.ForeignKey(DeleteAnchor1)
            m2m_field2 = models.ManyToManyField(
                DeleteAnchor4,
                db_table='non-default_m2m_table')

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('TestModel', 'm2m_field1'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'm2m_field1' has been deleted"),
            [
                "DeleteField('TestModel', 'm2m_field1')",
            ],
            'DefaultManyToManyModel')

    def test_delete_many_to_many_field_custom_table(self):
        """Testing DeleteField with ManyToManyField and custom table"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field2 = models.IntegerField(db_column='non-default_db_column')
            int_field3 = models.IntegerField(unique=True)
            fk_field1 = models.ForeignKey(DeleteAnchor1)
            m2m_field1 = models.ManyToManyField(DeleteAnchor3)

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('TestModel', 'm2m_field2'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'm2m_field2' has been deleted"),
            [
                "DeleteField('TestModel', 'm2m_field2')",
            ],
            'NonDefaultManyToManyModel')

    def test_delete_foreign_key(self):
        """Testing DeleteField with ForeignKey"""
        class DestModel(models.Model):
            my_id = models.AutoField(primary_key=True)
            char_field = models.CharField(max_length=20)
            int_field = models.IntegerField()
            int_field2 = models.IntegerField(db_column='non-default_db_column')
            int_field3 = models.IntegerField(unique=True)
            m2m_field1 = models.ManyToManyField(DeleteAnchor3)
            m2m_field2 = models.ManyToManyField(
                DeleteAnchor4,
                db_table='non-default_m2m_table')

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('TestModel', 'fk_field1'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'fk_field1' has been deleted"),
            [
                "DeleteField('TestModel', 'fk_field1')",
            ],
            'DeleteForeignKeyModel')

    def test_delete_column_from_custom_table(self):
        """Testing DeleteField with custom table name"""
        class DestModel(models.Model):
            alt_value = models.CharField(max_length=20)

            class Meta:
                db_table = 'custom_table_name'

        self.set_base_model(CustomTableModel, name='CustomTableModel')

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('CustomTableModel', 'value'),
            ],
            ("In model tests.CustomTableModel:\n"
             "    Field 'value' has been deleted"),
            [
                "DeleteField('CustomTableModel', 'value')",
            ],
            'DeleteColumnCustomTableModel',
            model_name='CustomTableModel')
