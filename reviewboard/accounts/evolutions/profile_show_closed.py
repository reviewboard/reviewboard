from django_evolution.mutations import RenameField
from django.db import models


MUTATIONS = [
    RenameField('Profile', 'show_submitted', 'show_closed'),
]
