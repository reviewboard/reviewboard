from __future__ import unicode_literals

from django.db import models
from django_evolution.mutations import AddField, SQLMutation


MUTATIONS = [
    AddField('ReviewRequest', 'shipit_count', models.IntegerField, initial=0,
             null=True),
    SQLMutation('populate_shipit_count', ["""
        UPDATE reviews_reviewrequest
           SET shipit_count = (
               SELECT COUNT(*)
                 FROM reviews_review
                WHERE reviews_review.review_request_id =
                      reviews_reviewrequest.id
                  AND reviews_review.public
                  AND reviews_review.ship_it
                  AND reviews_review.base_reply_to_id is NULL)
"""])
]
