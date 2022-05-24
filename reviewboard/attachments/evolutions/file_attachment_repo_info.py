"""Add repository-related fields to FileAttachment.

This includes:

* ``added_in_filediff``
* ``reop_revision``
* ``repo_path``
* ``repository``

Version Added:
    1.7.14
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileAttachment', 'repository', models.ForeignKey, null=True,
             related_model='scmtools.Repository'),
    AddField('FileAttachment', 'repo_revision', models.CharField,
             max_length=512, null=True, db_index=True),
    AddField('FileAttachment', 'repo_path', models.CharField,
             max_length=1024, null=True),
    AddField('FileAttachment', 'added_in_filediff', models.ForeignKey,
             null=True, related_model='diffviewer.FileDiff'),
]
