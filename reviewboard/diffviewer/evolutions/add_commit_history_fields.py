from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models
from djblets.db.fields import RelationCounterField


MUTATIONS = [
    AddField('FileDiff', 'diff_commit', models.ForeignKey, null=True,
             related_model='diffviewer.DiffCommit'),
    AddField('DiffSet', 'diff_commit_count', RelationCounterField, null=True)
]
