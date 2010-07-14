from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('ScreenshotComment', 'issue_opened', models.BooleanField,
        initial=False),
    AddField('ScreenshotComment', 'issue_status', models.CharField,
        initial=u'', max_length=1, db_index=True)
]

