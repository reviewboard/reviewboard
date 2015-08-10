#
# fields.py -- Model fields.
#
# Copyright (c) 2007-2008  Christian Hammond
# Copyright (c) 2007-2008  David Trowbridge
# Copyright (c) 2008-2013  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from ast import literal_eval
from datetime import datetime
import base64
import json
import logging
import weakref

from django import forms
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import F, Q
from django.db.models.expressions import ExpressionNode
from django.db.models.signals import (m2m_changed, post_delete, post_init,
                                      post_save)
from django.utils import six
from django.utils.encoding import smart_unicode

from djblets.db.validators import validate_json
from djblets.util.dates import get_tz_aware_utcnow


class Base64DecodedValue(str):
    """
    A subclass of string that can be identified by Base64Field, in order
    to prevent double-encoding or double-decoding.
    """
    pass


class Base64FieldCreator(object):
    def __init__(self, field):
        self.field = field

    def __set__(self, obj, value):
        pk_val = obj._get_pk_val(obj.__class__._meta)
        pk_set = pk_val is not None and smart_unicode(pk_val) != ''

        if (isinstance(value, Base64DecodedValue) or not pk_set):
            obj.__dict__[self.field.name] = base64.encodestring(value)
        else:
            obj.__dict__[self.field.name] = value

        setattr(obj, "%s_initted" % self.field.name, True)

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')

        value = obj.__dict__[self.field.name]

        if value is None:
            return None
        else:
            return Base64DecodedValue(base64.decodestring(value))


class Base64Field(models.TextField):
    """
    A subclass of TextField that encodes its data as base64 in the database.
    This is useful if you're dealing with unknown encodings and must guarantee
    that no modifications to the text occurs and that you can read/write
    the data in any database with any encoding.
    """
    serialize_to_string = True

    def contribute_to_class(self, cls, name):
        super(Base64Field, self).contribute_to_class(cls, name)

        setattr(cls, self.name, Base64FieldCreator(self))
        setattr(cls, 'get_%s_base64' % self.name,
                lambda model_instance: model_instance.__dict__[self.name])

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, Base64DecodedValue):
            value = base64.encodestring(value)

        return value

    def save_form_data(self, instance, data):
        setattr(instance, self.name, Base64DecodedValue(data))

    def to_python(self, value):
        if isinstance(value, Base64DecodedValue):
            return value
        else:
            return Base64DecodedValue(base64.decodestring(value))

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)

        if isinstance(value, Base64DecodedValue):
            return base64.encodestring(value)
        else:
            return value


class ModificationTimestampField(models.DateTimeField):
    """
    A subclass of DateTimeField that only auto-updates the timestamp when
    updating an existing object or when the value of the field is None. This
    specialized field is equivalent to DateTimeField's auto_now=True, except
    it allows for custom timestamp values (needed for
    serialization/deserialization).
    """
    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs.update({
            'editable': False,
            'blank': True,
        })
        models.DateTimeField.__init__(self, verbose_name, name, **kwargs)

    def pre_save(self, model, add):
        if not add or getattr(model, self.attname) is None:

            if settings.USE_TZ:
                value = get_tz_aware_utcnow()
            else:
                value = datetime.now()

            setattr(model, self.attname, value)
            return value

        return super(ModificationTimestampField, self).pre_save(model, add)

    def get_internal_type(self):
        return "DateTimeField"


class JSONFormField(forms.CharField):
    """Provides a form field for JSON input.

    This is meant to be used by JSONField, and handles the work of
    normalizing a Python data structure back into a serialized JSON
    string for editing.
    """
    def __init__(self, encoder=None, *args, **kwargs):
        super(JSONFormField, self).__init__(*args, **kwargs)
        self.encoder = encoder or DjangoJSONEncoder()

    def prepare_value(self, value):
        if isinstance(value, six.string_types):
            return value
        else:
            return self.encoder.encode(value)


