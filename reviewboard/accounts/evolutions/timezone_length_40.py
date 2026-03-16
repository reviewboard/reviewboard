"""Increase max_length of Profile.timezone from 30 to 40.

Version Added:
    8.0
"""

from __future__ import annotations

from django_evolution.mutations import ChangeField


MUTATIONS = [
    # Increasing the size of timezone to deal with new largest TZ:
    # len('America/Argentina/ComodRivadavia') == 32
    ChangeField('Profile', 'timezone', initial=None, max_length=40),
]
