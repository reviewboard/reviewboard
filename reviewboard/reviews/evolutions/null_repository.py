"""Change ReviewRequest.repository to allow NULL.

Version Added:
    1.5
"""

from __future__ import annotations

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'repository', initial=None, null=True)
]
