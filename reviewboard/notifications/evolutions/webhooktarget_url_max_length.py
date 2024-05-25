"""Evolution to increase the max length of the URL field.

Version Added:
    7.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('WebHookTarget', 'url', initial=None, max_length=512),
]
