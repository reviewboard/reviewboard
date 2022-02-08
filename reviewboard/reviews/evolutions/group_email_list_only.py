from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Group', 'email_list_only', models.BooleanField, initial=True)
]
