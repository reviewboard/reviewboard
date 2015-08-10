from django.db import models

from django_evolution.errors import EvolutionException
from django_evolution.mutations import (DeleteField, AddField, DeleteModel,
                                        ChangeField, ChangeMeta)
from django_evolution.signature import (ATTRIBUTE_DEFAULTS,
                                        has_index_together_changed,
                                        has_unique_together_changed)


class NullFieldInitialCallback(object):
    def __init__(self, app, model, field):
        self.app = app
        self.model = model
        self.field = field

    def __repr__(self):
        return '<<USER VALUE REQUIRED>>'

    def __call__(self):
        raise EvolutionException(
            "Cannot use hinted evolution: AddField or ChangeField mutation "
            "for '%s.%s' in '%s' requires user-specified initial value."
            % (self.model, self.field, self.app))


def get_initial_value(app_label, model_name, field_name):
    """Derive an initial value for a field.

    If a default has been provided on the field definition or the field allows
    for an empty string, that value will be used. Otherwise, a placeholder
    callable will be used. This callable cannot actually be used in an
    evolution, but will indicate that user input is required.
    """
    model = models.get_model(app_label, model_name)
    field = model._meta.get_field(field_name)

    if field and (field.has_default() or
                  (field.empty_strings_allowed and field.blank)):
        return field.get_default()

    return NullFieldInitialCallback(app_label, model_name, field_name)


