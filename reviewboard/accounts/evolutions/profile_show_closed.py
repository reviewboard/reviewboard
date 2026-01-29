"""Rename Profile.show_submitted to show_closed.

Version Added:
    2.0
"""

from __future__ import annotations

from django_evolution.mutations import RenameField


MUTATIONS = [
    RenameField('Profile', 'show_submitted', 'show_closed'),
]
