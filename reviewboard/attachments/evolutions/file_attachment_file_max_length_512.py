"""Increase max_length of FileAttachment.file from 100 to 512.

Version Added:
    1.6.19
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileAttachment', 'file', initial=None, max_length=512)
]
