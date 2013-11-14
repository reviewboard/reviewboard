from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models

MUTATIONS = [
    AddField('Comment', 'issue_opened', models.BooleanField, initial=False),
    AddField('Comment', 'issue_status', models.CharField,
             initial='', max_length=1, null=True, db_index=True),
    AddField('ScreenshotComment', 'issue_opened', models.BooleanField,
             initial=False),
    AddField('ScreenshotComment', 'issue_status', models.CharField,
             initial='', max_length=1, null=True, db_index=True)
]
