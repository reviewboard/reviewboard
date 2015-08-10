import copy
import logging
from datetime import datetime

import django
from django.conf import settings
from django.core.management import sql
from django.core.management.color import no_style
from django.db import connection, connections, transaction, models
from django.db.backends.util import truncate_name
from django.db.models.loading import cache
from django.db.utils import DEFAULT_DB_ALIAS
from django.utils.datastructures import SortedDict
from django.utils.functional import curry

from django_evolution import signature
from django_evolution.db import EvolutionOperationsMulti
from django_evolution.signature import rescan_indexes_for_database_sig
from django_evolution.tests import models as evo_test
from django_evolution.utils import write_sql, execute_sql


DEFAULT_TEST_ATTRIBUTE_VALUES = {
    models.CharField: 'TestCharField',
    models.IntegerField: '123',
    models.AutoField: None,
    models.DateTimeField: datetime.now(),
    models.PositiveIntegerField: '42'
}


digest = connection.creation._digest


def wrap_sql_func(func, evo_test, style, db_name=None):
    return func(evo_test, style, connections[db_name or DEFAULT_DB_ALIAS])

# Wrap the sql.* functions to work with the multi-db support
sql_create = curry(wrap_sql_func, sql.sql_create)
sql_indexes = curry(wrap_sql_func, sql.sql_indexes)
sql_delete = curry(wrap_sql_func, sql.sql_delete)


def set_model_name(model, name):
    if hasattr(model._meta, 'model_name'):
        model._meta.model_name = name
    else:
        model._meta.module_name = name


def get_model_name(model):
    if hasattr(model._meta, 'model_name'):
        return model._meta.model_name
    else:
        return model._meta.module_name


def _register_models(database_sig, app_label='tests', db_name='default',
                     *models, **kwargs):
    app_cache = SortedDict()
    evolver = EvolutionOperationsMulti(db_name, database_sig).get_evolver()
    register_indexes = kwargs.get('register_indexes', False)

    my_connection = connections[db_name or DEFAULT_DB_ALIAS]
    max_name_length = my_connection.ops.max_name_length()

    for name, model in reversed(models):
        orig_model_name = get_model_name(model)

        if orig_model_name in cache.app_models['django_evolution']:
            del cache.app_models['django_evolution'][orig_model_name]

        orig_db_table = model._meta.db_table
        orig_object_name = model._meta.object_name

        generated_db_table = truncate_name(
            '%s_%s' % (model._meta.app_label, orig_model_name),
            max_name_length)

        if orig_db_table.startswith(generated_db_table):
            model._meta.db_table = '%s_%s' % (app_label, name.lower())

        model._meta.db_table = truncate_name(model._meta.db_table,
                                             max_name_length)
        model._meta.app_label = app_label
        model._meta.object_name = name
        model_name = name.lower()
        set_model_name(model, model_name)

        # Add an entry for the table in database_sig, if it's not already
        # there.
        if model._meta.db_table not in database_sig:
            database_sig[model._meta.db_table] = \
                signature.create_empty_database_table_sig()

        if register_indexes:
            # Now that we definitely have an entry, store the indexes for
            # all the fields in database_sig, so that other operations can
            # look up the index names.
            for field in model._meta.local_fields:
                if field.db_index or field.unique:
                    index_name = evolver.get_default_index_name(
                        model._meta.db_table, field)

                    signature.add_index_to_database_sig(
                        evolver, database_sig, model, [field],
                        index_name=index_name,
                        unique=field.unique)

            for field_names in model._meta.unique_together:
                signature.add_index_to_database_sig(
                    evolver, database_sig, model,
                    evolver.get_fields_for_names(model, field_names),
                    index_name=field_names[0],
                    unique=True)

            for field_names in getattr(model._meta, 'index_together', []):
                fields = evolver.get_fields_for_names(model, field_names)
                index_name = evolver.get_default_index_together_name(
                    model._meta.db_table, fields)

                signature.add_index_to_database_sig(
                    evolver, database_sig, model,
                    fields,
                    index_name=index_name)

        # Register the model with the app.
        add_app_test_model(model, app_label=app_label)

        for field in model._meta.local_many_to_many:
            if not field.rel.through:
                continue

            through = field.rel.through

            generated_db_table = truncate_name(
                '%s_%s' % (orig_db_table, field.name),
                max_name_length)

            if through._meta.db_table == generated_db_table:
                through._meta.app_label = app_label

                # Transform the 'through' table information only
                # if we've transformed the parent db_table.
                if model._meta.db_table != orig_db_table:
                    through._meta.db_table = \
                        '%s_%s' % (model._meta.db_table, field.name)

                    through._meta.object_name = \
                        through._meta.object_name.replace(
                            orig_object_name,
                            model._meta.object_name)

                    set_model_name(
                        through,
                        get_model_name(through).replace(orig_model_name,
                                                        model_name))

            through._meta.db_table = \
                truncate_name(through._meta.db_table, max_name_length)

            for field in through._meta.local_fields:
                if field.rel and field.rel.to:
                    column = field.column

                    if (column.startswith(orig_model_name) or
                        column.startswith('to_%s' % orig_model_name) or
                        column.startswith('from_%s' % orig_model_name)):

                        field.column = column.replace(
                            orig_model_name,
                            get_model_name(model))

            through_model_name = get_model_name(through)

            if through_model_name in cache.app_models['django_evolution']:
                del cache.app_models['django_evolution'][through_model_name]

            app_cache[through_model_name] = through
            add_app_test_model(through, app_label=app_label)

        app_cache[model_name] = model

    if evo_test not in cache.app_store:
        cache.app_store[evo_test] = len(cache.app_store)

        if hasattr(cache, 'app_labels'):
            cache.app_labels[app_label] = evo_test

    return app_cache


