"""Limit Repository.path, mirror_path, and raw_file_url to 255 chars.

The old max_lengths were 256 characters.

Version Added:
    1.5
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'path', initial=None, max_length=255),
    ChangeField('Repository', 'mirror_path', initial=None, max_length=255),
    ChangeField('Repository', 'raw_file_url', initial=None, max_length=255)
]
