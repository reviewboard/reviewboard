class SQLResult(object):
    """Represents one or more SQL statements.

    This is returned by functions generating SQL statements. It can store
    the main SQL statements to execute, or SQL statements to be executed before
    or after the main statements.

    SQLResults can easily be added together or converted into a flat list of
    SQL statements to execute.
    """
    def __init__(self, sql=None, pre_sql=None, post_sql=None):
        self.sql = sql or []
        self.pre_sql = pre_sql or []
        self.post_sql = post_sql or []

    def add(self, sql_or_result):
        """Adds a list of SQL statements or an SQLResult.

        If an SQLResult is passed, its ``pre_sql``, ``sql``, and ``post_sql``
        lists will be added to this one.

        If a list of SQL statements is passed, it will be added to this
        SQLResult's sql list.
        """
        if isinstance(sql_or_result, SQLResult):
            self.pre_sql += sql_or_result.pre_sql
            self.sql += sql_or_result.sql
            self.post_sql += sql_or_result.post_sql
        else:
            self.sql += sql_or_result

    def add_pre_sql(self, sql_or_result):
        """Adds a list of SQL statements or an SQLResult to ``pre_sql`.

        If an SQLResult is passed, it will be converted into a list of SQL
        statements.
        """
        self.pre_sql += self.normalize_sql(sql_or_result)

    def add_sql(self, sql_or_result):
        """Adds a list of SQL statements or an SQLResult to ``sql``.

        If an SQLResult is passed, it will be converted into a list of SQL
        statements.
        """
        self.sql += self.normalize_sql(sql_or_result)

    def add_post_sql(self, sql_or_result):
        """Adds a list of SQL statements or an SQLResult to ``post_sql``.

        If an SQLResult is passed, it will be converted into a list of SQL
        statements.
        """
        self.post_sql += self.normalize_sql(sql_or_result)

    def normalize_sql(self, sql_or_result):
        """Normalizes a list of SQL statements or an SQLResult into a list.

        If a list of SQL statements is provided, it will be returned. If
        an SQLResult is provided, it will be converted into a list of SQL
        statements and returned.
        """
        if isinstance(sql_or_result, SQLResult):
            return sql_or_result.to_sql()
        else:
            return sql_or_result or []

    def to_sql(self):
        """Flattens the SQLResult into a list of SQL statements."""
        return self.pre_sql + self.sql + self.post_sql

    def __repr__(self):
        return ('<SQLResult: pre_sql=%r, sql=%r, post_sql=%r>'
                % (self.pre_sql, self.sql, self.post_sql))


class AlterTableSQLResult(SQLResult):
    """Represents one or more SQL statements or Alter Table rules.

    This is returned by functions generating SQL statements. It can store
    the main SQL statements to execute, or SQL statements to be executed before
    or after the main statements.

    SQLResults can easily be added together or converted into a flat list of
    SQL statements to execute.
    """
    def __init__(self, evolver, model, alter_table=None, *args, **kwargs):
        super(AlterTableSQLResult, self).__init__(*args, **kwargs)
        self.evolver = evolver
        self.model = model
        self.alter_table = alter_table or []

    def add(self, sql_result):
        """Adds a list of SQL statements or an SQLResult.

        If an SQLResult is passed, its ``pre_sql``, ``sql``, and ``post_sql``
        lists will be added to this one.

        If an AlterTableSQLResult is passed, its ``alter_table`` lists will
        also be added to this one.

        If a list of SQL statements is passed, it will be added to this
        SQLResult's sql list.
        """
        super(AlterTableSQLResult, self).add(sql_result)

        if isinstance(sql_result, AlterTableSQLResult):
            self.alter_table += sql_result.alter_table

    def add_alter_table(self, alter_table):
        """Adds a list of Alter Table rules to ``alter_table``."""
        self.alter_table += alter_table

    def to_sql(self):
        """Flattens the AlterTableSQLResult into a list of SQL statements.

        Any ``alter_table`` entries will be collapsed together into
        ALTER TABLE statements.
        """
        sql = []
        sql += self.pre_sql

        if self.alter_table:
            qn = self.evolver.connection.ops.quote_name
            quoted_table_name = qn(self.model._meta.db_table)
            alter_table_batches = self._preprocess_alter_table_ops()

            for statements, sql_params in alter_table_batches:
                alter_table_sql = (
                    'ALTER TABLE %s %s;'
                    % (quoted_table_name, ', '.join(statements))
                )

                if sql_params:
                    sql.append((alter_table_sql, sql_params))
                else:
                    sql.append(alter_table_sql)

        sql += self.sql
        sql += self.post_sql

        return sql

    def _preprocess_alter_table_ops(self):
        """Pre-processes Alter Table operations.

        This will attempt to merge together adjacent MODIFY COLUMN
        operations on a field to form a single MODIFY COLUMN.

        It will also split the Alter Table operations into batches,
        separated by operations setting independent=True.
        """
        qn = self.evolver.connection.ops.quote_name
        new_alter_table_items = []
        prev_op = None
        prev_item = None

        for item in self.alter_table:
            alter_table_attrs = []
            op = item.get('op', 'sql')

            if op == 'MODIFY COLUMN':
                if (prev_op == op and
                    prev_item['column'] == item['column'] and
                    prev_item['db_type'] == item['db_type']):
                    # We're issuing another MODIFY COLUMN on the same column,
                    # so combine.

                    if 'params' in item:
                        prev_params = prev_item.setdefault('params', [])

                        for param in item['params']:
                            if param and param not in prev_params:
                                prev_params.append(param)

                    if 'sql_params' in item:
                        prev_item.setdefault('sql_params', []).extend(
                            item['sql_params'])

                    # Skip adding this or setting the prev_op/prev_item.
                    continue

            new_alter_table_items.append(item)
            prev_op = op
            prev_item = item

        alter_table_statements = []
        alter_table_sql_params = []
        alter_table_batches = [(alter_table_statements,
                                alter_table_sql_params)]

        for item in new_alter_table_items:
            alter_table_attrs = []
            op = item.get('op', 'sql')
            independent = item.get('independent', False)

            if independent:
                # This particular ALTER TABLE statement needs to stand
                # alone, so break it up into its own batch.
                alter_table_statements = []
                alter_table_sql_params = []
                alter_table_batches.append((alter_table_statements,
                                            alter_table_sql_params))

            if op == 'sql':
                alter_table_attrs.append(item['sql'])
            else:
                alter_table_attrs.append(item['op'])

                if 'column' in item:
                    alter_table_attrs.append(qn(item['column']))

                if op in ('MODIFY COLUMN', 'ADD COLUMN') and 'db_type' in item:
                    alter_table_attrs.append(item['db_type'])

                if 'params' in item:
                    alter_table_attrs.extend([
                        param
                        for param in item['params']
                        if param
                    ])

            alter_table_statements.append(' '.join(alter_table_attrs))

            if 'sql_params' in item:
                alter_table_sql_params.extend(item['sql_params'])

            if independent:
                # Now that we've processed this independent statement,
                # start a new batch for the next.
                alter_table_statements = []
                alter_table_sql_params = []
                alter_table_batches.append((alter_table_statements,
                                            alter_table_sql_params))

        # Filter out any batches that we are empty, and return the result.
        return [
            alter_table_batch
            for alter_table_batch in alter_table_batches
            if alter_table_batch[0]
        ]

    def __repr__(self):
        return ('<AlterTableSQLResult: pre_sql=%r, sql=%r, post_sql=%r,'
                ' alter_table=%r>'
                % (self.pre_sql, self.sql, self.post_sql, self.alter_table))
