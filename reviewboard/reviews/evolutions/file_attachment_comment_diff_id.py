"""Add FileAttachmentComment.diff_against_file_attachment.

Version Added:
    2.0
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileAttachmentComment', 'diff_against_file_attachment',
             models.ForeignKey, null=True,
             related_model='attachments.FileAttachment')
]
