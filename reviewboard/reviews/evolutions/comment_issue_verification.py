"""Add ReviewRequest.issue_verifying_count.

Version Added:
    3.0
"""

from django_evolution.mutations import AddField
from djblets.db.fields import CounterField


MUTATIONS = [
    AddField('ReviewRequest', 'issue_verifying_count', CounterField,
             null=True),
]
