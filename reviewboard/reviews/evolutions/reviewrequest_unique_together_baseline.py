from __future__ import unicode_literals

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('ReviewRequest', 'unique_together',
               (('commit_id', 'repository'),
                ('changenum', 'repository'),
                ('local_site', 'local_id'))),
]
