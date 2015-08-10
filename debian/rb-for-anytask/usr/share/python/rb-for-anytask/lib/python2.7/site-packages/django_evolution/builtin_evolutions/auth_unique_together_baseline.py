from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('Permission', 'unique_together',
               [('content_type', 'codename')]),
]
