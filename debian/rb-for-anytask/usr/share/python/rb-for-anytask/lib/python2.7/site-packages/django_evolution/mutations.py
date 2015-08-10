import copy

from django.db import models
from django.db.models.base import ModelState
from django.db.models.fields import AutoField, FieldDoesNotExist
from django.db.models.fields.related import (ForeignKey, ManyToManyField,
                                             RECURSIVE_RELATIONSHIP_CONSTANT)
from django.utils.datastructures import SortedDict
from django.utils.functional import curry

from django_evolution.db import EvolutionOperationsMulti
from django_evolution.db.sql_result import SQLResult
from django_evolution.errors import (CannotSimulate, SimulationFailure,
                                     EvolutionNotImplementedError)
from django_evolution.signature import (ATTRIBUTE_DEFAULTS,
                                        record_unique_together_applied)
from django_evolution.utils import get_database_for_model_name


FK_INTEGER_TYPES = [
    'AutoField', 'PositiveIntegerField', 'PositiveSmallIntegerField'
]


def create_field(proj_sig, field_name, field_type, field_attrs, parent_model):
    """
    Create an instance of a field from a field signature. This is useful for
    accessing all the database property mechanisms built into fields.
    """
    # related_model isn't a valid field attribute, so it must be removed
    # prior to instantiating the field, but it must be restored
    # to keep the signature consistent.
    related_model = field_attrs.pop('related_model', None)

    if related_model:
        related_app_name, related_model_name = related_model.split('.')
        related_model_sig = proj_sig[related_app_name][related_model_name]
        to = MockModel(proj_sig, related_app_name, related_model_name,
                       related_model_sig, stub=True)

        field = field_type(to, name=field_name, **field_attrs)
        field_attrs['related_model'] = related_model
    else:
        field = field_type(name=field_name, **field_attrs)

    if field_type is ManyToManyField and parent_model is not None:
        # Starting in Django 1.2, a ManyToManyField must have a through
        # model defined. This will be set internally to an auto-created
        # model if one isn't specified. We have to fake that model.
        through_model = field_attrs.get('through_model', None)
        through_model_sig = None

        if through_model:
            through_app_name, through_model_name = through_model.split('.')
            through_model_sig = proj_sig[through_app_name][through_model_name]
        elif hasattr(field, '_get_m2m_attr'):
            # Django >= 1.2
            to = field.rel.to._meta.object_name.lower()

            if (field.rel.to == RECURSIVE_RELATIONSHIP_CONSTANT or
                to == parent_model._meta.object_name.lower()):
                from_ = 'from_%s' % to
                to = 'to_%s' % to
            else:
                from_ = parent_model._meta.object_name.lower()

            # This corresponds to the signature in
            # related.create_many_to_many_intermediary_model
            through_app_name = parent_model.app_name
            through_model_name = '%s_%s' % (parent_model._meta.object_name,
                                            field.name)
            through_model = '%s.%s' % (through_app_name, through_model_name)

            fields = SortedDict()
            fields['id'] = {
                'field_type': AutoField,
                'primary_key': True,
            }

            fields[from_] = {
                'field_type': ForeignKey,
                'related_model': '%s.%s' % (parent_model.app_name,
                                            parent_model._meta.object_name),
                'related_name': '%s+' % through_model_name,
            }

            fields[to] = {
                'field_type': ForeignKey,
                'related_model': related_model,
                'related_name': '%s+' % through_model_name,
            }

            through_model_sig = {
                'meta': {
                    'db_table': field._get_m2m_db_table(parent_model._meta),
                    'managed': True,
                    'auto_created': True,
                    'app_label': through_app_name,
                    'unique_together': ((from_, to),),
                    'pk_column': 'id',
                },
                'fields': fields,
            }

            field.auto_created = True

        if through_model_sig:
            through = MockModel(proj_sig, through_app_name, through_model_name,
                                through_model_sig)
            field.rel.through = through

        field.m2m_db_table = curry(field._get_m2m_db_table, parent_model._meta)
        field.set_attributes_from_rel()

    field.set_attributes_from_name(field_name)

    return field


