from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebHookTarget', 'repositories', initial=None, null=False),
]
