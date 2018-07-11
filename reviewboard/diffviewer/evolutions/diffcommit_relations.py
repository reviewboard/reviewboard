from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models
from djblets.db.fields import RelationCounterField


MUTATIONS = [
    AddField('DiffSet', 'commit_count', RelationCounterField, null=True),
    AddField('DiffSet', 'file_count', RelationCounterField, null=True),
    AddField('DiffCommit', 'file_count', RelationCounterField, null=True),
    AddField('FileDiff', 'commit', models.ForeignKey, null=True,
             related_model='diffviewer.DiffCommit'),
]
