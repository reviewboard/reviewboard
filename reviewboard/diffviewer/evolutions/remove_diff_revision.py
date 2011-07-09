from django_evolution.mutations import DeleteField


MUTATIONS = [
    DeleteField('FileDiff', 'diff_revision')
]
