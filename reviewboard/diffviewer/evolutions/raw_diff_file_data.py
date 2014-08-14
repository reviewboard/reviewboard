from __future__ import unicode_literals

from django_evolution.mutations import AddField, RenameField, RenameModel
from django.db import models


MUTATIONS = [
    RenameModel('FileDiffData', 'LegacyFileDiffData',
                db_table='diffviewer_filediffdata'),
    RenameField('FileDiff', 'diff_hash', 'legacy_diff_hash',
                db_column='diff_hash_id'),
    RenameField('FileDiff', 'parent_diff_hash', 'legacy_parent_diff_hash',
                db_column='parent_diff_hash_id'),
    AddField('FileDiff', 'diff_hash', models.ForeignKey, null=True,
             db_column='raw_diff_hash_id',
             related_model='diffviewer.RawFileDiffData'),
    AddField('FileDiff', 'parent_diff_hash', models.ForeignKey, null=True,
             db_column='raw_parent_diff_hash_id',
             related_model='diffviewer.RawFileDiffData'),
]
