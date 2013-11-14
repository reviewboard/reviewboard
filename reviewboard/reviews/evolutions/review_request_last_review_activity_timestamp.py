from __future__ import unicode_literals

from django_evolution.mutations import RenameField


MUTATIONS = [
    RenameField('ReviewRequest', 'last_review_timestamp',
                'last_review_activity_timestamp',
                db_column='last_review_timestamp'),
]
