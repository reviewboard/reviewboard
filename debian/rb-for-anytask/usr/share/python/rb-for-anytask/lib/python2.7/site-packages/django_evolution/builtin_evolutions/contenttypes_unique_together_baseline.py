from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('ContentType', 'unique_together', [('app_label', 'model')]),
]
