"""Evolution to move away from MultiSelectField.

Version Added:
    7.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebHookTarget', 'events', initial=None, max_length=512),
]
