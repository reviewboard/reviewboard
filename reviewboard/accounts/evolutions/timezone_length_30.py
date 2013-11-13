from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    # http://code.google.com/p/reviewboard/issues/detail?id=3005
    # Increasing the size of timezone to deal with largest TZ.
    # len('America/Argentina/Buenos_Aires') == 30.
    ChangeField('Profile', 'timezone', max_length=30)
]
