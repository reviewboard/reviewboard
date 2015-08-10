from django.core.management import color
from django.db import models

from django_evolution.db.common import BaseEvolutionOperations, SQLResult


TEMP_TABLE_NAME = 'TEMP_TABLE'


class EvolutionOperations(BaseEvolutionOperations):
    def delete_column(self, model, f):
        field_list = [
            field for field in model._meta.local_fields
            # Remove the field to be deleted
            if f.name != field.name
            # and any Generic fields
            and field.db_type(connection=self.connection) is not None
        ]
        table_name = model._meta.db_table

        sql_result = SQLResult()
        sql_result.add(self.create_temp_table(field_list))
        sql_result.add(self.copy_to_temp_table(table_name, field_list))
        sql_result.add(self.delete_table(table_name))
        sql_result.add(self.create_table(table_name, field_list))
        sql_result.add(self.copy_from_temp_table(table_name, field_list))
        sql_result.add(self.delete_table(TEMP_TABLE_NAME))

        return sql_result

    def copy_to_temp_table(self, source_table_name, original_field_list,
                           new_field_list=None):
        qn = self.connection.ops.quote_name

        source_columns = self.column_names(original_field_list)

        if new_field_list:
            temp_columns = self.column_names(new_field_list)
        else:
            temp_columns = source_columns

        return [
            'INSERT INTO %s (%s) SELECT %s FROM %s;' %
            (qn(TEMP_TABLE_NAME), temp_columns, source_columns,
             qn(source_table_name))
        ]

    def copy_from_temp_table(self, dest_table_name, field_list):
        qn = self.connection.ops.quote_name

        return [
            'INSERT INTO %(dest_table_name)s (%(column_names)s)'
            ' SELECT %(column_names)s FROM %(temp_table)s;'
            % {
                'dest_table_name': qn(dest_table_name),
                'temp_table': qn(TEMP_TABLE_NAME),
                'column_names': self.column_names(field_list),
            }
        ]

    def column_names(self, field_list):
        qn = self.connection.ops.quote_name
        columns = []

        for field in field_list:
            if not isinstance(field, models.ManyToManyField):
                columns.append(qn(field.column))

        return ', '.join(columns)

    def insert_to_temp_table(self, field, initial):
        # At this point, initial can only be None if null=True, otherwise it is
        # a user callable or the default AddFieldInitialCallback which will
        # shortly raise an exception.
        if initial is None:
            return []

        qn = self.connection.ops.quote_name

        update_sql = 'UPDATE %(table_name)s SET %(column_name)s = %%s;' % {
            'table_name': qn(TEMP_TABLE_NAME),
            'column_name': qn(field.column),
        }

        if callable(initial):
            sql = update_sql % initial()
        else:
            sql = (update_sql, (initial,))

        return [sql]

    def create_temp_table(self, field_list):
        return self.create_table(TEMP_TABLE_NAME, field_list, True, False)

    def create_indexes_for_table(self, table_name, field_list):
        class FakeMeta(object):
            def __init__(self, table_name, field_list):
                self.db_table = table_name
                self.local_fields = field_list
                self.fields = field_list  # Required for Pre QS-RF support
                self.db_tablespace = None
                self.managed = True
                self.proxy = False
                self.swapped = False
                self.index_together = []

        class FakeModel(object):
            def __init__(self, table_name, field_list):
                self._meta = FakeMeta(table_name, field_list)

        style = color.no_style()

        return self.connection.creation.sql_indexes_for_model(
            FakeModel(table_name, field_list), style)

    def create_table(self, table_name, field_list, temporary=False,
                     create_index=True):
        qn = self.connection.ops.quote_name
        output = []

        create = ['CREATE']
        if temporary:
            create.append('TEMPORARY')
        create.append('TABLE %s' % qn(table_name))
        output = [' '.join(create)]
        output.append('(')
        columns = []
        for field in field_list:
            if not models.ManyToManyField == field.__class__:
                column_name = qn(field.column)
                column_type = field.db_type(connection=self.connection)
                params = [column_name, column_type]

                # Always use null if this is a temporary table. It may be
                # used to create a new field (which will be null while data is
                # copied across from the old table).
                if temporary or field.null:
                    params.append('NULL')
                else:
                    params.append('NOT NULL')

                if field.unique:
                    params.append('UNIQUE')

                if field.primary_key:
                    params.append('PRIMARY KEY')

                columns.append(' '.join(params))

        output.append(', '.join(columns))
        output.append(');')
        output = [''.join(output)]

        if create_index:
            output.extend(
                self.create_indexes_for_table(table_name, field_list))

        return output

    def rename_column(self, model, old_field, new_field):
        sql_result = SQLResult()

        if old_field.column == new_field.column:
            # No Operation
            return sql_result

        opts = model._meta
        original_fields = opts.local_fields
        new_fields = []
        for f in original_fields:
            # Ignore Generic Fields
            if f.db_type(connection=self.connection) is not None:
                if f.name == old_field.name:
                    new_fields.append(new_field)
                else:
                    new_fields.append(f)

        table_name = opts.db_table

        sql_result.add(self.create_temp_table(new_fields))
        sql_result.add(self.copy_to_temp_table(table_name, original_fields,
                                               new_fields))
        sql_result.add(self.delete_table(table_name))
        sql_result.add(self.create_table(table_name, new_fields))
        sql_result.add(self.copy_from_temp_table(table_name, new_fields))
        sql_result.add(self.delete_table(TEMP_TABLE_NAME))

        return sql_result

    def add_column(self, model, f, initial):
        table_name = model._meta.db_table
        original_fields = [
            field
            for field in model._meta.local_fields
            if field.db_type(connection=self.connection) is not None
        ]
        new_fields = list(original_fields)
        new_fields.append(f)

        sql_result = SQLResult()
        sql_result.add(self.create_temp_table(new_fields))
        sql_result.add(self.copy_to_temp_table(table_name, original_fields))
        sql_result.add(self.insert_to_temp_table(f, initial))
        sql_result.add(self.delete_table(table_name))
        sql_result.add(self.create_table(table_name, new_fields,
                                         create_index=False))
        sql_result.add(self.copy_from_temp_table(table_name, new_fields))
        sql_result.add(self.delete_table(TEMP_TABLE_NAME))

        if f.unique or f.primary_key:
            self.record_index(model, [f], use_constraint_name=True,
                              unique=True)

        return sql_result

    def change_column_attr_null(self, model, mutation, field, old_value,
                                new_value):
        return self.change_attribute(model, field, 'null', new_value,
                                     mutation.initial)

    def change_column_attr_max_length(self, model, mutation, field, old_value,
                                      new_value):
        return self.change_attribute(model, field, 'max_length', new_value)

    def get_change_unique_sql(self, model, field, new_unique_value,
                              constraint_name, initial):
        return self.change_attribute(model, field, '_unique', new_unique_value)

    def get_drop_unique_constraint_sql(self, model, index_name):
        opts = model._meta
        table_name = opts.db_table
        fields = [
            f
            for f in opts.local_fields
            if f.db_type(connection=self.connection) is not None
        ]

        sql_result = SQLResult()
        sql_result.add(self.create_temp_table(fields))
        sql_result.add(self.copy_to_temp_table(table_name, fields))
        sql_result.add(self.delete_table(table_name))
        sql_result.add(self.create_table(table_name, fields))
        sql_result.add(self.copy_from_temp_table(table_name, fields))
        sql_result.add(self.delete_table(TEMP_TABLE_NAME))

        return sql_result

    def change_attribute(self, model, field, attr_name, new_attr_value,
                         initial=None):
        opts = model._meta
        table_name = opts.db_table
        setattr(field, attr_name, new_attr_value)
        fields = [
            f
            for f in opts.local_fields
            if f.db_type(connection=self.connection) is not None
        ]

        sql_result = SQLResult()
        sql_result.add(self.create_temp_table(fields))
        sql_result.add(self.copy_to_temp_table(table_name, fields))
        sql_result.add(self.insert_to_temp_table(opts.get_field(field.name),
                                                 initial))
        sql_result.add(self.delete_table(table_name))
        sql_result.add(self.create_table(table_name, fields,
                                         create_index=False))
        sql_result.add(self.copy_from_temp_table(table_name, fields))
        sql_result.add(self.delete_table(TEMP_TABLE_NAME))

        return sql_result

    def get_indexes_for_table(self, table_name):
        cursor = self.connection.cursor()
        qn = self.connection.ops.quote_name
        indexes = {}

        cursor.execute('PRAGMA index_list(%s);' % qn(table_name))

        for row in list(cursor.fetchall()):
            index_name = row[1]
            indexes[index_name] = {
                'unique': row[2],
                'columns': []
            }

            cursor.execute('PRAGMA index_info(%s)' % qn(index_name))

            for index_info in cursor.fetchall():
                # Column name
                indexes[index_name]['columns'].append(index_info[2])

        return indexes