class JSONField(models.TextField):
    """
    A field for storing JSON-encoded data. The data is accessible as standard
    Python data types and is transparently encoded/decoded to/from a JSON
    string in the database.
    """
    serialize_to_string = True
    default_validators = [validate_json]

    def __init__(self, verbose_name=None, name=None,
                 encoder=DjangoJSONEncoder(), **kwargs):
        blank = kwargs.pop('blank', True)
        models.TextField.__init__(self, verbose_name, name, blank=blank,
                                  **kwargs)
        self.encoder = encoder

    def contribute_to_class(self, cls, name):
        def get_json(model_instance):
            return self.dumps(getattr(model_instance, self.attname, None))

        def set_json(model_instance, json):
            setattr(model_instance, self.attname, self.loads(json))

        super(JSONField, self).contribute_to_class(cls, name)

        setattr(cls, "get_%s_json" % self.name, get_json)
        setattr(cls, "set_%s_json" % self.name, set_json)

        post_init.connect(self.post_init, sender=cls)

    def pre_save(self, model_instance, add):
        return self.dumps(getattr(model_instance, self.attname, None))

    def post_init(self, instance=None, **kwargs):
        value = self.value_from_object(instance)

        if value:
            value = self.loads(value)
        else:
            value = {}

        setattr(instance, self.attname, value)

    def get_db_prep_save(self, value, *args, **kwargs):
        if not isinstance(value, six.string_types):
            value = self.dumps(value)

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_to_string(self, obj):
        return self.dumps(self.value_from_object(obj))

    def dumps(self, data):
        if isinstance(data, six.string_types):
            return data
        else:
            return self.encoder.encode(data)

    def loads(self, val):
        try:
            val = json.loads(val, encoding=settings.DEFAULT_CHARSET)

            # XXX We need to investigate why this is happening once we have
            #     a solid repro case.
            if isinstance(val, six.string_types):
                logging.warning("JSONField decode error. Expected dictionary, "
                                "got string for input '%s'" % val)
                # For whatever reason, we may have gotten back
                val = json.loads(val, encoding=settings.DEFAULT_CHARSET)
        except ValueError:
            # There's probably embedded unicode markers (like u'foo') in the
            # string. We have to eval it.
            try:
                val = literal_eval(val)
            except Exception as e:
                logging.error('Failed to eval JSONField data "%r": %s'
                              % (val, e))
                val = {}

            if isinstance(val, six.string_types):
                logging.warning('JSONField decode error after literal_eval: '
                                'Expected dictionary, got string: %r' % val)
                val = {}

        return val

    def formfield(self, **kwargs):
        return super(JSONField, self).formfield(
            form_class=JSONFormField,
            encoder=self.encoder,
            **kwargs)


