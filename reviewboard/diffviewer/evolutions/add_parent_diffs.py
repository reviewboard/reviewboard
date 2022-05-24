"""Add FileDiff.parent_diff and rename FileDiff.diff_base64 to diff.

``FileDiff.diff_base64`` is also changed to use a
:py:class:`djblets.db.fields.Base64Field`.

Version Added:
    1.0
"""

from django_evolution.mutations import AddField, RenameField
from djblets.db.evolution import FakeChangeFieldType
from djblets.db.fields import Base64Field


MUTATIONS = [
    FakeChangeFieldType('FileDiff', 'diff_base64', Base64Field),
    RenameField('FileDiff', 'diff_base64', 'diff', db_column='diff_base64'),
    AddField('FileDiff', 'parent_diff', Base64Field, initial="",
             db_column='parent_diff_base64'),
]