class MockMeta(object):
    """
    A mockup of a models Options object, based on the model signature.

    The stub argument is used to circumvent recursive relationships. If
    'stub' is provided, the constructed model will only be a stub -
    it will only have a primary key field.
    """
    def __init__(self, proj_sig, app_name, model_name, model_sig):
        self.object_name = model_name
        self.app_label = app_name
        self.meta = {
            'order_with_respect_to': None,
            'has_auto_field': None,
            'db_tablespace': None,
            'swapped': False,
        }
        self.meta.update(model_sig['meta'])
        self._fields = SortedDict()
        self._many_to_many = SortedDict()
        self.abstract = False
        self.managed = True
        self.proxy = False
        self._model_sig = model_sig
        self._proj_sig = proj_sig

    def setup_fields(self, model, stub=False):
        for field_name, field_sig in self._model_sig['fields'].items():
            if not stub or field_sig.get('primary_key', False):
                field_type = field_sig.pop('field_type')
                field = create_field(self._proj_sig, field_name, field_type,
                                     field_sig, model)

                if AutoField == type(field):
                    self.meta['has_auto_field'] = True
                    self.meta['auto_field'] = field

                field_sig['field_type'] = field_type

                if ManyToManyField == type(field):
                    self._many_to_many[field.name] = field
                else:
                    self._fields[field.name] = field

                field.set_attributes_from_name(field_name)
                if field_sig.get('primary_key', False):
                    self.pk = field

    def __getattr__(self, name):
        return self.meta[name]

    def get_field(self, name):
        try:
            return self._fields[name]
        except KeyError:
            try:
                return self._many_to_many[name]
            except KeyError:
                raise FieldDoesNotExist('%s has no field named %r' %
                                        (self.object_name, name))

    def get_field_by_name(self, name):
        return (self.get_field(name), None, True, None)

    def get_fields(self):
        return self._fields.values()

    def get_many_to_many_fields(self):
        return self._many_to_many.values()

    fields = property(fget=get_fields)
    local_fields = property(fget=get_fields)
    local_many_to_many = property(fget=get_many_to_many_fields)


class MockModel(object):
    """
    A mockup of a model object, providing sufficient detail
    to derive database column and table names using the standard
    Django fields.
    """
    def __init__(self, proj_sig, app_name, model_name, model_sig, stub=False,
                 db_name=None):
        self.app_name = app_name
        self.model_name = model_name
        self._meta = MockMeta(proj_sig, app_name, model_name, model_sig)
        self._meta.setup_fields(self, stub)
        self._state = ModelState(db_name)

    def __repr__(self):
        return '<MockModel for %s.%s>' % (self.app_name, self.model_name)

    def __eq__(self, other):
        # For our purposes, we don't want to appear equal to "self".
        # Really, Django 1.2 should be checking if this is a string before
        # doing this comparison,
        return (isinstance(other, MockModel) and
                self.app_name == other.app_name and
                self.model_name == other.model_name)


class MockRelated(object):
    """
    A mockup of django.db.models.related.RelatedObject, providing
    sufficient detail to derive database column and table names using
    the standard Django fields.
    """
    def __init__(self, related_model, model, field):
        self.parent_model = related_model
        self.model = model
        self.opts = model._meta
        self.field = field
        self.name = '%s:%s' % (model.app_name, model.model_name)
        self.var_name = model.model_name.lower()


class BaseMutation(object):
    def __init__(self):
        pass

    def mutate(self, mutator):
        """
        Performs the mutation on the database. Database changes will occur
        after this function is invoked.
        """
        raise NotImplementedError()

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        """
        Performs a simulation of the mutation to be performed. The purpose of
        the simulate function is to ensure that after all mutations have
        occured the database will emerge in a state consistent with the
        currently loaded models file.
        """
        raise NotImplementedError()

    def is_mutable(self, app_label, proj_sig, database_sig, database):
        """
        test if the current mutation could be applied to the given database
        """
        return False

    def __repr__(self):
        return '<%s>' % str(self)


