from django.db import models

from django_evolution.mutations import AddField

MUTATIONS = [
    AddField('ReviewRequest', 'files', models.ManyToManyField, related_model='filemanager.Filemanager'),
    AddField('ReviewRequest', 'inactive_files', models.ManyToManyField, related_model='filemanager.Filemanager'),
    AddField('Review', 'file_comments', models.ManyToManyField, related_model='filemanager.FilemanagerComment'),
    AddField('ReviewRequestDraft', 'files', models.ManyToManyField, related_model='filemanager.Filemanager'),
    AddField('ReviewRequestDraft', 'inactive_files', models.ManyToManyField, related_model='filemanager.Filemanager')
]

