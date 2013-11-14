from __future__ import unicode_literals

from django.db import models
from django_evolution.mutations import AddField, SQLMutation


MUTATIONS = [
    AddField('ReviewRequest', 'last_review_timestamp',
             models.DateTimeField, null=True),
    SQLMutation('populate_last_review_timestamp', ["""
        UPDATE reviews_reviewrequest
           SET last_review_timestamp = (
               SELECT reviews_review.timestamp
                 FROM reviews_review
                WHERE reviews_review.review_request_id =
                      reviews_reviewrequest.id
                  AND reviews_review.public
                ORDER BY reviews_review.timestamp DESC
                LIMIT 1)
"""])
]
