"""Rename ReviewRequest.last_review_timestamp.

This has been renamed to ``last_review_activity_timestamp``.

Version Added:
    1.6.15
"""

from django_evolution.mutations import RenameField


MUTATIONS = [
    RenameField('ReviewRequest', 'last_review_timestamp',
                'last_review_activity_timestamp',
                db_column='last_review_timestamp'),
]
