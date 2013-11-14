from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'bug_tracker', max_length=256),
]
