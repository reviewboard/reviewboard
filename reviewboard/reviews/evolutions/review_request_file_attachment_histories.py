"""Add ReviewRequest.file_attachment_histories.

Version Added:
    2.5
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'file_attachment_histories',
             models.ManyToManyField,
             related_model='attachments.FileAttachmentHistory')
]
