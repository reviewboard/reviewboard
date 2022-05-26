"""Add an index for ReviewRequest.summary.

Version Added:
    2.0.9
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'summary', initial=None, db_index=True),
]
