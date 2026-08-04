"""Added FileAttachment.local_site and user, and allow NULL on file.

Version Added:
    2.5
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField, ChangeField


MUTATIONS = [
    AddField('FileAttachment', 'user', models.ForeignKey, null=True,
             related_model='auth.User'),
    AddField('FileAttachment', 'local_site', models.ForeignKey, null=True,
             related_model='site.LocalSite'),
    ChangeField('FileAttachment', 'file', initial=None, null=True),
]
