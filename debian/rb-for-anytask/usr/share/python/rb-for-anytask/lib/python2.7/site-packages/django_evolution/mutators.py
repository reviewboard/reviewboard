import copy
import logging

from django_evolution.db import EvolutionOperationsMulti
from django_evolution.errors import CannotSimulate
from django_evolution.mutations import (AddField, ChangeField, ChangeMeta,
                                        DeleteField, MockModel,
                                        MonoBaseMutation, MutateModelField,
                                        RenameField)
from django_evolution.utils import get_database_for_model_name


class ModelMutator(object):
    """Tracks and runs mutations for a model.

    A ModelMutator is bound to a particular model (by type, not instance) and
    handles operations that apply to that model.

    Operations are first registered by mutations, and then later provided to
    the database's operations backend, where they will be applied to the
    database.

    After all operations are added, the caller is expected to call to_sql()
    to get the SQL statements needed to apply those operations. Once called,
    the mutator is finalized, and new operations cannot be added.

    ModelMutator only works with mutations that are instances of
    MutateModelField. It is also intended for internal use by AppMutator.
    """
    def __init__(self, app_mutator, model_name, app_label, proj_sig,
                 database_sig, database):
        self.app_mutator = app_mutator
        self.model_name = model_name
        self.app_label = app_label
        self.database = (database or
                         get_database_for_model_name(app_label, model_name))
        self.can_simulate = True
        self._ops = []
        self._finalized = False

        assert self.database
        evolution_ops = EvolutionOperationsMulti(self.database,
                                                 self.database_sig)
        self.evolver = evolution_ops.get_evolver()

    @property
    def proj_sig(self):
        return self.app_mutator.proj_sig

    @property
    def database_sig(self):
        return self.app_mutator.database_sig

    @property
    def model_sig(self):
        return self.proj_sig[self.app_label][self.model_name]

    def create_model(self):
        """Creates a mock model instance with the stored information.

        This is typically used when calling a mutation's mutate() function
        and passing a model instance, but can also be called whenever
        a new instance of the model is needed for any lookups.
        """
        return MockModel(self.proj_sig, self.app_label, self.model_name,
                         self.model_sig, db_name=self.database)

    def add_column(self, mutation, field, initial):
        """Adds a pending Add Column operation.

        This will cause to_sql() to include SQL for adding the column
        with the given information to the model.
        """
        assert not self._finalized

        self._ops.append({
            'type': 'add_column',
            'mutation': mutation,
            'field': field,
            'initial': initial,
        })

    def change_column(self, mutation, field, new_attrs):
        """Adds a pending Change Column operation.

        This will cause to_sql() to include SQL for changing one or more
        attributes for the given column.
        """
        assert not self._finalized

        self._ops.append({
            'type': 'change_column',
            'mutation': mutation,
            'field': field,
            'new_attrs': new_attrs,
        })

    def delete_column(self, mutation, field):
        """Adds a pending Delete Column operation.

        This will cause to_sql() to include SQL for deleting the given
        column.
        """
        assert not self._finalized

        self._ops.append({
            'type': 'delete_column',
            'mutation': mutation,
            'field': field,
        })

    def delete_model(self, mutation):
        """Adds a pending Delete Model operation.

        This will cause to_sql() to include SQL for deleting the model.
        """
        assert not self._finalized

        self._ops.append({
            'type': 'delete_model',
            'mutation': mutation,
        })

    def change_meta(self, mutation, prop_name, new_value):
        """Adds a pending Change Meta operation.

        This will cause to_sql() to include SQL for changing a supported
        attribute in the model's Meta class.
        """
        assert not self._finalized

        self._ops.append({
            'type': 'change_meta',
            'mutation': mutation,
            'prop_name': prop_name,
            'old_value': self.model_sig['meta'][prop_name],
            'new_value': new_value,
        })

    def add_sql(self, mutation, sql):
        """Adds an operation for executing custom SQL.

        This will cause to_sql() to include the provided SQL statements.
        The SQL should be a list of a statements.
        """
        assert not self._finalized

        self._ops.append({
            'type': 'sql',
            'mutation': mutation,
            'sql': sql,
        })

    def run_mutation(self, mutation):
        """Runs the specified mutation.

        The mutation will be provided with a temporary mock instance of a
        model that can be used for field or meta lookups.

        The mutation must be an instance of MutateModelField.
        """
        assert isinstance(mutation, MutateModelField)
        assert not self._finalized

        mutation.mutate(self, self.create_model())
        self.run_simulation(mutation)

    def run_simulation(self, mutation):
        try:
            mutation.simulate(self.app_label, self.proj_sig,
                              self.database_sig, self.database)
        except CannotSimulate:
            self.can_simulate = False

    def to_sql(self):
        """Returns SQL for the operations added to this mutator.

        The SQL will represent all the operations made by the mutator,
        as determined by the database operations backend.

        Once called, no new operations can be added to the mutator.
        """
        assert not self._finalized

        self._finalized = True

        return self.evolver.generate_table_ops_sql(self, self._ops)

    def finish_op(self, op):
        """Finishes handling an operation.

        This is called by the evolution operations backend when it is done
        with an operation.

        Simulations for the operation's associated mutation will be applied,
        in order to update the signatures for the changes made by the
        mutation.
        """
        mutation = op['mutation']

        try:
            mutation.simulate(self.app_label, self.proj_sig,
                              self.database_sig, self.database)
        except CannotSimulate:
            self.can_simulate = False


