"""Add FileDiff.diff_hash and parent_diff_hash, and rename diff/parent_diff.

``diff`` has been renamed to ``diff64``, and ``parent_diff`` to
``parent_diff64``.

Version Added:
    1.7
"""

from django_evolution.mutations import AddField, RenameField
from django.db import models


MUTATIONS = [
    RenameField('FileDiff', 'diff', 'diff64', db_column='diff_base64'),
    RenameField('FileDiff', 'parent_diff', 'parent_diff64',
                db_column='parent_diff_base64'),
    AddField('FileDiff', 'diff_hash', models.ForeignKey, null=True,
             related_model='diffviewer.FileDiffData'),
    AddField('FileDiff', 'parent_diff_hash', models.ForeignKey, null=True,
             related_model='diffviewer.FileDiffData'),
]
