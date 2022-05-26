"""Change WebAPIToken.extra_data and policy to allow NULL values.

Version Added:
    2.5
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebAPIToken', 'policy', initial=None, null=True),
    ChangeField('WebAPIToken', 'extra_data', initial=None, null=True),
]
