from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebAPIToken', 'policy', initial=None, null=True),
    ChangeField('WebAPIToken', 'extra_data', initial=None, null=True),
]
