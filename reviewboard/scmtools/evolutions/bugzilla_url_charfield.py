"""Convert Repository.bug_tracker from a URLField to a CharField.

Version Added:
    1.0
"""

from __future__ import annotations

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'bug_tracker', max_length=256),
]
