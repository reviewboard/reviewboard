from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'file_attachment_histories',
             models.ManyToManyField,
             related_model='attachments.FileAttachmentHistory')
]