class MonoBaseMutation(BaseMutation):
    # introducting model_name at this stage will prevent subclasses to be
    # cross databases
    def __init__(self, model_name=None):
        super(MonoBaseMutation, self).__init__()
        self.model_name = model_name

    def evolver(self, model, database_sig, database=None):
        if database is None:
            database = get_database_for_model_name(model.app_label,
                                                   model.model_name)

        return EvolutionOperationsMulti(database, database_sig).get_evolver()

    def is_mutable(self, app_label, proj_sig, database_sig, database):
        db_name = (database or
                   get_database_for_model_name(app_label, self.model_name))
        return db_name and db_name == database


class SQLMutation(BaseMutation):
    def __init__(self, tag, sql, update_func=None):
        self.tag = tag
        self.sql = sql
        self.update_func = update_func

    def __str__(self):
        return "SQLMutation('%s')" % self.tag

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        """SQL mutations cannot be simulated unless an update function is
        provided"""

        if callable(self.update_func):
            self.update_func(app_label, proj_sig)
        else:
            raise CannotSimulate('Cannot simulate SQLMutations')

    def mutate(self, mutator):
        "The mutation of an SQL mutation returns the raw SQL"
        mutator.add_sql(self, self.sql)

    def is_mutable(self, app_label, proj_sig, database_sig, database):
        return True


class MutateModelField(MonoBaseMutation):
    """Base class for any fields that mutate a model.

    This is used for classes that perform any mutation on a model.
    Such mutations will be provided a model they can work with.

    Operations added to the mutator by this field will be associated with
    that model. That will allow the operations backend to perform any
    optimizations to improve evolution time for the model.
    """
    def mutate(self, mutator, model):
        raise NotImplementedError


class DeleteField(MutateModelField):
    def __init__(self, model_name, field_name):
        super(DeleteField, self).__init__(model_name)
        self.field_name = field_name

    def __str__(self):
        return "DeleteField('%s', '%s')" % (self.model_name, self.field_name)

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.model_name]

        # If the field was used in the unique_together attribute, update it.
        unique_together = model_sig['meta']['unique_together']
        unique_together_list = []

        for ut_index in range(0, len(unique_together), 1):
            ut = unique_together[ut_index]
            unique_together_fields = []

            for field_name_index in range(0, len(ut), 1):
                field_name = ut[field_name_index]

                if not field_name == self.field_name:
                    unique_together_fields.append(field_name)

            unique_together_list.append(tuple(unique_together_fields))

        model_sig['meta']['unique_together'] = tuple(unique_together_list)

        if model_sig['fields'][self.field_name].get('primary_key', False):
            raise SimulationFailure('Cannot delete a primary key.')

        # Simulate the deletion of the field.
        try:
            model_sig['fields'].pop(self.field_name)
        except KeyError:
            raise SimulationFailure('Cannot find the field named "%s".'
                                    % self.field_name)

    def mutate(self, mutator, model):
        field_sig = mutator.model_sig['fields'][self.field_name]

        # Temporarily remove field_type from the field signature
        # so that we can create a field
        field_type = field_sig.pop('field_type')
        field = create_field(mutator.proj_sig, self.field_name, field_type,
                             field_sig, model)
        field_sig['field_type'] = field_type

        if field_type is models.ManyToManyField:
            mutator.add_sql(
                self,
                mutator.evolver.delete_table(
                    field._get_m2m_db_table(model._meta)))
        else:
            mutator.delete_column(self, field)


