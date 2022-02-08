from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'summary', initial=None, db_index=True),
]
