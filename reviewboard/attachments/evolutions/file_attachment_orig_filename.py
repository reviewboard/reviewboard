from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileAttachment', 'orig_filename', models.CharField,
             max_length=256, null=True)
]
