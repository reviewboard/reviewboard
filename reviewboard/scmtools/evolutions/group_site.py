"""Remove the unique flag from Repository.name and Repository.path.

Version Added:
    1.6
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'path', initial=None, unique=False),
    ChangeField('Repository', 'name', initial=None, unique=False)
]
