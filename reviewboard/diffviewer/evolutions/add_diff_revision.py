from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('FileDiff', 'diff_revision', models.CharField, initial='', max_length=512),
    SQLMutation('populate_diff_revision', ["""
    UPDATE diffviewer_filediff
       SET diff_revision = source_revision
     WHERE diff_revision = ''
    """])
]
