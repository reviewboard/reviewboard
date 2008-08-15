from django_evolution.mutations import *

from djblets.util.fields import Base64Field
from djblets.util.dbevolution import FakeChangeFieldType


MUTATIONS = [
    FakeChangeFieldType('FileDiff', 'diff_base64', Base64Field),
    RenameField('FileDiff', 'diff_base64', 'diff', db_column='diff_base64'),
    AddField('FileDiff', 'parent_diff', Base64Field, initial="", db_column='parent_diff_base64'),
]

