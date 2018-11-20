from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'name', initial=None, max_length=255),
]
