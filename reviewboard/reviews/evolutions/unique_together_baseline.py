"""Add unique_together state for Django Evolution 0.7.

Version Added:
    2.0
"""

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('Group', 'unique_together', (('name', 'local_site'),)),
    ChangeMeta('ReviewRequest', 'unique_together',
               (('commit_id', 'repository'),
                ('changenum', 'repository'),
                ('local_site', 'local_id'))),
]
