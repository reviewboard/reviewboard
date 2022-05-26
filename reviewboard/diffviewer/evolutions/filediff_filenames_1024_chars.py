"""Increase max_length of FileDiff.dest_file and source_file to 1024.

This is an increase from 512 characters.

Version Added:
    1.0.2
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileDiff', 'source_file', initial=None, max_length=1024),
    ChangeField('FileDiff', 'dest_file', initial=None, max_length=1024)
]
