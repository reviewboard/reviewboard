from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    ChangeField('Repository', 'path', initial=None, unique=False),
    ChangeField('Repository', 'name', initial=None, unique=False)
]