class Diff(object):
    """
    A diff between two model signatures.

    The resulting diff is contained in two attributes:

    self.changed = {
        app_label: {
            'changed': {
                model_name : {
                    'added': [ list of added field names ]
                    'deleted': [ list of deleted field names ]
                    'changed': {
                        field: [ list of modified property names ]
                    },
                    'meta_changed': {
                        'index_together': new value
                        'unique_together': new value
                    }
                }
            'deleted': [ list of deleted model names ]
        }
    }
    self.deleted = {
        app_label: [ list of models in deleted app ]
    }
    """
    def __init__(self, original, current):
        self.original_sig = original
        self.current_sig = current

        self.changed = {}
        self.deleted = {}

        if self.original_sig.get('__version__', 1) != 1:
            raise EvolutionException(
                "Unknown version identifier in original signature: %s",
                self.original_sig['__version__'])

        if self.current_sig.get('__version__', 1) != 1:
            raise EvolutionException(
                "Unknown version identifier in target signature: %s",
                self.current_sig['__version__'])

        for app_name, old_app_sig in original.items():
            if app_name == '__version__':
                # Ignore the __version__ tag
                continue

            new_app_sig = self.current_sig.get(app_name, None)

            if new_app_sig is None:
                # App has been deleted
                self.deleted[app_name] = old_app_sig.keys()
                continue

            for model_name, old_model_sig in old_app_sig.items():
                new_model_sig = new_app_sig.get(model_name, None)

                if new_model_sig is None:
                    # Model has been deleted
                    items = self.chain_set_default(self.changed, app_name,
                                                   'deleted')
                    items.append(model_name)
                    continue

                old_fields = old_model_sig['fields']
                new_fields = new_model_sig['fields']

                # Look for deleted or modified fields
                for field_name, old_field_data in old_fields.items():
                    new_field_data = new_fields.get(field_name, None)

                    if new_field_data is None:
                        # Field has been deleted
                        items = self.chain_set_default(
                            self.changed, app_name, 'changed', model_name,
                            'deleted')
                        items.append(field_name)
                        continue

                    properties = set(old_field_data.keys())
                    properties.update(new_field_data.keys())

                    for prop in properties:
                        old_value = old_field_data.get(
                            prop,
                            ATTRIBUTE_DEFAULTS.get(prop, None))

                        new_value = new_field_data.get(
                            prop,
                            ATTRIBUTE_DEFAULTS.get(prop, None))

                        if old_value != new_value:
                            try:
                                if (prop == 'field_type' and
                                    (old_value().get_internal_type() ==
                                     new_value().get_internal_type())):
                                    continue
                            except TypeError:
                                pass

                            # Field has been changed
                            items = self.chain_set_default(
                                self.changed, app_name, 'changed',
                                model_name, 'changed', field_name)
                            items.append(prop)

                # Look for added fields
                new_fields = new_model_sig['fields']

                for field_name, new_field_data in new_fields.items():
                    old_field_data = old_fields.get(field_name, None)

                    if old_field_data is None:
                        items = self.chain_set_default(
                            self.changed, app_name, 'changed',
                            model_name, 'added')
                        items.append(field_name)

                # Look for changes to unique_together
                if has_unique_together_changed(old_model_sig, new_model_sig):
                    items = self.chain_set_default(
                        self.changed, app_name, 'changed', model_name,
                        'meta_changed')
                    items.append('unique_together')

                # Look for changes to index_together
                if has_index_together_changed(old_model_sig, new_model_sig):
                    items = self.chain_set_default(
                        self.changed, app_name, 'changed', model_name,
                        'meta_changed')
                    items.append('index_together')

    def is_empty(self, ignore_apps=True):
        """Is this an empty diff? i.e., is the source and target the same?

        Set 'ignore_apps=False' if you wish to ignore changes caused by
        deleted applications. This is used when you don't purge deleted
        applications during an evolve.
        """
        if ignore_apps:
            return not self.changed
        else:
            return not self.deleted and not self.changed

    def __str__(self):
        "Output an application signature diff in a human-readable format"
        lines = []

        for app_label in self.deleted:
            lines.append('The application %s has been deleted' % app_label)

        for app_label, app_changes in self.changed.items():
            for model_name in app_changes.get('deleted', {}):
                lines.append('The model %s.%s has been deleted'
                             % (app_label, model_name))

            app_changed = app_changes.get('changed', {})

            for model_name, change in app_changed.iteritems():
                lines.append('In model %s.%s:' % (app_label, model_name))

                for field_name in change.get('added', []):
                    lines.append("    Field '%s' has been added" % field_name)

                for field_name in change.get('deleted', []):
                    lines.append("    Field '%s' has been deleted"
                                 % field_name)

                changed = change.get('changed', {})

                for field_name, field_change in changed.iteritems():
                    lines.append("    In field '%s':" % field_name)

                    for prop in field_change:
                        lines.append("        Property '%s' has changed"
                                     % prop)

                meta_changed = change.get('meta_changed', [])

                for prop_name in meta_changed:
                    lines.append("    Meta property '%s' has changed"
                                 % prop_name)

        return '\n'.join(lines)

    def evolution(self):
        "Generate an evolution that would neutralize the diff"
        mutations = {}

        for app_label, app_changes in self.changed.items():
            for model_name, change in app_changes.get('changed', {}).items():
                model_sig = self.current_sig[app_label][model_name]

                for field_name in change.get('added', {}):
                    field_sig = model_sig['fields'][field_name]
                    field_type = field_sig['field_type']

                    add_params = [
                        (key, field_sig[key])
                        for key in field_sig.keys()
                        if key in ATTRIBUTE_DEFAULTS.keys()
                    ]
                    add_params.append(('field_type', field_type))

                    if (field_type is not models.ManyToManyField and
                        not field_sig.get('null', ATTRIBUTE_DEFAULTS['null'])):
                        add_params.append(
                            ('initial',
                             get_initial_value(app_label, model_name,
                                               field_name)))

                    if 'related_model' in field_sig:
                        add_params.append(('related_model',
                                           '%s' % field_sig['related_model']))

                    mutations.setdefault(app_label, []).append(
                        AddField(model_name, field_name, **dict(add_params)))

                for field_name in change.get('deleted', []):
                    mutations.setdefault(app_label, []).append(
                        DeleteField(model_name, field_name))

                changed = change.get('changed', {})

                for field_name, field_change in changed.iteritems():
                    changed_attrs = {}
                    current_field_sig = model_sig['fields'][field_name]

                    for prop in field_change:
                        if prop == 'related_model':
                            changed_attrs[prop] = current_field_sig[prop]
                        else:
                            changed_attrs[prop] = \
                                current_field_sig.get(prop,
                                                      ATTRIBUTE_DEFAULTS[prop])

                    if ('null' in changed_attrs and
                        current_field_sig['field_type'] !=
                            models.ManyToManyField and
                        not current_field_sig.get('null',
                                                  ATTRIBUTE_DEFAULTS['null'])):
                        changed_attrs['initial'] = \
                            get_initial_value(app_label, model_name,
                                              field_name)

                    mutations.setdefault(app_label, []).append(
                        ChangeField(model_name, field_name, **changed_attrs))

                meta_changed = change.get('meta_changed', [])

                for prop_name in ('unique_together', 'index_together'):
                    if prop_name in meta_changed:
                        mutations.setdefault(app_label, []).append(
                            ChangeMeta(model_name,
                                       prop_name,
                                       model_sig['meta'][prop_name]))

            for model_name in app_changes.get('deleted', {}):
                mutations.setdefault(app_label, []).append(
                    DeleteModel(model_name))

        return mutations

    def chain_set_default(self, d, *keys, **kwargs):
        """Chains several setdefault calls, creating a nested structure.

        This allows for easily chaining a series of setdefault calls for
        dictionaries in order to quickly build a tree and return the last
        entry.
        """
        for key in keys[:-1]:
            d = d.setdefault(key, {})

        return d.setdefault(keys[-1], [])
