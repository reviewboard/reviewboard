from __future__ import unicode_literals

from django.db import models, transaction
from django.db.models.signals import post_save

from djblets.db.fields import RelationCounterField
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class ReffedModel(models.Model):
    m2m_reffed_counter = RelationCounterField('m2m_reffed')
    reffed_key_counter = RelationCounterField('key_reffed')

    # These are here to ensure that RelationCounterField's smarts don't
    # over-increment/decrement other counters.
    m2m_reffed_counter_2 = RelationCounterField('m2m_reffed')
    reffed_key_counter_2 = RelationCounterField('key_reffed')


class M2MRefModel(models.Model):
    m2m = models.ManyToManyField(ReffedModel, related_name='m2m_reffed')
    counter = RelationCounterField('m2m')
    counter_2 = RelationCounterField('m2m')


class KeyRefModel(models.Model):
    key = models.ForeignKey(ReffedModel, related_name='key_reffed',
                            null=True)


class BadKeyRefModel(models.Model):
    key = models.ForeignKey(ReffedModel, related_name='bad_key_reffed')
    counter = RelationCounterField('key')
    counter_2 = RelationCounterField('key')


class RelationCounterFieldTests(TestModelsLoaderMixin, TestCase):
    """Tests for djblets.db.fields.RelationCounterField."""
    tests_app = 'djblets.db.tests'

    # ManyToManyField.add will do 1 filter(), 1 bulk_create().
    # RelationCounterField will do 1 increment(), 1 reload() for self;
    # 1 increment() total for all objects.
    M2M_ADD_BASE_QUERY_COUNT = 2 + 3

    # RelationCounterField will do 1 reload() per item.
    M2M_ADD_LOADED_ITEM_QUERY_COUNT = 1

    # ManyToManyField.add will do 1 filter(), 1 delete()
    # RelationCounterField will do 1 decrement(), 2 update()
    M2M_REMOVE_BASE_QUERY_COUNT = 2 + 3

    # RelationCounterField will do 1 reload() per item
    M2M_REMOVE_LOADED_ITEM_QUERY_COUNT = 1

    # ManyToManyField.clear will do 2 filters(), 1 delete().
    # RelationCounterField will do 1 decrement(), 1 reload(), 1 update().
    M2M_CLEAR_BASE_QUERY_COUNT = 3 + 3

    # RelationCounterField will do 1 reload().
    M2M_CLEAR_LOADED_ITEM_QUERY_COUNT = 1

    # Django will do 1 delete().
    # RelationCounterField will do 1 decrement(), 1 reload().
    KEY_REMOVE_ITEM_QUERY_COUNT = 1 + 2

    # Django will do 1 create().
    # RelationCounterField will do 1 update().
    KEY_CREATE_UNLOADED_REL_QUERY_COUNT = 2

    # RelationCounterField will do 1 count(), 1 reload()
    REINIT_QUERY_COUNT = 2

    def setUp(self):
        super(RelationCounterFieldTests, self).setUp()

        # Make sure the state is clear due to dropped references before
        # each run.
        self.assertFalse(RelationCounterField._instance_states)

    #
    # Instance tracking tests
    #

    @transaction.atomic
    def test_reused_ids(self):
        """Testing RelationCounterField with reused instance IDs"""
        sid = transaction.savepoint()

        model = M2MRefModel.objects.create()
        added_model = ReffedModel.objects.create()
        model.m2m.add(added_model)
        self.assertEqual(model.pk, 1)
        self.assertEqual(added_model.pk, 1)
        self.assertEqual(model.counter, 1)
        self.assertEqual(model.counter_2, 1)

        # Roll back, and set up the test again.
        transaction.savepoint_rollback(sid)

        model = M2MRefModel.objects.create()
        added_model = ReffedModel.objects.create()
        model.m2m.add(added_model)
        self.assertEqual(model.pk, 1)
        self.assertEqual(added_model.pk, 1)
        self.assertEqual(model.counter, 1)
        self.assertEqual(model.counter_2, 1)

    def test_unsaved_and_other_double_save(self):
        """Testing RelationCounterField with an unsaved object and a double
        save on another object
        """
        # Due to a misplaced assertion, we had a bug where _on_first_save
        # was failing an assertion check when there were two instances of
        # a class, and the second one created was then saved twice. The
        # signal connection from the first stuck around and saw that
        # updated=False, which it expected would be True. However, it didn't
        # check first if it was matching the expected instance.
        base_receiver_count = len(post_save.receivers)

        model1 = M2MRefModel()
        model2 = M2MRefModel()
        self.assertEqual(model1.pk, None)
        self.assertEqual(model2.pk, None)
        self.assertEqual(len(post_save.receivers), base_receiver_count + 2)

        # Perform the first save, which will do update=True.
        model2.save()
        self.assertEqual(len(post_save.receivers), base_receiver_count + 1)

        # Perform the second save, which will do update=False.
        model2.save()
        self.assertEqual(len(post_save.receivers), base_receiver_count + 1)

    def test_disconnect_signal_on_destroy(self):
        """Testing RelationCounterField disconnects signals for an object when
        it falls out of scope
        """
        base_receiver_count = len(post_save.receivers)

        model = M2MRefModel()
        self.assertEqual(model.pk, None)
        self.assertEqual(len(post_save.receivers), base_receiver_count + 1)

        model = None
        self.assertEqual(len(post_save.receivers), base_receiver_count)


    #
    # Forward-relation ManyToManyField tests
    #

    def test_m2m_forward_initialize(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and initialization
        """
        with self.assertNumQueries(1):
            model = M2MRefModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)

    def test_m2m_forward_and_reinit(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and re-initialization
        """
        with self.assertNumQueries(2):
            model = M2MRefModel.objects.create()
            added_model = ReffedModel.objects.create()

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(added_model)

        with self.assertNumQueries(self.REINIT_QUERY_COUNT):
            model.counter = None
            model.reinit_counter()
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)

    def test_m2m_forward_and_create(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and creating object
        """
        with self.assertNumQueries(1):
            model = M2MRefModel.objects.create()

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_1 = model.m2m.create()
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_2 = model.m2m.create()
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_add(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and adding object
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_add_many(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and adding multiple objects
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   2 * self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1, rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_remove(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and removing object
        """
        with self.assertNumQueries(2):
            model = M2MRefModel.objects.create()
            rel_model = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model.m2m_reffed_counter, 0)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model.m2m_reffed_counter, 1)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(self.M2M_REMOVE_BASE_QUERY_COUNT +
                                   self.M2M_REMOVE_LOADED_ITEM_QUERY_COUNT):
            model.m2m.remove(rel_model)
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model.m2m_reffed_counter, 0)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 0)

    def test_m2m_forward_and_clear(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and clearing all objects
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT +
                                   2 * self.M2M_CLEAR_LOADED_ITEM_QUERY_COUNT):
            model.m2m.clear()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

    def test_m2m_forward_and_clear_unloaded(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and clearing all unloaded objects
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

        # Get rid of these for now, so that the state will drop. This will
        # ensure we're re-fetching on pre_clear.
        rel_model_id_1 = rel_model_1.pk
        rel_model_id_2 = rel_model_2.pk
        del rel_model_1
        del rel_model_2

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT):
            model.m2m.clear()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)

        with self.assertNumQueries(2):
            rel_model_1 = ReffedModel.objects.get(
                pk=rel_model_id_1)
            rel_model_2 = ReffedModel.objects.get(
                pk=rel_model_id_2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

    #
    # Reverse-relation ManyToManyField tests
    #

    def test_m2m_reverse_initialize(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and initialization
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)

    def test_m2m_reverse_and_reinit(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and re-initialization
        """
        with self.assertNumQueries(2):
            model = ReffedModel.objects.create()
            rel_model = M2MRefModel.objects.create()

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model)

        with self.assertNumQueries(self.REINIT_QUERY_COUNT):
            model.m2m_reffed_counter = None
            model.reinit_m2m_reffed_counter()
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)

    def test_m2m_reverse_and_create(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and creating object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_1 = model.m2m_reffed.create()
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_2 = model.m2m_reffed.create()
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

    def test_m2m_reverse_and_add(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and adding object
        """
        with self.assertNumQueries(3):
            model = ReffedModel.objects.create()
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_1)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_2)
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

    def test_m2m_reverse_and_remove(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and removing object
        """
        with self.assertNumQueries(2):
            model = ReffedModel.objects.create()
            rel_model = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model.counter, 0)
            self.assertEqual(rel_model.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model.counter, 1)
            self.assertEqual(rel_model.counter_2, 1)

        with self.assertNumQueries(self.M2M_REMOVE_BASE_QUERY_COUNT +
                                   self.M2M_REMOVE_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.remove(rel_model)
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model.counter, 0)
            self.assertEqual(rel_model.counter_2, 0)

    def test_m2m_reverse_and_clear(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and clearing all objects
        """
        with self.assertNumQueries(3):
            model = ReffedModel.objects.create()
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_1)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_2)
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT +
                                   2 * self.M2M_CLEAR_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.clear()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

    def test_m2m_reverse_and_clear_unloaded(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and clearing all unloaded objects
        """
        with self.assertNumQueries(3):
            model = ReffedModel.objects.create()
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_1)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_2)
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

        # Get rid of these for now, so that the state will drop. This will
        # ensure we're re-fetching on pre_clear.
        rel_model_id_1 = rel_model_1.pk
        rel_model_id_2 = rel_model_2.pk
        del rel_model_1
        del rel_model_2

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT):
            model.m2m_reffed.clear()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(2):
            rel_model_1 = M2MRefModel.objects.get(
                pk=rel_model_id_1)
            rel_model_2 = M2MRefModel.objects.get(
                pk=rel_model_id_2)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

    #
    # Forward-relation ForeignKey tests
    #

    def test_fkey_forward_initialize(self):
        """Testing RelationCounterField with forward ForeignKey relation
        and initialization disallowed
        """
        with self.assertNumQueries(0):
            self.assertRaisesMessage(
                ValueError,
                "RelationCounterField cannot work with the forward "
                "end of a ForeignKey ('key')",
                lambda: BadKeyRefModel())

    #
    # Reverse-relation ForeignKey tests
    #

    def test_fkey_reverse_initialize(self):
        """Testing RelationCounterField with reverse ForeignKey relation
        and initialization
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

    def test_fkey_reverse_and_reinit(self):
        """Testing RelationCounterField with reverse ForeignKey relation
        and re-initialization
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model)

        with self.assertNumQueries(self.REINIT_QUERY_COUNT):
            model.reffed_key_counter = None
            model.reinit_reffed_key_counter()
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

    def test_fkey_reverse_and_add(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        adding object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 2)
            self.assertEqual(model.reffed_key_counter_2, 2)

    def test_fkey_reverse_and_add_unloaded_by_id(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        adding unloaded object by ID
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        model_id = model.pk
        del model

        with self.assertNumQueries(self.KEY_CREATE_UNLOADED_REL_QUERY_COUNT):
            KeyRefModel.objects.create(key_id=model_id)

        with self.assertNumQueries(1):
            model = ReffedModel.objects.get(pk=model_id)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

    def test_fkey_reverse_and_delete(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        deleting object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        with self.assertNumQueries(self.KEY_REMOVE_ITEM_QUERY_COUNT):
            rel_model.delete()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

    def test_fkey_reverse_and_save_existing(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        saving existing object doesn't modify counts
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        with self.assertNumQueries(1):
            rel_model.save()
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

    def test_fkey_reverse_delete_unloaded(self):
        """Testing RelationCounterField with reverse ForeignKey relation
        and deleting unloaded object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        model_id = model.pk
        del model

        with self.assertNumQueries(self.KEY_REMOVE_ITEM_QUERY_COUNT):
            rel_model.delete()

        with self.assertNumQueries(1):
            model = ReffedModel.objects.get(pk=model_id)
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

    def test_fkey_reverse_and_delete_with_all_unloaded(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        deleting object with all instances unloaded
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        model_id = model.pk
        del model
        del rel_model

        with self.assertNumQueries(self.KEY_REMOVE_ITEM_QUERY_COUNT):
            KeyRefModel.objects.all().delete()

        with self.assertNumQueries(1):
            model = ReffedModel.objects.get(pk=model_id)
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)
