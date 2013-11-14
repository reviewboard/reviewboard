from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileDiff', 'source_file', initial=None, max_length=1024),
    ChangeField('FileDiff', 'dest_file', initial=None, max_length=1024)
]
