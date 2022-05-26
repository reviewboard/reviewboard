"""Change Group.mailing_list from an EmailField to a CharField.

This doesn't actually perform a field type change (not an option in Django
Evolution at this point), but it does set the attributes required to match an
`EmailField`.

Version Added:
    2.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Group', 'mailing_list', initial=None, max_length=254)
]
