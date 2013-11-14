from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'file_attachments', models.ManyToManyField,
             related_model='attachments.FileAttachment'),
    AddField('ReviewRequest', 'inactive_file_attachments',
             models.ManyToManyField,
             related_model='attachments.FileAttachment'),
    AddField('Review', 'file_attachment_comments', models.ManyToManyField,
             related_model='reviews.FileAttachmentComment'),
    AddField('ReviewRequestDraft', 'file_attachments', models.ManyToManyField,
             related_model='attachments.FileAttachment'),
    AddField('ReviewRequestDraft', 'inactive_file_attachments',
             models.ManyToManyField,
             related_model='attachments.FileAttachment')
]
