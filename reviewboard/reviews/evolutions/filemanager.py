from django.db import models

from django_evolution.mutations import AddField

MUTATIONS = [
    AddField('ReviewRequest', 'files', models.ManyToManyField, related_model='filemanager.UploadedFile'),
    AddField('ReviewRequest', 'inactive_files', models.ManyToManyField, related_model='filemanager.UploadedFile'),
    AddField('Review', 'file_comments', models.ManyToManyField, related_model='reviews.UploadedFileComment'),
    AddField('ReviewRequestDraft', 'files', models.ManyToManyField, related_model='filemanager.UploadedFile'),
    AddField('ReviewRequestDraft', 'inactive_files', models.ManyToManyField, related_model='filemanager.UploadedFile')
]

