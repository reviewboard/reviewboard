"""Add an index to LocalSite.public.

This aids in generating LocalSite stats on larger installs.

Version Added:
    5.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('LocalSite', 'public', db_index=True, initial=False),
]
