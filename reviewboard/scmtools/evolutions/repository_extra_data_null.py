"""Allow Repository.extra_data to be NULL.

Version Added:
    1.6.7
"""

from __future__ import annotations

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'extra_data', initial=None, null=True),
]
