"""Add FileAttachment.orig_filename.

Version Added:
    1.6.18
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileAttachment', 'orig_filename', models.CharField,
             max_length=256, null=True)
]
