from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileAttachment', 'file', initial=None, max_length=512)
]
