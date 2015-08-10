import os
import pickle

from django_evolution.builtin_evolutions import BUILTIN_SEQUENCES
from django_evolution.errors import EvolutionException
from django_evolution.models import Evolution, Version
from django_evolution.mutations import SQLMutation
from django_evolution.signature import (has_unique_together_changed,
                                        create_project_sig)


def get_evolution_sequence(app):
    "Obtain the full evolution sequence for an application"
    app_name = '.'.join(app.__name__.split('.')[:-1])

    if app_name in BUILTIN_SEQUENCES:
        return BUILTIN_SEQUENCES[app_name]

    try:
        evolution_module = __import__(app_name + '.evolutions', {}, {}, [''])
        return evolution_module.SEQUENCE
    except:
        return []


def get_unapplied_evolutions(app, database):
    "Obtain the list of unapplied evolutions for an application"
    sequence = get_evolution_sequence(app)
    app_label = app.__name__.split('.')[-2]

    evolutions = Evolution.objects.filter(app_label=app_label).using(database)
    applied = [evo.label for evo in evolutions]

    return [seq for seq in sequence if seq not in applied]


def get_mutations(app, evolution_labels, database):
    """
    Obtain the list of mutations described by the named evolutions.
    """
    # For each item in the evolution sequence. Check each item to see if it is
    # a python file or an sql file.
    try:
        app_name = '.'.join(app.__name__.split('.')[:-1])

        if app_name in BUILTIN_SEQUENCES:
            module_name = 'django_evolution.builtin_evolutions'
        else:
            module_name = '%s.evolutions' % app_name

        evolution_module = __import__(module_name, {}, {}, [''])
    except ImportError:
        return []

    mutations = []

    for label in evolution_labels:
        directory_name = os.path.dirname(evolution_module.__file__)

        # The first element is used for compatibility purposes.
        filenames = [
            os.path.join(directory_name, label + '.sql'),
            os.path.join(directory_name, "%s_%s.sql" % (database, label)),
        ]

        found = False

        for filename in filenames:
            if os.path.exists(filename):
                sql_file = open(filename, 'r')
                sql = sql_file.readlines()
                sql_file.close()

                mutations.append(SQLMutation(label, sql))

                found = True
                break

        if not found:
            try:
                module_name = [evolution_module.__name__, label]
                module = __import__('.'.join(module_name),
                                    {}, {}, [module_name])
                mutations.extend(module.MUTATIONS)
            except ImportError:
                raise EvolutionException(
                    'Error: Failed to find an SQL or Python evolution named %s'
                    % label)

    latest_version = Version.objects.using(database).latest('when')

    app_label = app.__name__.split('.')[-2]
    old_proj_sig = pickle.loads(str(latest_version.signature))
    proj_sig = create_project_sig(database)

    if app_label in old_proj_sig and app_label in proj_sig:
        # We want to go through now and make sure we're only applying
        # evolutions for models where the signature is different between
        # what's stored and what's current.
        #
        # The reason for this is that we may have just installed a baseline,
        # which would have the up-to-date signature, and we might be trying
        # to apply evolutions on top of that (which would already be applied).
        # These would generate errors. So, try hard to prevent that.
        old_app_sig = old_proj_sig[app_label]
        app_sig = proj_sig[app_label]

        changed_models = set()

        # Find the list of models in the latest signature of this app
        # that aren't in the old signature.
        for model_name, model_sig in app_sig.iteritems():
            if (model_name not in old_app_sig or
                old_app_sig[model_name] != model_sig or
                has_unique_together_changed(old_app_sig[model_name],
                                            model_sig)):
                changed_models.add(model_name)

        # Now do the same for models in the old signature, in case the
        # model has been deleted.
        for model_name, model_sig in old_app_sig.iteritems():
            if model_name not in app_sig:
                changed_models.add(model_name)

        # We should now have a full list of which models changed. Filter
        # the list of mutations appropriately.
        mutations = [
            mutation
            for mutation in mutations
            if (not hasattr(mutation, 'model_name') or
                mutation.model_name in changed_models)
        ]

    return mutations