class AddField(MutateModelField):
    def __init__(self, model_name, field_name, field_type,
                 initial=None, **kwargs):
        super(AddField, self).__init__(model_name)
        self.field_name = field_name
        self.field_type = field_type
        self.field_attrs = kwargs
        self.initial = initial

    def __str__(self):
        if self.field_type.__module__.startswith('django.db.models'):
            field_prefix = 'models.'
        else:
            field_prefix = ''

        str_output = ["'%(model_name)s', '%(field_name)s', %(field_type)s" % {
            'model_name': self.model_name,
            'field_name': self.field_name,
            'field_type': field_prefix + self.field_type.__name__
        }]

        if self.initial is not None:
            if isinstance(self.initial, basestring):
                value = unicode(self.initial)
            else:
                value = self.initial

            str_output.append('initial=%s' % repr(value))

        for key, value in self.field_attrs.iteritems():
            str_output.append("%s=%s" % (key, repr(value)))

        return 'AddField(' + ', '.join(str_output) + ')'

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.model_name]

        if self.field_name in model_sig['fields']:
            raise SimulationFailure(
                "Model '%s.%s' already has a field named '%s'"
                % (app_label, self.model_name, self.field_name))

        if (self.field_type is not models.ManyToManyField and
            not self.field_attrs.get('null', ATTRIBUTE_DEFAULTS['null'])
            and self.initial is None):
            raise SimulationFailure(
                "Cannot create new column '%s' on '%s.%s' without a "
                "non-null initial value."
                % (self.field_name, app_label, self.model_name))

        model_sig['fields'][self.field_name] = {
            'field_type': self.field_type,
        }

        model_sig['fields'][self.field_name].update(self.field_attrs)

    def mutate(self, mutator, model):
        if self.field_type is models.ManyToManyField:
            self.add_m2m_table(mutator, model)
        else:
            self.add_column(mutator, model)

    def add_column(self, mutator, model):
        field = create_field(mutator.proj_sig, self.field_name,
                             self.field_type, self.field_attrs, model)

        mutator.add_column(self, field, self.initial)

    def add_m2m_table(self, mutator, model):
        field = create_field(mutator.proj_sig, self.field_name,
                             self.field_type, self.field_attrs, model)

        related_app_label, related_model_name = \
            self.field_attrs['related_model'].split('.')
        related_sig = mutator.proj_sig[related_app_label][related_model_name]
        related_model = MockModel(mutator.proj_sig, related_app_label,
                                  related_model_name, related_sig,
                                  mutator.database)
        related = MockRelated(related_model, model, field)

        if hasattr(field, '_get_m2m_column_name'):
            # Django < 1.2
            field.m2m_column_name = \
                curry(field._get_m2m_column_name, related)
            field.m2m_reverse_name = \
                curry(field._get_m2m_reverse_name, related)
        else:
            # Django >= 1.2
            field.m2m_column_name = curry(field._get_m2m_attr,
                                          related, 'column')
            field.m2m_reverse_name = curry(field._get_m2m_reverse_attr,
                                           related, 'column')

        mutator.add_sql(self, mutator.evolver.add_m2m_table(model, field))


class RenameField(MutateModelField):
    def __init__(self, model_name, old_field_name, new_field_name,
                 db_column=None, db_table=None):
        super(RenameField, self).__init__(model_name)
        self.old_field_name = old_field_name
        self.new_field_name = new_field_name
        self.db_column = db_column
        self.db_table = db_table

    def __str__(self):
        params = "'%s', '%s', '%s'" % (self.model_name, self.old_field_name,
                                       self.new_field_name)

        if self.db_column:
            params = params + ", db_column='%s'" % (self.db_column)
        if self.db_table:
            params = params + ", db_table='%s'" % (self.db_table)

        return "RenameField(%s)" % params

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.model_name]
        field_dict = model_sig['fields']
        field_sig = field_dict[self.old_field_name]

        if models.ManyToManyField == field_sig['field_type']:
            if self.db_table:
                field_sig['db_table'] = self.db_table
            else:
                field_sig.pop('db_table', None)
        elif self.db_column:
            field_sig['db_column'] = self.db_column
        else:
            # db_column and db_table were not specified (or not specified for
            # the appropriate field types). Clear the old value if one was set.
            # This amounts to resetting the column or table name to the Django
            # default name
            field_sig.pop('db_column', None)

        field_dict[self.new_field_name] = field_dict.pop(self.old_field_name)

    def mutate(self, mutator, model):
        old_field_sig = mutator.model_sig['fields'][self.old_field_name]

        # Temporarily remove the field type so that we can create mock field
        # instances
        field_type = old_field_sig.pop('field_type')

        # Duplicate the old field sig, and apply the table/column changes
        new_field_sig = copy.copy(old_field_sig)

        if field_type is models.ManyToManyField:
            if self.db_table:
                new_field_sig['db_table'] = self.db_table
            else:
                new_field_sig.pop('db_table', None)
        elif self.db_column:
            new_field_sig['db_column'] = self.db_column
        else:
            new_field_sig.pop('db_column', None)

        # Create the mock field instances.
        old_field = create_field(mutator.proj_sig, self.old_field_name,
                                 field_type, old_field_sig, None)
        new_field = create_field(mutator.proj_sig, self.new_field_name,
                                 field_type, new_field_sig, None)

        # Restore the field type to the signature
        old_field_sig['field_type'] = field_type

        new_model = MockModel(mutator.proj_sig, mutator.app_label,
                              self.model_name, mutator.model_sig,
                              db_name=mutator.database)
        evolver = mutator.evolver

        if field_type is models.ManyToManyField:
            old_m2m_table = old_field._get_m2m_db_table(new_model._meta)
            new_m2m_table = new_field._get_m2m_db_table(new_model._meta)

            sql = evolver.rename_table(new_model, old_m2m_table, new_m2m_table)
        else:
            sql = evolver.rename_column(new_model, old_field, new_field)

        mutator.add_sql(self, sql)


