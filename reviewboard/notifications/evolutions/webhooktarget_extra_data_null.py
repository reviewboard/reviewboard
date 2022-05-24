"""Update WebHookTarget.extra_data to allow NULL.

Version Added:
    2.5
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebHookTarget', 'extra_data', initial=None, null=True)
]
