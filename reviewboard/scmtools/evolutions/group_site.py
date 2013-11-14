from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'path', initial=None, unique=False),
    ChangeField('Repository', 'name', initial=None, unique=False)
]
