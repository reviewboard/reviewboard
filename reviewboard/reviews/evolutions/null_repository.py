"""Change ReviewRequest.repository to allow NULL.

Version Added:
    1.5
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'repository', initial=None, null=True)
]
