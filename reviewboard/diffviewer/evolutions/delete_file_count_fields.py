"""Delete file_count fields from DiffCommit and DiffSet.

Version Added:
    4.0
"""

from django_evolution.mutations import DeleteField


MUTATIONS = [
    DeleteField('DiffSet', 'file_count'),
    DeleteField('DiffCommit', 'file_count'),
]
