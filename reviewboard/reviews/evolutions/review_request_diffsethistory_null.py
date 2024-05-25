"""Evolution to set null=True on a review request's diffset history.

This only affects the stored signature, and should not impact the database
schema.

Version Added:
    7.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'diffset_history', initial=None, null=True),
]
