from django.db.backends.util import truncate_name

from django_evolution.db.common import BaseEvolutionOperations
from django_evolution.db.sql_result import AlterTableSQLResult


class EvolutionOperations(BaseEvolutionOperations):
    def rename_column(self, model, old_field, new_field):
        if old_field.column == new_field.column:
            # No Operation
            return []

        qn = self.connection.ops.quote_name
        max_name_length = self.connection.ops.max_name_length()
        opts = model._meta
        refs = {}
        models = []

        return AlterTableSQLResult(
            self,
            model,
            pre_sql=self.remove_field_constraints(old_field, opts, models,
                                                  refs),
            alter_table=[
                {
                    'independent': True,
                    'sql': 'RENAME COLUMN %s TO %s'
                           % (truncate_name(qn(old_field.column),
                                            max_name_length),
                              truncate_name(qn(new_field.column),
                                            max_name_length)),
                },
            ],
            post_sql=self.add_primary_key_field_constraints(
                old_field, new_field, models, refs)
        )

    def get_drop_unique_constraint_sql(self, model, index_name):
        return AlterTableSQLResult(
            self,
            model,
            [{'sql': 'DROP CONSTRAINT %s' % index_name}]
        )

    def get_default_index_name(self, table_name, field):
        assert field.unique or field.db_index

        if field.unique:
            index_name = '%s_%s_key' % (table_name, field.column)
        elif field.db_index:
            index_name = '%s_%s' % (table_name, field.column)

        return truncate_name(index_name, self.connection.ops.max_name_length())

    def get_indexes_for_table(self, table_name):
        cursor = self.connection.cursor()
        indexes = {}

        cursor.execute(
            "SELECT i.relname as index_name, a.attname as column_name,"
            "       ix.indisunique"
            "  FROM pg_catalog.pg_class t, pg_catalog.pg_class i,"
            "       pg_catalog.pg_index ix, pg_catalog.pg_attribute a"
            " WHERE t.oid = ix.indrelid AND"
            "       i.oid = ix.indexrelid AND"
            "       a.attrelid = t.oid AND"
            "       a.attnum = ANY(ix.indkey) AND"
            "       t.relkind = 'r' AND"
            "       t.relname = %s"
            " ORDER BY i.relname, a.attnum;",
            [table_name])

        for row in cursor.fetchall():
            index_name = row[0]
            col_name = row[1]

            if index_name not in indexes:
                indexes[index_name] = {
                    'unique': row[2],
                    'columns': []
                }

            indexes[index_name]['columns'].append(col_name)

        return indexes

    def normalize_bool(self, value):
        if value:
            return True
        else:
            return False
