"""Add rich_text fields to comments, reviews, and review requests.

Version Added:
    2.0
"""

from django_evolution.mutations import AddField
from django.db import models

MUTATIONS = [
    AddField('Comment', 'rich_text', models.BooleanField,
             initial=False),
    AddField('FileAttachmentComment', 'rich_text', models.BooleanField,
             initial=False),
    AddField('ScreenshotComment', 'rich_text', models.BooleanField,
             initial=False),
    AddField('Review', 'rich_text', models.BooleanField, initial=False),
    AddField('ReviewRequest', 'rich_text', models.BooleanField, initial=False),
    AddField('ReviewRequestDraft', 'rich_text', models.BooleanField,
             initial=False)
]
