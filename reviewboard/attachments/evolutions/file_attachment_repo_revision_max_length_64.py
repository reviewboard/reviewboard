from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileAttachment', 'repo_revision', initial=None,
                max_length=64),
]
