import copy
import logging

from django.core.management import color
from django.db import connection as default_connection
from django.db.backends.util import truncate_name

from django_evolution.db.sql_result import AlterTableSQLResult, SQLResult
from django_evolution.errors import EvolutionNotImplementedError
from django_evolution.signature import (add_index_to_database_sig,
                                        remove_index_from_database_sig)
from django_evolution.support import supports_index_together


class BaseEvolutionOperations(object):
    supported_change_attrs = (
        'null', 'max_length', 'db_column', 'db_index', 'db_table', 'unique',
    )

    supported_change_meta = ('index_together', 'unique_together')

    mergeable_ops = (
        'add_column', 'change_column', 'delete_column', 'change_meta'
    )

    def __init__(self, database_sig, connection=default_connection):
        self.database_sig = database_sig
        self.connection = connection

    def generate_table_ops_sql(self, mutator, ops):
        """Generates SQL for a sequence of mutation operations.

        This will process each operation one-by-one, generating default SQL,
        using generate_table_op_sql().
        """
        sql_results = []
        prev_sql_result = None
        prev_op = None

        for op in ops:
            sql_result = self.generate_table_op_sql(mutator, op,
                                                    prev_sql_result, prev_op)

            if sql_result is not prev_sql_result:
                sql_results.append(sql_result)
                prev_sql_result = sql_result

            prev_op = op

        sql = []

        for sql_result in sql_results:
            sql.extend(sql_result.to_sql())

        return sql

    def generate_table_op_sql(self, mutator, op, prev_sql_result, prev_op):
        """Generates SQL for a single mutation operation.

        This will call different SQL-generating functions provided by the
        class, depending on the details of the operation.

        If two adjacent operations can be merged together (meaning that
        they can be turned into one ALTER TABLE statement), they'll be placed
        in the same AlterTableSQLResult.
        """
        model = mutator.create_model()

        op_type = op['type']
        mutation = op['mutation']

        if prev_op and self._are_ops_mergeable(prev_op, op):
            sql_result = prev_sql_result
        else:
            sql_result = AlterTableSQLResult(self, model)

        if op_type == 'add_column':
            field = op['field']
            sql_result.add(self.add_column(model, field, op['initial']))
            sql_result.add(self.create_index(model, field))
        elif op_type == 'change_column':
            sql_result.add(self.change_column_attrs(model, mutation,
                                                    op['field'].name,
                                                    op['new_attrs']))
        elif op_type == 'delete_column':
            sql_result.add(self.delete_column(model, op['field']))
        elif op_type == 'change_meta':
            evolve_func = getattr(self, 'change_meta_%s' % op['prop_name'])
            sql_result.add(evolve_func(model, op['old_value'],
                                       op['new_value']))
        elif op_type == 'sql':
            sql_result.add(op['sql'])
        else:
            raise EvolutionNotImplementedError(
                'Unknown mutation operation "%s"' % op_type)

        mutator.finish_op(op)

        return sql_result

    def quote_sql_param(self, param):
        "Add protective quoting around an SQL string parameter"
        if isinstance(param, basestring):
            return u"'%s'" % unicode(param).replace(u"'", ur"\'")
        else:
            return param

    def rename_column(self, model, old_field, new_field):
        """Renames the specified column.

        This must be implemented by subclasses. It must return an SQLResult
        or AlterTableSQLResult representing the SQL needed to rename the
        column.
        """
        raise NotImplementedError

    def get_rename_table_sql(self, model, old_db_tablename, db_tablename):
        qn = self.connection.ops.quote_name

        # We want to define an explicit ALTER TABLE here, instead of setting
        # alter_table in AlterTableSQLResult, so that we can be explicit about
        # the old and new table names.
        return SQLResult(['ALTER TABLE %s RENAME TO %s;'
                          % (qn(old_db_tablename), qn(db_tablename))])

    def rename_table(self, model, old_db_tablename, db_tablename):
        sql_result = SQLResult()

        if old_db_tablename == db_tablename:
            # No Operation
            return sql_result

        style = color.no_style()
        max_name_length = self.connection.ops.max_name_length()
        creation = self.connection.creation

        refs = {}
        models = []

        for field in model._meta.local_many_to_many:
            if (field.rel and
                field.rel.through and
                field.rel.through._meta.db_table == old_db_tablename):

                through = field.rel.through

                for m2m_field in through._meta.local_fields:
                    if m2m_field.rel and m2m_field.rel.to == model:
                        models.append(m2m_field.rel.to)
                        refs.setdefault(m2m_field.rel.to, []).append(
                            (through, m2m_field))

        remove_refs = refs.copy()

        for relto in models:
            sql_result.add_pre_sql(creation.sql_remove_table_constraints(
                relto, remove_refs, style))

        sql_result.add(self.get_rename_table_sql(
            model, old_db_tablename, db_tablename))

        for relto in models:
            for rel_class, f in refs[relto]:
                if rel_class._meta.db_table == old_db_tablename:
                    rel_class._meta.db_table = db_tablename

                rel_class._meta.db_table = \
                    truncate_name(rel_class._meta.db_table, max_name_length)

            sql_result.add_post_sql(
                creation.sql_for_pending_references(relto, style, refs))

        return sql_result

    def delete_column(self, model, f):
        return AlterTableSQLResult(
            self,
            model,
            [
                {
                    'op': 'DROP COLUMN',
                    'column': f.column,
                    'params': ['CASCADE']
                },
            ],
        )

    def delete_table(self, table_name):
        qn = self.connection.ops.quote_name
        return SQLResult(['DROP TABLE %s;' % qn(table_name)])

    def add_m2m_table(self, model, f):
        style = color.no_style()
        creation = self.connection.creation

        if f.rel.through:
            references = {}
            pending_references = {}

            sql, references = creation.sql_create_model(f.rel.through, style)

            # Sort the list, in order to create consistency in the order of
            # ALTER TABLEs. This is primarily needed for unit tests.
            for refto, refs in sorted(references.iteritems(),
                                      key=lambda i: repr(i)):
                pending_references.setdefault(refto, []).extend(refs)
                sql.extend(creation.sql_for_pending_references(
                    refto, style, pending_references))

            sql.extend(creation.sql_for_pending_references(
                f.rel.through, style, pending_references))
        else:
            sql = creation.sql_for_many_to_many_field(model, f, style)

        return sql

    def add_column(self, model, f, initial):
        qn = self.connection.ops.quote_name
        sql_result = AlterTableSQLResult(self, model)

        if f.rel:
            # it is a foreign key field
            # NOT NULL REFERENCES "django_evolution_addbasemodel"
            # ("id") DEFERRABLE INITIALLY DEFERRED

            # ALTER TABLE <tablename> ADD COLUMN <column name> NULL
            # REFERENCES <tablename1> ("<colname>") DEFERRABLE INITIALLY
            # DEFERRED
            related_model = f.rel.to
            related_table = related_model._meta.db_table
            related_pk_col = related_model._meta.pk.name
            constraints = ['%sNULL' % (not f.null and 'NOT ' or '')]

            if f.unique or f.primary_key:
                constraints.append('UNIQUE')

            sql_result.add_alter_table([
                {
                    'op': 'ADD COLUMN',
                    'column': f.column,
                    'db_type': f.db_type(connection=self.connection),
                    'params': constraints + [
                        'REFERENCES',
                        qn(related_table),
                        '(%s)' % qn(related_pk_col),
                        self.connection.ops.deferrable_sql(),
                    ]
                }
            ])
        else:
            null_constraints = '%sNULL' % (not f.null and 'NOT ' or '')

            if f.unique or f.primary_key:
                unique_constraints = 'UNIQUE'
            else:
                unique_constraints = ''

            # At this point, initial can only be None if null=True,
            # otherwise it is a user callable or the default
            # AddFieldInitialCallback which will shortly raise an exception.
            if initial is not None:
                if callable(initial):
                    sql_result.add_alter_table([
                        {
                            'op': 'ADD COLUMN',
                            'column': f.column,
                            'db_type': f.db_type(connection=self.connection),
                            'params': [unique_constraints],
                        }
                    ])

                    sql_result.add_sql([
                        'UPDATE %s SET %s = %s WHERE %s IS NULL;'
                        % (qn(model._meta.db_table), qn(f.column),
                           initial(), qn(f.column))
                    ])

                    if not f.null:
                        # Only put this sql statement if the column cannot
                        # be null.
                        sql_result.add_sql(
                            self.set_field_null(model, f, f.null))
                else:
                    sql_result.add_alter_table([
                        {
                            'op': 'ADD COLUMN',
                            'column': f.column,
                            'db_type': f.db_type(connection=self.connection),
                            'params': [
                                null_constraints,
                                unique_constraints,
                                'DEFAULT',
                                '%s',
                            ],
                            'sql_params': [initial]
                        }
                    ])

                    # Django doesn't generate default columns, so now that
                    # we've added one to get default values for existing
                    # tables, drop that default.
                    sql_result.add_post_sql([
                        'ALTER TABLE %s ALTER COLUMN %s DROP DEFAULT;'
                        % (qn(model._meta.db_table), qn(f.column))
                    ])
            else:
                sql_result.add_alter_table([
                    {
                        'op': 'ADD COLUMN',
                        'column': f.column,
                        'db_type': f.db_type(connection=self.connection),
                        'params': [null_constraints, unique_constraints],
                    }
                ])

        if f.unique or f.primary_key:
            self.record_index(model, [f], use_constraint_name=True,
                              unique=True)

        return sql_result

    def set_field_null(self, model, field, null):
        if null:
            attr = 'DROP NOT NULL'
        else:
            attr = 'SET NOT NULL'

        return AlterTableSQLResult(
            self,
            model,
            [
                {
                    'op': 'ALTER COLUMN',
                    'column': field.column,
                    'params': [attr],
                },
            ]
        )

    def create_index(self, model, f):
        """Returns the SQL for creating an index for a single field.

        The index will be recorded in the database signature for future
        operations within the transaction, and the appropriate SQL for
        creating the index will be returned.

        This is not intended to be overridden.
        """
        index_name = self.find_index_name(model, [f.column])

        if index_name:
            return []

        style = color.no_style()

        self.record_index(model, [f])

        return SQLResult(
            self.connection.creation.sql_indexes_for_field(model, f, style))

    def create_unique_index(self, model, index_name, fields):
        qn = self.connection.ops.quote_name

        self.record_index(model, fields, index_name=index_name, unique=True)

        return SQLResult([
            'CREATE UNIQUE INDEX %s ON %s (%s);'
            % (index_name, model._meta.db_table,
               ', '.join([qn(field.column) for field in fields])),
        ])

    def drop_index(self, model, f):
        """Returns the SQL for dropping an index for a single field.

        The index matching the field's column will be looked up and,
        if found, the SQL for dropping it will be returned.

        If the index was not found on the database or in the database
        signature, this won't return any SQL statements.

        This is not intended to be overridden. Instead, subclasses should
        override `get_drop_index_sql`.
        """
        index_name = self.find_index_name(model, [f.column])

        if index_name:
            return self.drop_index_by_name(model, index_name)
        else:
            return []

    def drop_index_by_name(self, model, index_name):
        """Returns the SQL to drop an index, given an index name.

        The index will be removed fom the database signature, and
        the appropriate SQL for dropping the index will be returned.

        This is not intended to be overridden. Instead, subclasses should
        override `get_drop_index_sql`.
        """
        self.remove_recorded_index(model, index_name)

        return self.get_drop_index_sql(model, index_name)

    def get_drop_index_sql(self, model, index_name):
        """Returns the database-specific SQL to drop an index.

        This can be overridden by subclasses if they use a syntax
        other than "DROP INDEX <name>;"
        """
        qn = self.connection.ops.quote_name

        return SQLResult(['DROP INDEX %s;' % qn(index_name)])

    def get_new_index_name(self, model, fields, unique=False):
        """Returns a newly generated index name.

        This returns a unique index name for any indexes created by
        django-evolution. It does not need to match what Django would
        create by default.

        The default works well in most cases, but can be overridden
        for database backends that require it.
        """
        colname = self.connection.creation._digest(*[f.name for f in fields])

        return truncate_name('%s_%s' % (model._meta.db_table, colname),
                             self.connection.ops.max_name_length())

    def get_default_index_name(self, table_name, field):
        """Returns a default index name for the database.

        This will return an index name for the given field that matches what
        the database or Django database backend would automatically generate
        when marking a field as indexed or unique.

        This can be overridden by subclasses if the database or Django
        database backend provides different values.
        """
        assert field.unique or field.db_index

        if field.unique:
            index_name = field.column
        elif field.db_index:
            # This whole block of logic comes from sql_indexes_for_field
            # in django.db.backends.creation, and is designed to match
            # the logic for the past few versions of Django.
            if supports_index_together:
                # Starting in Django 1.5, the _digest is passed a raw
                # list. While this is probably a bug (digest should
                # expect a string), we still need to retain
                # compatibility. We know this behavior hasn't changed
                # as of Django 1.6.1.
                #
                # It also uses the field name, and not the column name.
                column = [field.name]
            else:
                column = field.column

            column = self.connection.creation._digest(column)
            index_name = '%s_%s' % (table_name, column)

        return truncate_name(index_name, self.connection.ops.max_name_length())

    def get_default_index_together_name(self, table_name, fields):
        """Returns a default index name for an index_together.

        This will return an index name for the given field that matches what
        Django uses for index_together fields.
        """
        index_name = '%s_%s' % (
            table_name,
            self.connection.creation._digest([f.name for f in fields]))

        return truncate_name(index_name, self.connection.ops.max_name_length())

    def change_column_attrs(self, model, mutation, field_name, new_attrs):
        """Returns the SQL for changing one or more column attributes.

        This will generate all the statements needed for changing a set
        of attributes for a column.

        The resulting AlterTableSQLResult contains all the SQL needed
        to apply these attributes.
        """
        field = model._meta.get_field(field_name)
        attrs_sql_result = AlterTableSQLResult(self, model)

        for attr_name, attr_info in new_attrs.iteritems():
            method_name = 'change_column_attr_%s' % attr_name
            evolve_func = getattr(self, method_name)

            try:
                sql_result = evolve_func(model, mutation, field,
                                         attr_info['old_value'],
                                         attr_info['new_value'])
                assert not sql_result or isinstance(sql_result, SQLResult)
            except Exception, e:
                logging.critical(
                    'Error running database evolver function %s: %s',
                    method_name, e,
                    exc_info=1)
                raise

            attrs_sql_result.add(sql_result)

        return attrs_sql_result

    def change_column_attr_null(self, model, mutation, field, old_value,
                                new_value):
        """Returns the SQL for changing a column's NULL/NOT NULL attribute."""
        qn = self.connection.ops.quote_name
        initial = mutation.initial
        opts = model._meta
        pre_sql = []

        if not new_value and initial is not None:
            sql_prefix = (
                'UPDATE %(table_name)s SET %(column_name)s = %%s'
                ' WHERE %(column_name)s IS NULL;'
                % {
                    'table_name': qn(opts.db_table),
                    'column_name': qn(field.column),
                }
            )

            if callable(initial):
                update_sql = sql_prefix % initial()
            else:
                update_sql = (sql_prefix, (initial,))

            pre_sql.append(update_sql)

        sql_result = self.set_field_null(model, field, new_value)
        sql_result.add_pre_sql(pre_sql)

        return sql_result

    def change_column_attr_max_length(self, model, mutation, field, old_value,
                                      new_value):
        """Returns the SQL for changing a column's max length."""
        field.max_length = new_value

        qn = self.connection.ops.quote_name
        column = field.column
        db_type = field.db_type(connection=self.connection)

        return AlterTableSQLResult(
            self,
            model,
            [
                {
                    'op': 'ALTER COLUMN',
                    'column': column,
                    'params': [
                        'TYPE %s USING CAST(%s as %s)'
                        % (db_type, qn(column), db_type),
                    ],
                },
            ]
        )

    def change_column_attr_db_column(self, model, mutation, field, old_value,
                                     new_value):
        """Returns the SQL for changing a column's name."""
        new_field = copy.copy(field)
        new_field.column = new_value

        return self.rename_column(model, field, new_field)

    def change_column_attr_db_table(self, model, mutation, field, old_value,
                                    new_value):
        """Returns the SQL for changing the table for a ManyToManyField."""
        return self.rename_table(model, old_value, new_value)

    def change_column_attr_db_index(self, model, mutation, field, old_value,
                                    new_value):
        """Returns the SQL for creating/dropping indexes for a column."""
        field.db_index = new_value

        if new_value:
            return self.create_index(model, field)
        else:
            return self.drop_index(model, field)

    def change_column_attr_unique(self, model, mutation, field, old_value,
                                  new_value):
        """Returns the SQL to change a field's unique flag.

        Changing the unique flag for a given column will affect indexes.
        If setting unique to True, an index will be created in the
        database signature for future operations within the transaction.
        If False, the index will be dropped from the database signature.

        The SQL needed to change the column will be returned.

        This is not intended to be overridden. Instead, subclasses should
        override `get_change_unique_sql`.
        """
        if new_value:
            constraint_name = self.get_new_index_name(model, [field],
                                                      unique=True)
            self.record_index(model, [field], index_name=constraint_name,
                              unique=True)
        else:
            constraint_name = self.find_index_name(model, [field.column],
                                                   unique=True)
            self.remove_recorded_index(model, constraint_name, unique=True)

        return self.get_change_unique_sql(model, field, new_value,
                                          constraint_name, mutation.initial)

    def get_change_unique_sql(self, model, field, new_unique_value,
                              constraint_name, initial):
        """Returns the database-specific SQL to change a column's unique flag.

        This can be overridden by subclasses if they use a different syntax.
        """
        qn = self.connection.ops.quote_name

        if new_unique_value:
            alter_table_item = {
                'sql': 'ADD CONSTRAINT %s UNIQUE(%s)'
                       % (constraint_name, qn(field.column))
            }
        else:
            alter_table_item = {
                'sql': 'DROP CONSTRAINT %s' % constraint_name
            }

        return AlterTableSQLResult(self, model, [alter_table_item])

    def change_meta_unique_together(self, model, old_unique_together,
                                    new_unique_together):
        """Changes the unique_together constraints of a table."""
        sql_result = SQLResult()

        old_unique_together = set(old_unique_together)
        new_unique_together = set(new_unique_together)

        to_remove = old_unique_together.difference(new_unique_together)

        for field_names in to_remove:
            fields = self.get_fields_for_names(model, field_names)
            columns = self.get_column_names_for_fields(fields)
            index_name = self.find_index_name(model, columns, unique=True)

            if index_name:
                self.remove_recorded_index(model, index_name, unique=True)
                sql_result.add_sql(
                    self.get_drop_unique_constraint_sql(model, index_name))

        for field_names in new_unique_together:
            fields = self.get_fields_for_names(model, field_names)
            columns = self.get_column_names_for_fields(fields)
            index_name = self.find_index_name(model, columns, unique=True)

            if not index_name:
                # This doesn't exist in the database, so we want to add it.
                index_name = self.get_new_index_name(model, fields,
                                                     unique=True)
                sql_result.add_sql(
                    self.create_unique_index(model, index_name, fields))

        return sql_result

    def get_drop_unique_constraint_sql(self, model, index_name):
        return self.get_drop_index_sql(model, index_name)

    def change_meta_index_together(self, model, old_index_together,
                                   new_index_together):
        """Changes the index_together indexes of a table."""
        sql = []
        style = color.no_style()

        old_index_together = set(old_index_together)
        new_index_together = set(new_index_together)

        to_remove = old_index_together.difference(new_index_together)

        for field_names in to_remove:
            fields = self.get_fields_for_names(model, field_names)
            columns = self.get_column_names_for_fields(fields)
            index_name = self.find_index_name(model, columns)

            if index_name:
                sql.extend(self.drop_index_by_name(model, index_name).to_sql())

        for field_names in new_index_together:
            fields = self.get_fields_for_names(model, field_names)
            columns = self.get_column_names_for_fields(fields)
            index_name = self.find_index_name(model, columns)

            if not index_name:
                # This doesn't exist in the database, so we want to add it.
                self.record_index(model, fields)
                sql.extend(self.connection.creation.sql_indexes_for_fields(
                    model, fields, style))

        return sql

    def find_index_name(self, model, column_names, unique=False):
        """Finds an index in the database matching the given criteria.

        This will look in the database signature, attempting to find the
        name of an index that matches the list of columns and the
        uniqueness flag. If one is found, it will be returned. Otherwise,
        None is returned.

        This takes into account all indexes found when first beginning
        then evolution process, and those added during the evolution
        process.
        """
        if not isinstance(column_names, (list, tuple)):
            column_names = (column_names,)

        opts = model._meta
        table_name = opts.db_table

        if table_name in self.database_sig:
            indexes = self.database_sig[table_name]['indexes']

            for index_name, index_info in indexes.iteritems():
                if (index_info['columns'] == column_names and
                    index_info['unique'] == unique):
                    return index_name

        return None

    def get_fields_for_names(self, model, field_names):
        """Returns a list of fields for the given field names."""
        return [
            model._meta.get_field(field_name)
            for field_name in field_names
        ]

    def get_column_names_for_fields(self, fields):
        return [field.column for field in fields]

    def get_indexes_for_table(self, table_name):
        """Returns a dictionary of indexes from the database.

        This introspects the database to return a mapping of index names
        to index information, with the following keys:

            * columns -> list of column names
            * unique -> whether it's a unique index

        This function must be implemented by subclasses.
        """
        raise NotImplementedError

    def remove_field_constraints(self, field, opts, models, refs):
        sql = []

        if field.primary_key:
            creation = self.connection.creation
            style = color.no_style()

            for f in opts.local_many_to_many:
                if f.rel and f.rel.through:
                    through = f.rel.through

                    for m2m_f in through._meta.local_fields:
                        if (m2m_f.rel and
                            m2m_f.rel.to._meta.db_table == opts.db_table and
                            m2m_f.rel.field_name == field.column):

                            models.append(m2m_f.rel.to)
                            refs.setdefault(m2m_f.rel.to, []).append(
                                (through, m2m_f))

            remove_refs = refs.copy()
            style = color.no_style()

            for relto in models:
                sql.extend(creation.sql_remove_table_constraints(
                    relto, remove_refs, style))

        return sql

    def add_primary_key_field_constraints(self, old_field, new_field, models,
                                          refs):
        sql = []

        if old_field.primary_key:
            creation = self.connection.creation
            style = color.no_style()

            for relto in models:
                for rel_class, f in refs[relto]:
                    f.rel.field_name = new_field.column

                del relto._meta._fields[old_field.name]
                relto._meta._fields[new_field.name] = new_field

                sql.extend(creation.sql_for_pending_references(
                    relto, style, refs))

        return sql

    def record_index(self, model, fields, use_constraint_name=False,
                     index_name=None, unique=False):
        """Records an index in the database signature.

        This is a convenience to record an index in the database signature
        for future lookups. It can take an index name, or it can generate
        a constraint name if that's to be used.
        """
        if not index_name and use_constraint_name:
            index_name = truncate_name(
                '%s_%s_key' % (model._meta.db_table, fields[0].column),
                self.connection.ops.max_name_length())

        assert index_name or not unique

        add_index_to_database_sig(self, self.database_sig, model, fields,
                                  index_name=index_name, unique=unique)

    def remove_recorded_index(self, model, index_name, unique=False):
        """Removes an index from the database signature."""
        remove_index_from_database_sig(self.database_sig, model,
                                       index_name, unique=unique)

    def normalize_value(self, value):
        if isinstance(value, bool):
            return self.normalize_bool(value)

        return value

    def normalize_bool(self, value):
        if value:
            return 1
        else:
            return 0

    def _are_ops_mergeable(self, op1, op2):
        """Returns whether two operations can be merged.

        If two operation types are compatible, their operations can be
        merged together into a single AlterTableSQLResult. This checks
        to see if the operations qualify.
        """
        return (op1['type'] in self.mergeable_ops and
                op2['type'] in self.mergeable_ops)
