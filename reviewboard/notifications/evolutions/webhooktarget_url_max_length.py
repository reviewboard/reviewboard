"""Evolution to increase the max length of the URL field.

Version Added:
    7.0
"""

from __future__ import annotations

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebHookTarget', 'url', initial=None, max_length=512),
]
