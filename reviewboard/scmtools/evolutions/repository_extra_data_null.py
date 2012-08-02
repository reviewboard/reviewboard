from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'extra_data', initial=None, null=True),
]
