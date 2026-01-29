"""Evolution to move away from MultiSelectField.

Version Added:
    7.0
"""

from __future__ import annotations

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebHookTarget', 'events', initial=None, max_length=512),
]