def register_models(database_sig, *models, **kwargs):
    return _register_models(database_sig, 'tests', 'default', *models,
                            **kwargs)


def register_models_multi(database_sig, app_label, db_name, *models, **kwargs):
    return _register_models(database_sig, app_label, db_name, *models,
                            **kwargs)


def _test_proj_sig(app_label, *models, **kwargs):
    "Generate a dummy project signature based around a single model"
    version = kwargs.get('version', 1)
    proj_sig = {
        app_label: SortedDict(),
        '__version__': version,
    }

    # Compute the project siguature
    for full_name, model in models:
        parts = full_name.split('.')

        if len(parts) == 1:
            name = parts[0]
            app = app_label
        else:
            app, name = parts

        proj_sig.setdefault(app, SortedDict())[name] = \
            signature.create_model_sig(model)

    return proj_sig


def create_test_proj_sig(*models, **kwargs):
    return _test_proj_sig('tests', *models, **kwargs)


def create_test_proj_sig_multi(app_label, *models, **kwargs):
    return _test_proj_sig(app_label, *models, **kwargs)

# XXX Legacy names for these functions
test_proj_sig = create_test_proj_sig
test_proj_sig_multi = create_test_proj_sig_multi


def execute_transaction(sql, output=False, database='default'):
    "A transaction wrapper for executing a list of SQL statements"
    my_connection = connection
    out_sql = []

    if not database:
        database = DEFAULT_DB_ALIAS

    my_connection = connections[database]
    using_args = {
        'using': database,
    }

    try:
        # Begin Transaction
        transaction.enter_transaction_management(**using_args)
        transaction.managed(True, **using_args)

        cursor = my_connection.cursor()

        # Perform the SQL
        if output:
            out_sql.extend(write_sql(sql, database))

        execute_sql(cursor, sql, database)

        transaction.commit(**using_args)
        transaction.leave_transaction_management(**using_args)
    except Exception, e:
        logging.error('Error executing SQL %s: %s' % (sql, e))
        transaction.rollback(**using_args)
        raise

    return out_sql


def execute_test_sql(start, end, sql, debug=False, app_label='tests',
                     database='default', database_sig=None, return_sql=False,
                     rescan_indexes=True):
    """
    Execute a test SQL sequence. This method also creates and destroys the
    database tables required by the models registered against the test
    application.

    start and end are the start- and end-point states of the application cache.

    sql is the list of sql statements to execute.

    cleanup is a list of extra sql statements required to clean up. This is
    primarily for any extra m2m tables that were added during a test that won't
    be cleaned up by Django's sql_delete() implementation.

    debug is a helper flag. It displays the ALL the SQL that would be executed,
    (including setup and teardown SQL), and executes the Django-derived
    setup/teardown SQL.
    """
    out_sql = []

    # Set up the initial state of the app cache
    set_app_test_models(copy.deepcopy(start), app_label=app_label)

    # Install the initial tables and indicies
    style = no_style()
    execute_transaction(sql_create(evo_test, style, database),
                        output=debug, database=database)
    execute_transaction(sql_indexes(evo_test, style, database),
                        output=debug, database=database)

    if rescan_indexes and database_sig:
        rescan_indexes_for_database_sig(database_sig, database)

    create_test_data(models.get_models(evo_test), database)

    # Set the app cache to the end state
    set_app_test_models(copy.deepcopy(end), app_label=app_label)

    try:
        if callable(sql):
            sql = sql()

        # Execute the test sql
        if debug:
            out_sql.extend(write_sql(sql, database))
        else:
            out_sql.extend(execute_transaction(sql, output=True,
                                               database=database))
    finally:
        # Cleanup the apps.
        delete_sql = sql_delete(evo_test, style, database)

        if debug:
            out_sql.append(delete_sql)
        else:
            out_sql.extend(execute_transaction(delete_sql, output=False,
                                               database=database))

    # This is a terrible hack, but it's necessary while we use doctests
    # and normal unit tests. If we always return the SQL, then the
    # doctests will expect us to compare the output of that (along with the
    # print statements).
    #
    # Down the road, everything should be redone to be standard unit tests,
    # and then we can just compare the returned SQL statements instead of
    # dealing with anything on stdout.
    if return_sql:
        return out_sql
    else:
        return None


