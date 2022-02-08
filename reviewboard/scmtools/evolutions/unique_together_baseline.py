from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('Repository', 'unique_together',
               (('name', 'local_site'),
                ('path', 'local_site'))),
]