class CounterField(models.IntegerField):
    """A field that provides atomic counter updating and smart initialization.

    The CounterField makes it easy to atomically update an integer,
    incrementing or decrementing it, without raise conditions or conflicts.
    It can update a single instance at a time, or a batch of objects at once.

    CounterField is useful for storing counts of objects, reducing the number
    of queries performed. This requires that the calling code properly
    increments or decrements at all the right times, of course.

    This takes an optional ``initializer`` parameter that, if provided, can
    be used to auto-populate the field the first time the model instance is
    loaded, perhaps based on querying a number of related objects. The value
    passed to ``initializer`` must be a function taking the model instance
    as a parameter, and must return an integer or None. If it returns None,
    the counter will not be updated or saved.

    The model instance will gain four new functions:

        * ``increment_{field_name}`` - Atomically increment by one.
        * ``decrement_{field_name}`` - Atomically decrement by one.
        * ``reload_{field_name}`` - Reload the value in this instance from the
                                    database.
        * ``reinit_{field_name}`` - Re-initializes the stored field using the
                                    initializer function.

    The field on the class (not the instance) provides two functions for
    batch-updating models:

        * ``increment`` - Takes a queryset and increments this field for
                          each object.
        * ``decrement`` - Takes a queryset and decrements this field for
                          each object.
    """
    @classmethod
    def increment_many(cls, model_instance, values, reload_object=True):
        """Increments several fields on a model instance at once.

        This takes a model instance and dictionary of fields to values,
        and will increment each of those fields by that value.

        If reload_object is True, then the fields on the instance will
        be reloaded to reflect the current values.
        """
        cls._update_values(model_instance, values, reload_object, 1)

    @classmethod
    def decrement_many(cls, model_instance, values, reload_object=True):
        """Decrements several fields on a model instance at once.

        This takes a model instance and dictionary of fields to values,
        and will decrement each of those fields by that value.

        If reload_object is True, then the fields on the instance will
        be reloaded to reflect the current values.
        """
        cls._update_values(model_instance, values, reload_object, -1)

    @classmethod
    def _update_values(cls, model_instance, values, reload_object, multiplier):
        update_values = {}

        for attname, value in six.iteritems(values):
            if value != 0:
                update_values[attname] = F(attname) + value * multiplier

        cls._set_values(model_instance, update_values, reload_object)

    @classmethod
    def _set_values(cls, model_instance, values, reload_object=True):
        if values:
            queryset = model_instance.__class__.objects.filter(
                pk=model_instance.pk)
            queryset.update(**values)

            if reload_object:
                cls._reload_model_instance(model_instance,
                                           six.iterkeys(values))

    @classmethod
    def _reload_model_instance(cls, model_instance, attnames):
        """Reloads the value in this instance from the database."""
        q = model_instance.__class__.objects.filter(pk=model_instance.pk)
        values = q.values(*attnames)[0]

        for attname, value in six.iteritems(values):
            setattr(model_instance, attname, value)

    def __init__(self, verbose_name=None, name=None,
                 initializer=None, default=None, **kwargs):
        kwargs.update({
            'blank': True,
            'null': True,
        })

        super(CounterField, self).__init__(verbose_name, name, default=default,
                                           **kwargs)

        self._initializer = initializer
        self._locks = {}

    def increment(self, queryset, increment_by=1):
        """Increments this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) + increment_by})

    def decrement(self, queryset, decrement_by=1):
        """Decrements this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) - decrement_by})

    def contribute_to_class(self, cls, name):
        def _increment(model_instance, *args, **kwargs):
            self._increment(model_instance, *args, **kwargs)

        def _decrement(model_instance, *args, **kwargs):
            self._decrement(model_instance, *args, **kwargs)

        def _reload(model_instance):
            self._reload(model_instance)

        def _reinit(model_instance):
            self._reinit(model_instance)

        super(CounterField, self).contribute_to_class(cls, name)

        setattr(cls, 'increment_%s' % self.name, _increment)
        setattr(cls, 'decrement_%s' % self.name, _decrement)
        setattr(cls, 'reload_%s' % self.name, _reload)
        setattr(cls, 'reinit_%s' % self.name, _reinit)
        setattr(cls, self.attname, self)

        post_init.connect(self._post_init, sender=cls)

    def _increment(self, model_instance, reload_object=True, increment_by=1):
        """Increments this field by one."""
        if increment_by != 0:
            cls = model_instance.__class__
            self.increment(cls.objects.filter(pk=model_instance.pk),
                           increment_by)

            if reload_object:
                self._reload(model_instance)

    def _decrement(self, model_instance, reload_object=True, decrement_by=1):
        """Decrements this field by one."""
        if decrement_by != 0:
            cls = model_instance.__class__
            self.decrement(cls.objects.filter(pk=model_instance.pk),
                           decrement_by)

            if reload_object:
                self._reload(model_instance)

    def _reload(self, model_instance):
        """Reloads the value in this instance from the database."""
        self._reload_model_instance(model_instance, [self.attname])

    def _reinit(self, model_instance):
        """Re-initializes the value in the database from the initializer."""
        if not (model_instance.pk or self._initializer or
                six.callable(self._initializer)):
            # We don't want to end up defaulting this to 0 if creating a
            # new instance unless an initializer is provided. Instead,
            # we'll want to handle this the next time the object is
            # accessed.
            return

        value = 0

        if self._initializer:
            if isinstance(self._initializer, ExpressionNode):
                value = self._initializer
            elif six.callable(self._initializer):
                self._locks[model_instance] = 1
                value = self._initializer(model_instance)
                del self._locks[model_instance]

        if value is not None:
            is_expr = isinstance(value, ExpressionNode)

            if is_expr and not model_instance.pk:
                value = 0
                is_expr = False

            if is_expr:
                cls = model_instance.__class__
                cls.objects.filter(pk=model_instance.pk).update(**{
                    self.attname: value,
                })

                self._reload_model_instance(model_instance, [self.attname])
            else:
                setattr(model_instance, self.attname, value)

                if model_instance.pk:
                    model_instance.save(update_fields=[self.attname])

    def _post_init(self, instance=None, **kwargs):
        # Prevent the possibility of recursive lookups where this
        # same CounterField on this same instance tries to initialize
        # more than once. In this case, this will have the updated
        # value shortly.
        if instance and instance not in self._locks:
            self._do_post_init(instance)

    def _do_post_init(self, instance):
        value = self.value_from_object(instance)

        if value is None:
            reinit = getattr(instance, 'reinit_%s' % self.name)
            reinit()


