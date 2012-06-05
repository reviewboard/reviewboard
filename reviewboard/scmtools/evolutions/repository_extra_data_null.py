from django_evolution.mutations import ChangeField
from django.db import models
from djblets.util.fields import JSONField


MUTATIONS = [
    ChangeField('Repository', 'extra_data', initial=None, null=True),
]