class ChangeField(MutateModelField):
    def __init__(self, model_name, field_name, initial=None, **kwargs):
        super(ChangeField, self).__init__(model_name)
        self.field_name = field_name
        self.field_attrs = kwargs
        self.initial = initial

    def __str__(self):
        params = (self.model_name, self.field_name)
        str_output = ["'%s', '%s'" % params]

        str_output.append('initial=%s' % repr(self.initial))

        for attr_name, attr_value in self.field_attrs.items():
            if str == type(attr_value):
                str_attr_value = "'%s'" % attr_value
            else:
                str_attr_value = str(attr_value)

            str_output.append('%s=%s' % (attr_name, str_attr_value,))

        return 'ChangeField(' + ', '.join(str_output) + ')'

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.model_name]
        field_sig = model_sig['fields'][self.field_name]

        # Catch for no-op changes.
        for field_attr, attr_value in self.field_attrs.items():
            field_sig[field_attr] = attr_value

        if ('null' in self.field_attrs and
            field_sig['field_type'] != models.ManyToManyField and
            not self.field_attrs['null'] and
            self.initial is None):
            raise SimulationFailure(
                "Cannot change column '%s' on '%s.%s' without a "
                "non-null initial value."
                % (self.field_name, app_label, self.model_name))

    def mutate(self, mutator, model):
        field_sig = mutator.model_sig['fields'][self.field_name]
        field = model._meta.get_field(self.field_name)

        for attr_name in self.field_attrs.iterkeys():
            if attr_name not in mutator.evolver.supported_change_attrs:
                raise EvolutionNotImplementedError(
                    "ChangeField does not support modifying the '%s' "
                    "attribute on '%s.%s'."
                    % (attr_name, self.model_name, self.field_name))

        new_field_attrs = {}

        for attr_name, attr_value in self.field_attrs.iteritems():
            old_attr_value = field_sig.get(attr_name,
                                           ATTRIBUTE_DEFAULTS[attr_name])

            # Avoid useless SQL commands if nothing has changed.
            if old_attr_value != attr_value:
                new_field_attrs[attr_name] = {
                    'old_value': old_attr_value,
                    'new_value': attr_value,
                }

        if new_field_attrs:
            mutator.change_column(self, field, new_field_attrs)


