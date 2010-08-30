from django_evolution.mutations import ChangeField
from django.db import models


MUTATIONS = [
    ChangeField('ReviewRequest', 'repository', initial=None, null=True)
]
