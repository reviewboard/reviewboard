from django.core.management import color

from django_evolution.db.common import BaseEvolutionOperations
from django_evolution.db.sql_result import AlterTableSQLResult, SQLResult


class EvolutionOperations(BaseEvolutionOperations):
    def delete_column(self, model, f):
        sql_result = AlterTableSQLResult(self, model)

        if f.rel:
            creation = self.connection.creation
            style = color.no_style()

            sql_result.add(creation.sql_remove_table_constraints(
                f.rel.to,
                {f.rel.to: [(model, f)]},
                style))

        sql_result.add_sql(
            super(EvolutionOperations, self).delete_column(model, f))

        return sql_result

    def rename_column(self, model, old_field, new_field):
        if old_field.column == new_field.column:
            # No Operation
            return []

        col_type = new_field.db_type(connection=self.connection)

        if col_type is None:
            # Skip ManyToManyFields, because they're not represented as
            # database columns in this table.
            return []

        models = []
        refs = {}
        opts = model._meta

        pre_sql = self.remove_field_constraints(old_field, opts, models, refs)
        alter_table_items = self._get_rename_column_sql(opts, old_field,
                                                        new_field)
        post_sql = self.add_primary_key_field_constraints(old_field, new_field,
                                                          models, refs)

        return AlterTableSQLResult(
            self,
            model,
            pre_sql=pre_sql,
            alter_table=alter_table_items,
            post_sql=post_sql
        )

    def _get_rename_column_sql(self, opts, old_field, new_field):
        qn = self.connection.ops.quote_name
        style = color.no_style()
        col_type = new_field.db_type(connection=self.connection)
        tablespace = new_field.db_tablespace or opts.db_tablespace
        alter_table_item = ''

        # Make the definition (e.g. 'foo VARCHAR(30)') for this field.
        field_output = [
            style.SQL_FIELD(qn(new_field.column)),
            style.SQL_COLTYPE(col_type),
            style.SQL_KEYWORD('%sNULL' %
                              (not new_field.null and 'NOT ' or '')),
        ]

        if new_field.primary_key:
            field_output.append(style.SQL_KEYWORD('PRIMARY KEY'))

        if new_field.unique:
            field_output.append(style.SQL_KEYWORD('UNIQUE'))

        if (tablespace and
            self.connection.features.supports_tablespaces and
            self.connection.features.autoindexes_primary_keys and
            (new_field.unique or new_field.primary_key)):
            # We must specify the index tablespace inline, because we
            # won't be generating a CREATE INDEX statement for this field.
            field_output.append(self.connection.ops.tablespace_sql(
                tablespace, inline=True))

        if new_field.rel:
            field_output.append(
                style.SQL_KEYWORD('REFERENCES') + ' ' +
                style.SQL_TABLE(qn(new_field.rel.to._meta.db_table)) + ' (' +
                style.SQL_FIELD(qn(new_field.rel.to._meta.get_field(
                    new_field.rel.field_name).column)) + ')' +
                self.connection.ops.deferrable_sql()
            )

        if old_field.primary_key:
            alter_table_item = 'DROP PRIMARY KEY, '

        alter_table_item += ('CHANGE COLUMN %s %s'
                             % (qn(old_field.column), ' '.join(field_output)))

        return [{'sql': alter_table_item}]

    def set_field_null(self, model, field, null):
        if null:
            null_attr = 'DEFAULT NULL'
        else:
            null_attr = 'NOT NULL'

        return AlterTableSQLResult(
            self,
            model,
            [
                {
                    'op': 'MODIFY COLUMN',
                    'column': field.column,
                    'db_type': field.db_type(connection=self.connection),
                    'params': [null_attr],
                }
            ]
        )

    def change_column_attr_max_length(self, model, mutation, field, old_value,
                                      new_value):
        qn = self.connection.ops.quote_name

        field.max_length = new_value

        db_type = field.db_type(connection=self.connection)
        params = {
            'table': qn(model._meta.db_table),
            'column': qn(field.column),
            'length': field.max_length,
            'type': db_type,
        }

        return AlterTableSQLResult(
            self,
            model,
            pre_sql=[
                'UPDATE %(table)s SET %(column)s=LEFT(%(column)s,%(length)d);'
                % params,
            ],
            alter_table=[
                {
                    'op': 'MODIFY COLUMN',
                    'column': field.column,
                    'db_type': db_type,
                },
            ]
        )

    def get_drop_index_sql(self, model, index_name):
        qn = self.connection.ops.quote_name

        return SQLResult([
            'DROP INDEX %s ON %s;'
            % (qn(index_name), qn(model._meta.db_table))
        ])

    def get_change_unique_sql(self, model, field, new_unique_value,
                              constraint_name, initial):
        qn = self.connection.ops.quote_name
        opts = model._meta
        sql = []

        if new_unique_value:
            sql.append(
                'CREATE UNIQUE INDEX %s ON %s(%s);'
                % (constraint_name, qn(opts.db_table), qn(field.column)))
        else:
            sql.append(
                'DROP INDEX %s ON %s;'
                % (constraint_name, qn(opts.db_table)))

        return SQLResult(sql)

    def get_rename_table_sql(self, model, old_db_tablename, db_tablename):
        qn = self.connection.ops.quote_name

        return SQLResult([
            'RENAME TABLE %s TO %s;'
            % (qn(old_db_tablename), qn(db_tablename))
        ])

    def get_indexes_for_table(self, table_name):
        cursor = self.connection.cursor()
        qn = self.connection.ops.quote_name
        indexes = {}

        try:
            cursor.execute('SHOW INDEX FROM %s;' % qn(table_name))
        except Exception:
            return {}

        for row in cursor.fetchall():
            index_name = row[2]
            col_name = row[4]

            if index_name not in indexes:
                indexes[index_name] = {
                    'unique': not bool(row[1]),
                    'columns': [],
                }

            indexes[index_name]['columns'].append(col_name)

        return indexes
