"""Set null=False for depends_on fields.

This only affects the stored signature, and should not impact the database
schema.

Version Added:
    4.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'depends_on', initial=None, null=False),
    ChangeField('ReviewRequestDraft', 'depends_on', initial=None, null=False),
]
