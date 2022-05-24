"""Reduce max_length of FileAttachment.repo_revision from 512 to 64.

Version Added:
    2.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileAttachment', 'repo_revision', initial=None,
                max_length=64),
]
