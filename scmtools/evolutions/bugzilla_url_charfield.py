from django.db import models
from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'bug_tracker', max_length=256),
]
