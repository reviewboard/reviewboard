"""Added FileAttachment.attachment_history and attachment_revision.

Version Added:
    2.5
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('FileAttachment', 'attachment_revision', models.IntegerField,
             initial=0),
    AddField('FileAttachment', 'attachment_history', models.ForeignKey,
             null=True, related_model='attachments.FileAttachmentHistory'),
]
