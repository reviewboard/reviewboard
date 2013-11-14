from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'repository', initial=None, null=True)
]