class SQLMutator(object):
    def __init__(self, mutation, sql):
        self.mutation = mutation
        self.sql = sql

    def to_sql(self):
        return self.sql


class AppMutator(object):
    """Tracks and runs mutations for an app.

    An AppMutator is bound to a particular app name, and handles operations
    that apply to anything on that app.

    This will create a ModelMutator internally for each set of adjacent
    operations that apply to the same model, allowing the database operations
    backend to optimize those operations. This means that it's in the best
    interest of a developer to keep related mutations batched together as much
    as possible.

    After all operations are added, the caller is expected to call to_sql()
    to get the SQL statements needed to apply those operations. Once called,
    the mutator is finalized, and new operations cannot be added.
    """
    def __init__(self, app_label, proj_sig, database_sig, database=None):
        self.app_label = app_label
        self.proj_sig = proj_sig
        self.database_sig = database_sig
        self.database = database
        self.can_simulate = True
        self._last_model_mutator = None
        self._mutators = []
        self._finalized = False
        self._orig_proj_sig = copy.deepcopy(self.proj_sig)
        self._orig_database_sig = copy.deepcopy(self.database_sig)

    def run_mutation(self, mutation):
        """Runs a mutation that applies to this app.

        If the mutation applies to a model, a ModelMutator for that model
        will be given the job of running this mutation. If the prior operation
        operated on the same model, then the previously created ModelMutator
        will be used. Otherwise, a new one will be created.
        """
        if isinstance(mutation, MutateModelField):
            if (self._last_model_mutator and
                mutation.model_name == self._last_model_mutator.model_name):
                # We can continue to apply operations to the previous
                # ModelMutator.
                model_mutator = self._last_model_mutator
            else:
                # This is a new model. Begin a new ModelMutator for it.
                self._finalize_model_mutator()

                model_mutator = ModelMutator(
                    self, mutation.model_name, self.app_label, self.proj_sig,
                    self.database_sig, self.database)
                self._last_model_mutator = model_mutator

            model_mutator.run_mutation(mutation)
        else:
            self._finalize_model_mutator()

            mutation.mutate(self)

    def run_mutations(self, mutations):
        """Runs a list of mutations."""
        mutations = self._preprocess_mutations(mutations)

        for mutation in mutations:
            self.run_mutation(mutation)

    def add_sql(self, mutation, sql):
        """Adds SQL that applies to the application."""
        assert not self._last_model_mutator

        self._mutators.append(SQLMutator(mutation, sql))

    def to_sql(self):
        """Returns SQL for the operations added to this mutator.

        The SQL will represent all the operations made by the mutator.
        Once called, no new operations can be added.
        """
        assert not self._finalized

        # Finalize one last time.
        self._finalize_model_mutator()

        self.proj_sig = self._orig_proj_sig
        self.database_sig = self._orig_database_sig

        sql = []

        for mutator in self._mutators:
            sql.extend(mutator.to_sql())

        self._finalized = True

        return sql

    def _finalize_model_mutator(self):
        """Finalizes the current ModelMutator, if one exists.

        The ModelMutator's SQL will be generated and added to the resulting
        SQL for this AppMutator.
        """
        if self._last_model_mutator:
            if not self._last_model_mutator.can_simulate:
                self.can_simulate = False

            self._mutators.append(self._last_model_mutator)
            self._last_model_mutator = None

    def _preprocess_mutations(self, mutations):
        """Pre-processes a list of mutations to filter out unnecessary changes.

        This attempts to take a set of mutations and figure out which ones
        are actually necessary to create the resulting signature.

        It does this by figuring out batches of mutations it can process in
        one go (basically, adjacent AddFields, DeleteFields, RenameFields, and
        ChangeFields), and then looks in each batch for any changes to fields
        that become unnecessary (due to field deletion).
        """
        mutation_batches = self._create_mutation_batches(mutations)

        # Go through all the mutation batches and get our resulting set of
        # mutations to apply to the database.
        result_mutations = []

        try:
            for mutation_batch in mutation_batches:
                result_mutations.extend(
                    self._process_mutation_batch(mutation_batch))
        except CannotSimulate:
            logging.warning(
                'Unable to pre-process mutations for optimization. '
                '%s contains a mutation that cannot be smimulated.',
                self.app_label)
            result_mutations = mutations

        return result_mutations

    def _create_mutation_batches(self, mutations):
        """Creates batches of mutations that can be pre-processed together.

        Figure out batches of mutations that are pre-processable, and group
        them together. Each batch will be considered as a whole when attempting
        to figure out which mutations to include or to filter out.

        Mutations that are not pre-processable will be left in their own
        non-pre-processable batches.
        """
        cur_mutation_batch = (True, [])
        mutation_batches = [cur_mutation_batch]

        for mutation in mutations:
            can_process = isinstance(mutation, MonoBaseMutation)

            if can_process != cur_mutation_batch[0]:
                cur_mutation_batch = (can_process, [])
                mutation_batches.append(cur_mutation_batch)

            cur_mutation_batch[1].append(mutation)

        return mutation_batches

    def _process_mutation_batch(self, mutation_batch):
        """Processes and optimizes a batch of mutations.

        This will look for any changes to fields that are unnecessary. It
        looks for any field that's deleted in this batch, and gets rid of any
        modifications made to that field, including the addition of the field.

        If the field is both added and deleted in this batch, all mutations
        concerning that field are filtered out.
        """
        can_process, mutations = mutation_batch

        if can_process:
            removed_mutations = set()
            deleted_fields = set()
            noop_fields = set()
            model_names = set()
            unique_together = {}
            last_change_mutations = {}
            renames = {}

            # On our first pass, we loop from last to first mutation and
            # attempt the following things:
            #
            # 1) Filter out all mutations to fields that are later deleted.
            #    We locate DeleteFields and then the mutations that previously
            #    try to operate on those deleted fields (which are pointless
            #    to execute).
            #
            # 2) We also look to see if there are any AddFields in this batch
            #    that later have a corresponding DeleteField. We consider
            #    these mutations, and any others dealing with these fields,
            #    to be no-ops, which will be filtered out.
            #
            # 3) We collapse down multiple ChangeFields into the first
            #    listed ChangeField or AddField. If a batch contains an
            #    AddField and then one or more ChangeFields, it will result
            #    in only a single AddField, with the attributes the field
            #    would otherwise have after executing all ChangeFields.
            #
            # 4) All renames are tracked. If the rename is for a field
            #    that's being deleted, it will be removed. Otherwise, the
            #    history of rename mutations are stored along with the field,
            #    in order from last to first, keyed off from the earliest
            #    field name.
            for mutation in reversed(mutations):
                remove_mutation = False

                model_names.add(mutation.model_name)

                if isinstance(mutation, AddField):
                    mutation_id = self._get_mutation_id(mutation)

                    if mutation_id in deleted_fields:
                        # This field is both added and deleted in this
                        # batch, resulting in a no-op. Track it for later
                        # so we can filter out the DeleteField.
                        noop_fields.add(mutation_id)
                        deleted_fields.remove(mutation_id)
                        remove_mutation = True
                    elif mutation_id in last_change_mutations:
                        # There's a ChangeField later in this batch that
                        # modifies this field. Roll those changes up into
                        # the initial AddField.
                        last_change_mutation = \
                            last_change_mutations[mutation_id]
                        self._copy_change_attrs(last_change_mutation,
                                                mutation)

                        # Remove that ChangeField from the list of mutations.
                        removed_mutations.add(last_change_mutation)
                        del last_change_mutations[mutation_id]
                elif isinstance(mutation, ChangeField):
                    mutation_id = self._get_mutation_id(mutation)

                    if mutation_id in deleted_fields:
                        # This field is scheduled for deletion in this batch,
                        # so this ChangeField is pointless. Filter it out.
                        remove_mutation = True
                    else:
                        # There's another ChangeField later in this batch that
                        # modifies this field. Roll those changes up into
                        # this ChangeField.
                        #
                        # Eventually, all ChangeFields for a given field
                        # will be rolled up into the first ChangeField.
                        last_change_mutation = \
                            last_change_mutations.get(mutation_id)

                        if last_change_mutation:
                            self._copy_change_attrs(last_change_mutation,
                                                    mutation)

                            # Remove that ChangeField from the list of
                            # mutations.
                            removed_mutations.add(last_change_mutation)

                        last_change_mutations[mutation_id] = mutation
                elif isinstance(mutation, DeleteField):
                    # Keep track of this field. Mutations preceding this
                    # DeleteField that reference this field name will be
                    # filtered out.
                    deleted_fields.add(self._get_mutation_id(mutation))
                elif isinstance(mutation, RenameField):
                    old_mutation_id = self._get_mutation_id(
                        mutation,
                        mutation.old_field_name)
                    new_mutation_id = self._get_mutation_id(
                        mutation,
                        mutation.new_field_name)

                    if new_mutation_id in deleted_fields:
                        # Rename the entry in the list of deleted fields so
                        # that other mutations earlier in the list can
                        # look it up.
                        deleted_fields.remove(new_mutation_id)
                        deleted_fields.add(old_mutation_id)
                        remove_mutation = True

                    # Create or update a record of rename mutations for this
                    # field. We use this to fix up field names on the second
                    # run through and to collapse RenameFields either into
                    # the first AddField or the first RenameField.
                    if new_mutation_id in renames:
                        self._rename_dict_key(renames,
                                              new_mutation_id,
                                              old_mutation_id)
                    else:
                        renames[old_mutation_id] = {
                            'can_process': False,
                            'mutations': [],
                        }

                    # Add the mutation to the list of renames for the field.
                    # This results in a chain from last RenameField to first.
                    renames[old_mutation_id]['mutations'].append(mutation)

                    if new_mutation_id in last_change_mutations:
                        # Rename the entry for the last ChangeField mutation
                        # so that earlier mutations will find the proper
                        # entry.
                        self._rename_dict_key(last_change_mutations,
                                              new_mutation_id,
                                              old_mutation_id)
                elif isinstance(mutation, ChangeMeta):
                    if (mutation.prop_name == 'unique_together' and
                        mutation.model_name not in unique_together):
                        # This is the most recent unique_together change
                        # for this model, which wins, since each ChangeMeta
                        # is expected to contain the full resulting value
                        # of the property.
                        unique_together[mutation.model_name] = \
                            mutation.new_value

                if remove_mutation:
                    removed_mutations.add(mutation)

            # We may now have mutations marked for removal, others marked
            # as no-ops, and have information on renames. Time to finish up
            # the process.
            #
            # We now loop from first to last mutation and do the following:
            #
            # 1) Remove any DeleteFields that are part of a no-op. The
            #    other fields as part of the no-op were already scheduled for
            #    removal in the first loop.
            #
            # 2) Collapse down any RenameFields into the first RenameField or
            #    AddField, and schedule the remaining for removal.
            #
            #    It also sets renames to be processable (so that they will
            #    affect other field names) the first time an AddField or
            #    RenameField is encountered.
            #
            #    Every RenameField that is processed is removed from the
            #    renames mutations list, updating the key, in order to allow
            #    future lookups to find the entry.
            #
            # 3) Change the field name on any fields from processable rename
            #    entries.
            if noop_fields or renames or unique_together:
                for mutation in mutations:
                    remove_mutation = False

                    if isinstance(mutation, AddField):
                        mutation_id = self._get_mutation_id(mutation)

                        if mutation_id in renames:
                            # Update the field name being added to the
                            # final name.
                            rename_info = renames[mutation_id]
                            rename_info['can_process'] = True
                            rename_mutations = rename_info['mutations']
                            mutation.field_name = \
                                rename_mutations[0].new_field_name

                            # Filter out each of the RenameFields.
                            removed_mutations.update(rename_mutations)
                    elif isinstance(mutation, ChangeField):
                        mutation_id = self._get_mutation_id(mutation)

                        if mutation_id in renames:
                            # The field has been renamed, so update the name of
                            # this ChangeField.
                            rename_info = renames[mutation_id]

                            if rename_info['can_process']:
                                rename_mutation = rename_info['mutations'][0]
                                mutation.field_name = \
                                    rename_mutation.new_field_name
                    elif isinstance(mutation, DeleteField):
                        mutation_id = self._get_mutation_id(mutation)

                        if mutation_id in noop_fields:
                            # This DeleteField is pointless, since the
                            # field it's trying to delete was added in this
                            # batch. Just remove it. We'll have removed all
                            # others related to it by now.
                            remove_mutation = True
                        elif mutation_id in renames:
                            # The field has been renamed, so update the name
                            # of this ChangeField.
                            rename_info = renames[mutation_id]

                            if rename_info['can_process']:
                                rename_mutation = rename_info['mutations'][0]
                                mutation.field_name = \
                                    rename_mutation.old_field_name
                    elif isinstance(mutation, RenameField):
                        old_mutation_id = self._get_mutation_id(
                            mutation,
                            mutation.old_field_name)
                        new_mutation_id = self._get_mutation_id(
                            mutation,
                            mutation.new_field_name)

                        if old_mutation_id in noop_fields:
                            # Rename the entry in noop_fields so that we
                            # can properly handle future mutations
                            # referencing that field.
                            noop_fields.remove(old_mutation_id)
                            noop_fields.add(new_mutation_id)
                            remove_mutation = True

                        if old_mutation_id in renames:
                            # Set the renames for this field to be processable.
                            # Then we'll update the mutation list and the
                            # key in order to allow for future lookups.
                            rename_info = renames[old_mutation_id]
                            rename_info['can_process'] = True
                            rename_mutations = rename_info['mutations']

                            self._rename_dict_key(renames,
                                                  old_mutation_id,
                                                  new_mutation_id)

                            # This will become the main RenameField, so we
                            # want it to rename to the final field name.
                            mutation.new_field_name = \
                                rename_mutations[0].new_field_name

                            # Mark everything but the last rename mutation
                            # for removal, and update the list of mutations to
                            # include only this one.
                            removed_mutations.update(rename_mutations[:-1])
                            rename_info['mutations'] = [rename_mutations[-1]]
                    elif isinstance(mutation, ChangeMeta):
                        if (mutation.prop_name == 'unique_together' and
                            mutation.model_name in unique_together):
                            # This was a previously found unique_together.
                            # We'll check if the value matches the winning
                            # value from before. If not, we'll discard this
                            # mutation.
                            value = unique_together[mutation.model_name]

                            if mutation.new_value != value:
                                remove_mutation = True

                    if remove_mutation:
                        removed_mutations.add(mutation)

            # Filter out all mutations we've scheduled for removal.
            mutations = [
                mutation
                for mutation in mutations
                if mutation not in removed_mutations
            ]

            # Try to group all mutations to a table together. This lets the
            # evolver's optimizations to better group together operations.
            mutations_by_model = dict([
                (model_name, [])
                for model_name in model_names
            ])

            for mutation in mutations:
                mutations_by_model[mutation.model_name].append(mutation)

            mutations = [
                mutation
                for model_name in sorted(model_names)
                for mutation in mutations_by_model[model_name]
            ]

        return mutations

    def _copy_change_attrs(self, source_mutation, dest_mutation):
        dest_mutation.field_attrs.update(source_mutation.field_attrs)

        if source_mutation.initial is not None:
            dest_mutation.initial = source_mutation.initial

    def _rename_dict_key(self, d, old_key, new_key):
        d[new_key] = d[old_key]
        del d[old_key]

    def _get_mutation_id(self, mutation, field_name=None):
        assert hasattr(mutation, 'model_name')
        assert field_name or hasattr(mutation, 'field_name')

        return (mutation.model_name, field_name or mutation.field_name)
