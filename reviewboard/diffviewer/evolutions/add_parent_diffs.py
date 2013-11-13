from __future__ import unicode_literals

from django_evolution.mutations import AddField, RenameField
from djblets.db.evolution import FakeChangeFieldType
from djblets.db.fields import Base64Field


MUTATIONS = [
    FakeChangeFieldType('FileDiff', 'diff_base64', Base64Field),
    RenameField('FileDiff', 'diff_base64', 'diff', db_column='diff_base64'),
    AddField('FileDiff', 'parent_diff', Base64Field, initial="",
             db_column='parent_diff_base64'),
]
