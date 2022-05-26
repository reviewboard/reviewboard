"""Increase Repository.name's max length to 255 characters.

The old max length was 64 characters.

Version Added:
    3.0.11
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'name', initial=None, max_length=255),
]
