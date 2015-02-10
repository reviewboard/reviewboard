from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileAttachment', 'attachment_revision', models.IntegerField,
             initial=0),
    AddField('FileAttachment', 'attachment_history', models.ForeignKey,
             null=True, related_model='attachments.FileAttachmentHistory'),
]
