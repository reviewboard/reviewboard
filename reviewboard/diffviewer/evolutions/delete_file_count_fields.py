from django_evolution.mutations import DeleteField


MUTATIONS = [
    DeleteField('DiffSet', 'file_count'),
    DeleteField('DiffCommit', 'file_count'),
]
