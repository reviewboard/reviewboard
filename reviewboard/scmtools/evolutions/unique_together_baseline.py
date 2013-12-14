from __future__ import unicode_literals

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('Repository', 'unique_together',
               (('name', 'local_site'),
                ('path', 'local_site'))),
]
