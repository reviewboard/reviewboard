"""Set null=False for the WebHookTarget.repositories field.

This only affects the stored signature, and should not impact the database
schema.

Version Added:
    4.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebHookTarget', 'repositories', initial=None, null=False),
]
