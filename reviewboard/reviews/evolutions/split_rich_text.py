from __future__ import unicode_literals

from django_evolution.mutations import AddField, SQLMutation
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'description_rich_text',
             models.BooleanField, initial=False),
    AddField('ReviewRequest', 'testing_done_rich_text',
             models.BooleanField, initial=False),
    AddField('ReviewRequestDraft', 'description_rich_text',
             models.BooleanField, initial=False),
    AddField('ReviewRequestDraft', 'testing_done_rich_text',
             models.BooleanField, initial=False),
    AddField('Review', 'body_top_rich_text',
             models.BooleanField, initial=False),
    AddField('Review', 'body_bottom_rich_text',
             models.BooleanField, initial=False),

    SQLMutation('review_request_rich_text_defaults', ["""
        UPDATE reviews_reviewrequest
           SET description_rich_text = rich_text,
               testing_done_rich_text = rich_text;
    """]),

    SQLMutation('review_request_draft_rich_text_defaults', ["""
        UPDATE reviews_reviewrequestdraft
           SET description_rich_text = rich_text,
               testing_done_rich_text = rich_text;
    """]),

    SQLMutation('review_rich_text_defaults', ["""
        UPDATE reviews_review
           SET body_top_rich_text = rich_text,
               body_bottom_rich_text = rich_text;
    """]),
]
