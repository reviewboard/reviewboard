from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'files', models.ManyToManyField, related_model='filemanager.FileAttachment'),
    AddField('ReviewRequest', 'inactive_files', models.ManyToManyField, related_model='filemanager.FileAttachment'),
    AddField('Review', 'file_comments', models.ManyToManyField, related_model='reviews.FileAttachmentComment'),
    AddField('ReviewRequestDraft', 'files', models.ManyToManyField, related_model='filemanager.FileAttachment'),
    AddField('ReviewRequestDraft', 'inactive_files', models.ManyToManyField, related_model='filemanager.FileAttachment')
]

