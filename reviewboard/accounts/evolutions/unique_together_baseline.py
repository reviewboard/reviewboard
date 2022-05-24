"""Add ReviewRequestVisit and LocalSiteProfile.unique_together state.

This is needed for Django Evolution 0.7.

Version Added:
    2.0
"""

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('ReviewRequestVisit', 'unique_together',
               [('user', 'review_request')]),
    ChangeMeta('LocalSiteProfile', 'unique_together',
               [('user', 'local_site'), ('profile', 'local_site')]),
]