def create_test_data(app_models, database):
    deferred_models = []
    deferred_fields = {}
    using_args = {
        'using': database,
    }

    for model in app_models:
        params = {}
        deferred = False

        for field in model._meta.fields:
            if not deferred:
                if type(field) in (models.ForeignKey, models.ManyToManyField):
                    related_model = field.rel.to
                    related_q = related_model.objects.all().using(database)

                    if related_q.count():
                        related_instance = related_q[0]
                    elif field.null is False:
                        # Field cannot be null yet the related object
                        # hasn't been created yet Defer the creation of
                        # this model
                        deferred = True
                        deferred_models.append(model)
                    else:
                        # Field cannot be set yet but null is acceptable
                        # for the moment
                        deferred_fields[type(model)] = \
                            deferred_fields.get(type(model),
                                                []).append(field)
                        related_instance = None

                    if not deferred:
                        if type(field) is models.ForeignKey:
                            params[field.name] = related_instance
                        else:
                            params[field.name] = [related_instance]
                else:
                    params[field.name] = \
                        DEFAULT_TEST_ATTRIBUTE_VALUES[type(field)]

        if not deferred:
            model(**params).save(**using_args)

    # Create all deferred models.
    if deferred_models:
        create_test_data(deferred_models, database)

    # All models should be created (Not all deferred fields have been populated
    # yet) Populate deferred fields that we know about.  Here lies untested
    # code!
    if deferred_fields:
        for model, field_list in deferred_fields.items():
            for field in field_list:
                related_model = field.rel.to
                related_instance = related_model.objects.using(database)[0]

                if type(field) is models.ForeignKey:
                    setattr(model, field.name, related_instance)
                else:
                    getattr(model, field.name).add(related_instance,
                                                   **using_args)

            model.save(**using_args)


def test_sql_mapping(test_field_name, db_name='default'):
    engine = settings.DATABASES[db_name]['ENGINE'].split('.')[-1]

    sql_for_engine = __import__('django_evolution.tests.db.%s' % (engine),
                                {}, {}, [''])

    return getattr(sql_for_engine, test_field_name)


def deregister_models(app_label='tests'):
    "Clear the test section of the app cache"
    del cache.app_models[app_label]
    clear_models_cache()


def clear_models_cache():
    """Clears the Django models cache.

    This cache is used in Django >= 1.2 to quickly return results from
    cache.get_models(). It needs to be cleared when modifying the model
    registry.
    """
    if hasattr(cache, '_get_models_cache'):
        # On Django 1.2, we need to clear this cache when unregistering models.
        cache._get_models_cache.clear()


def set_app_test_models(models, app_label):
    """Sets the list of models in the Django test models registry."""
    cache.app_models[app_label] = models
    clear_models_cache()


def add_app_test_model(model, app_label):
    """Adds a model to the Django test models registry."""
    key = model._meta.object_name.lower()
    cache.app_models.setdefault(app_label, SortedDict())[key] = model
    clear_models_cache()


def generate_index_name(table, col_names, field_names=None, default=True):
    """Generates a suitable index name to test against.

    If default is True, then this will be a default index name for the
    given database. Otherwise, it will use an index name generated by
    Django Evolution.
    """
    if not isinstance(col_names, list):
        col_names = [col_names]

    if field_names and not isinstance(field_names, list):
        field_names = [field_names]

    if default:
        # Note that we're checking Django versions specifically, since we
        # want to test that we're getting the right index names for the
        # right versions of Django.
        if django.VERSION >= (1, 5):
            name = digest(field_names or col_names)
        elif django.VERSION >= (1, 2):
            name = digest(col_names[0])
        else:
            name = col_names[0]
    else:
        # This is a name created by Django Evolution, so follow the format
        # in get_new_index_name in the evolver.
        name = digest(*(field_names or col_names))

    return '%s_%s' % (table, name)


def has_index_with_columns(database_sig, table_name, columns, unique=False):
    """Returns whether there's an index with the given criteria.

    This looks in the database signature for an index for the given table,
    column names, and with the given uniqueness flag. It will return a boolean
    indicating if one was found.
    """
    assert table_name in database_sig

    for index_info in database_sig[table_name]['indexes'].itervalues():
        if index_info['columns'] == columns and index_info['unique'] == unique:
            return True

    return False


def generate_constraint_name(r_col, col, r_table, table):
    return '%s_refs_%s_%s' % (r_col, col, digest(r_table, table))
