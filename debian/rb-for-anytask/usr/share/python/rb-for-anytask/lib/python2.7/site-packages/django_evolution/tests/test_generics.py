from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from django_evolution.mutations import DeleteField
from django_evolution.tests.base_test_case import EvolutionTestCase


class GenericAnchor(models.Model):
    value = models.IntegerField()

    # Host a generic key here, too
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')


class GenericBaseModel(models.Model):
    char_field = models.CharField(max_length=20)
    int_field = models.IntegerField()

    # Plus a generic foreign key - the Generic itself should be ignored
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    # Plus a generic relation, which should be ignored
    generic = generic.GenericRelation(GenericAnchor)


class GenericRelationsTests(EvolutionTestCase):
    """Testing generic relations support."""
    sql_mapping_key = 'generics'
    default_base_model = GenericBaseModel
    default_extra_models = [
        ('Anchor', GenericAnchor),
    ]

    def create_test_proj_sig(self, model, *args, **kwargs):
        return super(GenericRelationsTests, self).create_test_proj_sig(
            model,
            extra_models=[('contenttypes.ContentType', ContentType)],
            *args, **kwargs)

    def test_delete_column(self):
        """Testing generic relations and deleting column"""
        class DestModel(models.Model):
            int_field = models.IntegerField()

            # Plus a generic foreign key - the Generic itself should be ignored
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField(db_index=True)
            content_object = generic.GenericForeignKey('content_type',
                                                       'object_id')

            # Plus a generic relation, which should be ignored
            generic = generic.GenericRelation(GenericAnchor)

        self.perform_evolution_tests(
            DestModel,
            [
                DeleteField('TestModel', 'char_field'),
            ],
            ("In model tests.TestModel:\n"
             "    Field 'char_field' has been deleted"),
            [
                "DeleteField('TestModel', 'char_field')",
            ],
            'DeleteColumnModel')