class RenameModel(MutateModelField):
    def __init__(self, old_model_name, new_model_name, db_table):
        super(RenameModel, self).__init__(old_model_name)
        self.old_model_name = old_model_name
        self.new_model_name = new_model_name
        self.db_table = db_table

    def __str__(self):
        params = "'%s', '%s'" % (self.old_model_name, self.new_model_name)

        if self.db_table:
            params += ", db_table='%s'" % self.db_table

        return 'RenameModel(%s)' % params

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.old_model_name]

        if self.db_table:
            model_sig['meta']['db_table'] = self.db_table
        else:
            # db_table was not specified. Clear the old value if one was set.
            # This amounts to resetting the column or table name to the Django
            # default name.
            model_sig['meta'].pop('db_table', None)

        app_sig[self.new_model_name] = app_sig.pop(self.old_model_name)

        old_related_model = '%s.%s' % (app_label, self.old_model_name)
        new_related_model = '%s.%s' % (app_label, self.new_model_name)

        for app_sig in proj_sig.itervalues():
            if not isinstance(app_sig, dict):
                continue

            for model_sig in app_sig.itervalues():
                for field in model_sig['fields'].itervalues():
                    if ('related_model' in field and
                        field['related_model'] == old_related_model):
                        field['related_model'] = new_related_model

    def mutate(self, mutator, model):
        old_model_sig = mutator.model_sig
        new_model_sig = copy.deepcopy(old_model_sig)

        new_model_sig['meta']['db_table'] = self.db_table

        new_model = MockModel(mutator.proj_sig, mutator.app_label,
                              self.new_model_name, new_model_sig,
                              db_name=mutator.database)
        evolver = mutator.evolver

        sql = evolver.rename_table(new_model,
                                   old_model_sig['meta']['db_table'],
                                   new_model_sig['meta']['db_table'])

        mutator.add_sql(self, sql)


class DeleteModel(MutateModelField):
    def __str__(self):
        return "DeleteModel(%r)" % self.model_name

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        app_sig = proj_sig[app_label]

        # Simulate the deletion of the model.
        del app_sig[self.model_name]

    def mutate(self, mutator, model):
        sql_result = SQLResult()

        # Remove any many to many tables.
        for field_name, field_sig in mutator.model_sig['fields'].items():
            if field_sig['field_type'] is models.ManyToManyField:
                field = model._meta.get_field(field_name)
                m2m_table = field._get_m2m_db_table(model._meta)
                sql_result.add(mutator.evolver.delete_table(m2m_table))

        # Remove the table itself.
        sql_result.add(mutator.evolver.delete_table(model._meta.db_table))

        mutator.add_sql(self, sql_result)


class DeleteApplication(BaseMutation):
    def __str__(self):
        return 'DeleteApplication()'

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        if database:
            app_sig = proj_sig[app_label]

            # Simulate the deletion of the models.
            for model_name in app_sig.keys():
                mutation = DeleteModel(model_name)

                if mutation.is_mutable(app_label, proj_sig, database_sig,
                                       database):
                    del app_sig[model_name]

    def mutate(self, mutator):
        # This test will introduce a regression, but we can't afford to remove
        # all models at a same time if they aren't owned by the same database
        if mutator.database:
            app_sig = mutator.proj_sig[mutator.app_label]

            for model_name in app_sig.keys():
                mutation = DeleteModel(model_name)

                if mutation.is_mutable(mutator.app_label, mutator.proj_sig,
                                       mutator.database_sig,
                                       mutator.database):
                    mutator.run_mutation(mutation)

    def is_mutable(self, app_label, proj_sig, database_sig, database):
        # the test is done in the mutate method above. We can return True
        return True


class ChangeMeta(MutateModelField):
    def __init__(self, model_name, prop_name, new_value):
        super(ChangeMeta, self).__init__(model_name)
        self.prop_name = prop_name
        self.new_value = new_value

    def __str__(self):
        return ("ChangeMeta('%s', '%s', %r)"
                % (self.model_name, self.prop_name, self.new_value))

    def simulate(self, app_label, proj_sig, database_sig, database=None):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.model_name]

        model_sig['meta'][self.prop_name] = self.new_value

        if self.prop_name == 'unique_together':
            record_unique_together_applied(model_sig)

    def mutate(self, mutator, model):
        if self.prop_name not in mutator.evolver.supported_change_meta:
            raise EvolutionNotImplementedError(
                "ChangeMeta does not support modifying the '%s' "
                "attribute on '%s'."
                % (self.prop_name, self.model_name))

        mutator.change_meta(self, self.prop_name, self.new_value)