class RelationCounterField(CounterField):
    """A field that provides an atomic count of a relation.

    RelationCounterField is a specialization of CounterField that tracks
    how many objects there are on the other side of a ManyToManyField or
    ForeignKey relation.

    RelationCounterField takes the name of a relation (either a field name,
    for a forward ManyToManyField relation, or the "related_name" for
    the reverse relation of another model's ForeignKey or ManyToManyField.
    (Note that using a forward ForeignKey relation is considered invalid,
    as the count can only be 1 or 0.)

    The counter will be initialized with the number of objects on the
    other side of the relation, and this will be kept updated so long as
    all updates to the table are made using standard create/save/delete
    operations on models.

    Note that updating a relation outside of a model's regular API (such as
    through raw SQL or something like an update() call) will cause the
    counters to get out of sync. They would then need to be reset using
    ``reinit_{field_name}``.
    """
    # Stores state across all instances of a RelationCounterField.
    #
    # Django doesn't make it easy to track updates to the other side of a
    # relation, meaning we have to do it ourselves. This dictionary will
    # weakly track InstanceState objects (which are tied to the lifecycle of
    # a particular model instancee). These objects are used to look up model
    # instances and their RelationCounterFields, given a model name, model
    # instance ID, and a relation name.
    _instance_states = weakref.WeakValueDictionary()

    # Stores instances we're tracking that haven't yet been saved.
    #
    # An unsaved instance may never be saved. We want to keep tabs on it
    # so we can disconnect any signal handlers if it ever falls out of
    # scope.
    #
    # Note that we're using a plain dictionary here, since we need to
    # control the weak references ourselves.
    _unsaved_instances = {}

    # Most of the hard work really lives in RelationTracker below. Here, we
    # store all registered instances of RelationTracker. There will be one
    # per model_cls/relation_name pair.
    _relation_trackers = {}

    class InstanceState(object):
        """Tracks state for a RelationCounterField assocation.

        State instances are bound to the lifecycle of a model instance.
        They keep track of the model instance (using a weak reference) and
        all RelationCounterFields tied to the relation name provided.

        These are used for looking up the proper instance and
        RelationCounterFields on the other end of a reverse relation, given
        a model, relation name, and IDs, through the _instance_states
        dictionary.
        """
        def __init__(self, model_instance, fields):
            self.model_instance_ref = weakref.ref(model_instance)
            self.fields = fields
            self.to_clear = set()

        @property
        def model_instance(self):
            return self.model_instance_ref()

        def reinit_fields(self):
            """Reinitializes all associated fields' counters."""
            model_instance = self.model_instance

            for field in self.fields:
                field._reinit(model_instance)

        def increment_fields(self, by=1):
            """Increments all associated fields' counters."""
            RelationCounterField.increment_many(
                self.model_instance,
                dict([(field.attname, by) for field in self.fields]))

        def decrement_fields(self, by=1):
            """Decrements all associated fields' counters."""
            RelationCounterField.decrement_many(
                self.model_instance,
                dict([(field.attname, by) for field in self.fields]))

        def zero_fields(self):
            """Zeros out all associated fields' counters."""
            RelationCounterField._set_values(
                self.model_instance,
                dict([(field.attname, 0) for field in self.fields]))

        def reload_fields(self):
            """Reloads all associated fields' counters."""
            RelationCounterField._reload_model_instance(
                self.model_instance,
                [field.attname for field in self.fields])

        def __repr__(self):
            return '<RelationCounterField.InstanceState for %s.pk=%s>' % (
                self.model_instance.__class__.__name__,
                self.model_instance.pk)

    class RelationTracker(object):
        """Tracks relations and updates state for all affected CounterFields.

        This class is responsible for all the hard work of updating
        RelationCounterFields refererring to a relation, based on updates
        to that relation. It's really the meat of RelationCounterField.

        Each RelationTracker is responsible for a given model/relation name
        pairing, across all instances of a model and across all
        RelationCounterFields following that relation name.

        The main reason the code lives here instead of in each
        RelationCounterField is to keep state better in sync and to ensure
        we're only ever dealing with one set of queries per relation name.
        We're also simplifying signal registration, helping to make things
        less error-prone.
        """
        def __init__(self, model_cls, rel_field_name):
            self._rel_field_name = rel_field_name
            self._rel_field, rel_model, is_rel_direct, is_m2m = \
                model_cls._meta.get_field_by_name(rel_field_name)

            self._is_rel_reverse = not is_rel_direct

            if not is_m2m and is_rel_direct:
                # This combination doesn't make any sense. There's only ever
                # one item on this side, so no point in counting. Let's just
                # complain about it.
                raise ValueError(
                    "RelationCounterField cannot work with the forward end of "
                    "a ForeignKey ('%s')"
                    % rel_field_name)

            dispatch_uid = '%s-%s.%s-related-save' % (
                id(self),
                self.__class__.__module__,
                self.__class__.__name__)

            if is_m2m:
                # This is going to be one end or the other of a ManyToManyField
                # relation.
                if is_rel_direct:
                    # This is a ManyToManyField, and we can get the 'rel'
                    # attribute through it.
                    m2m_field = self._rel_field
                    self._related_name = m2m_field.rel.related_name
                else:
                    # This is a RelatedObject. We need to get the field through
                    # this.
                    m2m_field = self._rel_field.field
                    self._related_name = m2m_field.attname

                # Listen for all M2M updates on the through table for this
                # ManyToManyField. Unfortunately, we can't look at a
                # particular instance, but we'll use state tracking to do the
                # necessary lookups and updates in the handler.
                m2m_changed.connect(
                    self._on_m2m_changed,
                    weak=False,
                    sender=m2m_field.rel.through,
                    dispatch_uid=dispatch_uid)
            else:
                # This is a ForeignKey or similar. It must be the reverse end.
                assert not is_rel_direct

                model = self._rel_field.model
                self._related_name = self._rel_field.field.attname

                # Listen for deletions and saves on that model type. In the
                # handler, we'll look up state for the other end of the
                # relation (the side owning this RelationCounterField), so that
                # we can update the counts.
                #
                # Unfortunately, we can't listen on the particular instance, so
                # we use the state tracking.
                post_delete.connect(
                    self._on_related_delete,
                    weak=False,
                    sender=model,
                    dispatch_uid=dispatch_uid)
                post_save.connect(
                    self._on_related_save,
                    weak=False,
                    sender=model,
                    dispatch_uid=dispatch_uid)

        def _on_m2m_changed(self, instance, action, reverse, model, pk_set,
                            **kwargs):
            """Handler for when a M2M relation has been updated.

            This will figure out the necessary operations that may need to be
            performed, given the update.

            For post_add/post_remove operations, it's pretty simple. We see
            if there are any instances (by way of stored state) for any of the
            affected IDs, and we re-initialize them.

            For clear operations, it's more tricky. We have to fetch all
            instances on the other side of the relation before any database
            changes are made, cache them in the InstanceState, and then update
            them all in post_clear.
            """
            if reverse != self._is_rel_reverse:
                # This doesn't match the direction we're paying attention to.
                # Ignore it.
                return

            is_post_clear = (action == 'post_clear')
            is_post_add = (action == 'post_add')
            is_post_remove = (action == 'post_remove')

            if is_post_clear or is_post_add or is_post_remove:
                state = RelationCounterField._get_state(
                    instance.__class__, instance.pk, self._rel_field_name)

                if state:
                    if is_post_add:
                        state.increment_fields(by=len(pk_set))
                    elif is_post_remove:
                        state.decrement_fields(by=len(pk_set))
                    elif is_post_clear:
                        state.zero_fields()

                    if not pk_set and is_post_clear:
                        # See the note below for 'pre_clear' for an explanation
                        # of why we're doing this.
                        pk_set = state.to_clear
                        state.to_clear = set()

                if pk_set:
                    # If any of the models have their own
                    # RelationCounterFields, make sure they've been updated to
                    # handle this side of things.
                    if is_post_add:
                        update_by = 1
                    else:
                        update_by = -1

                    # Update all RelationCounterFields on the other side of the
                    # relation that are referencing this relation.
                    self._update_counts(model, pk_set, '_related_name',
                                        update_by)

                    for pk in pk_set:
                        state = RelationCounterField._get_state(
                            model, pk, self._related_name)

                        if state:
                            state.reload_fields()
            elif action == 'pre_clear':
                # m2m_changed doesn't provide any information on affected IDs
                # for clear events (pre or post). We can, however, look up
                # these IDs ourselves, and if they match any existing
                # instances, we can re-initialize their counters in post_clear
                # above.
                #
                # We do this by fetching the IDs (without instantiating new
                # models) and storing it in the associated InstanceState. We'll
                # use those IDs above in the post_clear handler.
                state = RelationCounterField._get_state(
                    instance.__class__, instance.pk, self._rel_field_name)

                if state:
                    mgr = getattr(instance, self._rel_field_name)
                    state.to_clear.update(mgr.values_list('pk', flat=True))

        def _on_related_delete(self, instance, **kwargs):
            """Handler for when a ForeignKey relation is deleted.

            This will check if a model entry that has a ForeignKey relation
            to this field's parent model entry has been deleted from the
            database. If so, any associated counter fields on this end will be
            decremented.
            """
            state = self._get_reverse_foreign_key_state(instance)

            if state:
                state.decrement_fields()
            else:
                self._update_unloaded_fkey_rel_counts(instance, -1)

        def _on_related_save(self, instance=None, created=False, raw=False,
                             **kwargs):
            """Handler for when a ForeignKey relation is created.

            This will check if a model entry has been created that has a
            ForeignKey relation to this field's parent model entry. If so, any
            associated counter fields on this end will be decremented.
            """
            if raw or not created:
                return

            state = self._get_reverse_foreign_key_state(instance)

            if state:
                state.increment_fields()
            else:
                self._update_unloaded_fkey_rel_counts(instance, 1)

        def _update_unloaded_fkey_rel_counts(self, instance, by):
            """Updates unloaded model entry counters for a ForeignKey relation.

            This will get the ID of the model being referenced by the
            matching ForeignKey in the provided instance. If set, it will
            update all RelationCounterFields on that model that are tracking
            the ForeignKey.
            """
            rel_pk = getattr(instance, self._rel_field.field.attname)

            if rel_pk is not None:
                self._update_counts(self._rel_field.parent_model,
                                    [rel_pk], '_rel_field_name', by)

        def _update_counts(self, model_cls, pks, rel_attname, update_by):
            """Updates counts on all model entries matching the given criteria.

            This will update counts on all RelationCounterFields on all entries
            of the given model in the database that are tracking the given
            relation.
            """
            values = dict([
                (field.attname, F(field.attname) + update_by)
                for field in model_cls._meta.local_fields
                if (isinstance(field, RelationCounterField) and
                    (getattr(field._relation_tracker, rel_attname) ==
                        self._rel_field_name))
            ])

            if values:
                if len(pks) == 1:
                    q = Q(pk=list(pks)[0])
                else:
                    q = Q(pk__in=pks)

                model_cls.objects.filter(q).update(**values)

        def _get_reverse_foreign_key_state(self, instance):
            """Returns an InstanceState for the other end of a ForeignKey relation.

            This is used when listening to changes on models that establish a
            ForeignKey to this counter field's parent model. Given the instance
            on that end, we can get the state for this end.
            """
            return RelationCounterField._get_state(
                self._rel_field.parent_model,
                getattr(instance, self._rel_field.field.attname),
                self._rel_field_name)

    @classmethod
    def _reset_state(cls, instance):
        """Resets state for an instance.

        This will clear away any state tied to a particular instance ID. It's
        used to ensure that any old, removed entries (say, from a previous
        unit test) are cleared away before storing new state.
        """
        for key, state in list(six.iteritems(cls._instance_states)):
            if (state.model_instance.__class__ is instance.__class__ and
                state.model_instance.pk == instance.pk):
                del cls._instance_states[key]

    @classmethod
    def _store_state(cls, instance, field):
        """Stores state for a model instance and field.

        This constructs an InstanceState instance for the given model instance
        and RelationCounterField. It then associates it with the model instance
        and stores a weak reference to it in _instance_states.
        """
        assert instance.pk is not None

        key = (instance.__class__, instance.pk, field._rel_field_name)

        if key in cls._instance_states:
            cls._instance_states[key].fields.append(field)
        else:
            state = cls.InstanceState(instance, [field])
            setattr(instance, '_%s_state' % field.attname, state)
            cls._instance_states[key] = state

    @classmethod
    def _get_state(cls, model_cls, instance_id, rel_field_name):
        """Returns an InstanceState instance for the given parameters.

        If no InstanceState instance can be found that matches the
        parameters, None will be returned.
        """
        return cls._instance_states.get(
            (model_cls, instance_id, rel_field_name))

    def __init__(self, rel_field_name=None, *args, **kwargs):
        def _initializer(model_instance):
            if model_instance.pk:
                return getattr(model_instance, rel_field_name).count()
            else:
                return 0

        kwargs['initializer'] = _initializer

        super(RelationCounterField, self).__init__(*args, **kwargs)

        self._rel_field_name = rel_field_name
        self._relation_tracker = None

    def _do_post_init(self, instance):
        """Handles initialization of an instance of the parent model.

        This will begin the process of storing state about the model
        instance and listening to signals coming from the model on the
        other end of the relation.
        """
        super(RelationCounterField, self)._do_post_init(instance)

        cls = instance.__class__

        # We may not have a ID yet on the instance (as it may be a
        # newly-created instance not yet saved to the database). In this case,
        # we need to listen for the first save before storing the state.
        if instance.pk is None:
            instance_id = id(instance)
            dispatch_uid = '%s-%s.%s-first-save' % (
                instance_id,
                self.__class__.__module__,
                self.__class__.__name__)

            post_save.connect(
                lambda **kwargs: self._on_first_save(
                    instance_id, dispatch_uid=dispatch_uid, **kwargs),
                weak=False,
                sender=cls,
                dispatch_uid=dispatch_uid)

            self._unsaved_instances[instance_id] = weakref.ref(
                instance,
                lambda *args, **kwargs: self._on_unsaved_instance_destroyed(
                    cls, instance_id, dispatch_uid))
        else:
            RelationCounterField._store_state(instance, self)

        if not self._relation_tracker:
            key = (cls, self._rel_field_name)
            self._relation_tracker = \
                RelationCounterField._relation_trackers.get(key)

            if not self._relation_tracker:
                self._relation_tracker = \
                    self.RelationTracker(cls, self._rel_field_name)
                RelationCounterField._relation_trackers[key] = \
                    self._relation_tracker

    def _on_first_save(self, expected_instance_id, instance, dispatch_uid,
                       created=False, **kwargs):
        """Handler for the first save on a newly created instance.

        This will disconnect the signal and store the state on the instance.
        """
        if id(instance) == expected_instance_id:
            assert created

            # Stop listening immediately for any new signals here.
            # The Signal stuff deals with thread locks, so we shouldn't
            # have to worry about reaching any of this twice.
            post_save.disconnect(sender=instance.__class__,
                                 dispatch_uid=dispatch_uid)

            cls = self.__class__

            # This is a new row in the database (that is, the model instance
            # has been saved for the very first time), we need to flush any
            # existing state.
            #
            # The reason is that we may be running in a unit test situation, or
            # are dealing with code that deleted an entry and then saved a new
            # one with the old entry's PK explicitly assigned. Using the old
            # state will just cause problems.
            cls._reset_state(instance)

            # Now we can register each RelationCounterField on here.
            for field in instance.__class__._meta.local_fields:
                if isinstance(field, cls):
                    cls._store_state(instance, field)

    def _on_unsaved_instance_destroyed(self, cls, instance_id, dispatch_uid):
        """Handler for when an unsaved instance is destroyed.

        An unsaved instance would still have a signal connection set.
        We need to disconnect it to keep that connection from staying in
        memory indefinitely.
        """
        post_save.disconnect(sender=cls, dispatch_uid=dispatch_uid)

        del self._unsaved_instances[instance_id]
