import logging
from optparse import make_option
try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.models import get_apps, get_app
from django.db.utils import DEFAULT_DB_ALIAS

from django_evolution.diff import Diff
from django_evolution.errors import EvolutionException
from django_evolution.evolve import get_unapplied_evolutions, get_mutations
from django_evolution.models import Version, Evolution
from django_evolution.mutations import AddField, DeleteApplication
from django_evolution.mutators import AppMutator
from django_evolution.signature import create_database_sig, create_project_sig
from django_evolution.utils import write_sql, execute_sql


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--noinput', action='store_false', dest='interactive',
            default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option(
            '--hint', action='store_true', dest='hint', default=False,
            help='Generate an evolution script that would update the app.'),
        make_option(
            '--purge', action='store_true', dest='purge', default=False,
            help='Generate evolutions to delete stale applications.'),
        make_option(
            '--sql', action='store_true', dest='compile_sql',
            default=False,
            help='Compile a Django evolution script into SQL.'),
        make_option(
            '-x', '--execute', action='store_true', dest='execute',
            default=False,
            help='Apply the evolution to the database.'),
        make_option(
            '--database', action='store', dest='database',
            help='Nominates a database to synchronize.'),
    )

    if '--verbosity' not in [opt.get_opt_string()
                             for opt in BaseCommand.option_list]:
        option_list += make_option(
            '-v', '--verbosity', action='store',
            dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, '
                 '2=all output'),

    help = 'Evolve the models in a Django project.'
    args = '<appname appname ...>'

    requires_model_validation = False

    def handle(self, *app_labels, **options):
        try:
            self.evolve(*app_labels, **options)
        except CommandError:
            raise
        except Exception, e:
            logging.error('Unexpected error: %s' % e, exc_info=1)
            raise

    def evolve(self, *app_labels, **options):
        self.hint = options['hint']

        self.verbosity = int(options['verbosity'])
        self.interactive = options['interactive']
        self.execute = options['execute']
        self.compile_sql = options['compile_sql']
        self.purge = options['purge']
        self.database = options['database']

        if not self.database:
            self.database = DEFAULT_DB_ALIAS

        self.using_args = {
            'using': self.database
        }

        # Use the list of all apps, unless app labels are specified.
        if app_labels:
            if self.execute:
                raise CommandError('Cannot specify an application name when '
                                   'executing evolutions.')
            try:
                app_list = [get_app(app_label) for app_label in app_labels]
            except (ImproperlyConfigured, ImportError), e:
                raise CommandError("%s. Are you sure your INSTALLED_APPS "
                                   "setting is correct?" % e)
        else:
            app_list = get_apps()

        # Iterate over all applications running the mutations
        self.evolution_required = False
        self.simulated = True
        self.new_evolutions = []

        self.database_sig = create_database_sig(self.database)
        self.current_proj_sig = create_project_sig(self.database)
        self.current_signature = pickle.dumps(self.current_proj_sig)

        sql = []

        try:
            latest_version = \
                Version.objects.using(self.database).latest('when')

            self.old_proj_sig = pickle.loads(str(latest_version.signature))
            self.diff = Diff(self.old_proj_sig, self.current_proj_sig)
        except Evolution.DoesNotExist:
            raise CommandError("Can't evolve yet. Need to set an "
                               "evolution baseline.")

        try:
            for app in app_list:
                sql.extend(self.evolve_app(app))

            # Process the purged applications if requested to do so.
            if self.purge:
                sql.extend(self.purge_apps())
        except EvolutionException, e:
            raise CommandError(str(e))

        self.check_simulation()

        if self.evolution_required:
            self.perform_evolution(sql)
        elif self.verbosity > 0:
            self.stdout.write('No evolution required.\n')

    def evolve_app(self, app):
        app_label = app.__name__.split('.')[-2]
        sql = []

        if self.hint:
            evolutions = []
            hinted_evolution = self.diff.evolution()
            temp_mutations = hinted_evolution.get(app_label, [])
        else:
            evolutions = get_unapplied_evolutions(app, self.database)
            temp_mutations = get_mutations(app, evolutions, self.database)

        mutations = [
            mutation for mutation in temp_mutations
            if mutation.is_mutable(app_label, self.old_proj_sig,
                                   self.database_sig, self.database)
        ]

        if mutations:
            app_sql = ['', '-- Evolve application %s' % app_label]
            self.evolution_required = True

            app_mutator = AppMutator(app_label, self.old_proj_sig,
                                     self.database_sig, self.database)
            app_mutator.run_mutations(mutations)
            app_mutator_sql = app_mutator.to_sql()

            if self.compile_sql or self.execute:
                app_sql.extend(app_mutator_sql)

            if not app_mutator.can_simulate:
                self.simulated = False

            self.new_evolutions.extend(
                Evolution(app_label=app_label, label=label)
                for label in evolutions)

            if not self.execute:
                if self.compile_sql:
                    write_sql(app_sql, self.database)
                else:
                    self.stdout.write(
                        '%s\n' % self.generate_hint(app, app_label, mutations))

            sql.extend(app_sql)
        else:
            if self.verbosity > 1:
                self.stdout.write('Application %s is up to date\n' % app_label)

        return sql

    def purge_apps(self):
        sql = []

        if self.diff.deleted:
            self.evolution_required = True
            delete_app = DeleteApplication()
            purge_sql = []

            for app_label in self.diff.deleted:
                if delete_app.is_mutable(app_label, self.old_proj_sig,
                                         self.database_sig,
                                         self.database):
                    app_mutator = AppMutator(app_label, self.old_proj_sig,
                                             self.database_sig, self.database)
                    app_mutator.run_mutation(delete_app)
                    app_mutator_sql = app_mutator.to_sql()

                    if self.compile_sql or self.execute:
                        purge_sql.append('-- Purge application %s'
                                         % app_label)
                        purge_sql.extend(app_mutator_sql)

            if not self.execute:
                if self.compile_sql:
                    write_sql(purge_sql, self.database)
                else:
                    self.stdout.write(
                        'The following application(s) can be purged:\n')

                    for app_label in self.diff.deleted:
                        self.stdout.write('    %s\n' % app_label)

                    self.stdout.write('\n')

            sql.extend(purge_sql)
        else:
            if self.verbosity > 1:
                self.stdout.write('No applications need to be purged.\n')

        return sql

    def check_simulation(self):
        if self.simulated:
            diff = Diff(self.old_proj_sig, self.current_proj_sig)

            if not diff.is_empty(not self.purge):
                if self.hint:
                    self.stdout.write(self.style.ERROR(
                        'Your models contain changes that Django Evolution '
                        'cannot resolve automatically.\n'))
                    self.stdout.write(
                        'This is probably due to a currently unimplemented '
                        'mutation type.\n')
                    self.stdout.write(
                        'You will need to manually construct a mutation '
                        'to resolve the remaining changes.\n')
                else:
                    self.stdout.write(self.style.ERROR(
                        'The stored evolutions do not completely resolve '
                        'all model changes.\n'))
                    self.stdout.write(
                        'Run `./manage.py evolve --hint` to see a '
                        'suggestion for the changes required.\n')

                self.stdout.write(
                    '\n'
                    'The following are the changes that could not be '
                    'resolved:\n'
                    '%s\n'
                    % diff)

                raise CommandError('Your models contain changes that Django '
                                   'Evolution cannot resolve automatically.')
        else:
            self.stdout.write(self.style.NOTICE(
                'Evolution could not be simulated, possibly due to raw '
                'SQL mutations\n'))

    def perform_evolution(self, sql):
        if self.execute:
            # Now that we've worked out the mutations required,
            # and we know they simulate OK, run the evolutions
            if self.interactive:
                confirm = raw_input("""
You have requested a database evolution. This will alter tables
and data currently in the %r database, and may result in
IRREVERSABLE DATA LOSS. Evolutions should be *thoroughly* reviewed
prior to execution.

Are you sure you want to execute the evolutions?

Type 'yes' to continue, or 'no' to cancel: """ % self.database)
            else:
                confirm = 'yes'

            if confirm.lower() == 'yes':
                # Begin Transaction
                transaction.enter_transaction_management(**self.using_args)
                transaction.managed(flag=True, **self.using_args)

                cursor = connections[self.database].cursor()

                try:
                    # Perform the SQL
                    execute_sql(cursor, sql, self.database)

                    # Now update the evolution table
                    version = Version(signature=self.current_signature)
                    version.save(**self.using_args)

                    for evolution in self.new_evolutions:
                        evolution.version = version
                        evolution.save(**self.using_args)

                    transaction.commit(**self.using_args)
                except Exception, ex:
                    transaction.rollback(**self.using_args)
                    raise CommandError('Error applying evolution: %s'
                                       % str(ex))

                transaction.leave_transaction_management(**self.using_args)

                if self.verbosity > 0:
                    self.stdout.write('Evolution successful.\n')
            else:
                self.stdout.write(self.style.ERROR('Evolution cancelled.\n'))
        elif not self.compile_sql:
            if self.verbosity > 0:
                if self.simulated:
                    self.stdout.write('Trial evolution successful.\n')

                    if not self.hint:
                        self.stdout.write(
                            "Run './manage.py evolve --execute' to "
                            "apply evolution.\n")

    def generate_hint(self, app, app_label, mutations):
        imports = set()
        project_imports = set()
        mutation_types = set()

        app_prefix = app.__name__.split('.')[0]

        for m in mutations:
            mutation_types.add(m.__class__.__name__)

            if isinstance(m, AddField):
                field_module = m.field_type.__module__

                if field_module.startswith('django.db.models'):
                    imports.add('from django.db import models')
                else:
                    import_str = 'from %s import %s' % \
                                 (field_module, m.field_type.__name__)

                    if field_module.startswith(app_prefix):
                        project_imports.add(import_str)
                    else:
                        imports.add(import_str)

        lines = [
            '#----- Evolution for %s' % app_label,
            'from django_evolution.mutations import %s'
            % ', '.join(sorted(mutation_types)),
        ]

        lines += sorted(imports)

        if project_imports:
            lines += [''] + sorted(project_imports)

        lines += [
            '',
            '',
            'MUTATIONS = [',
            '    ' + ',\n    '.join(unicode(m) for m in mutations),
            ']',
            '#----------------------',
        ]

        return '\n'.join(lines)
