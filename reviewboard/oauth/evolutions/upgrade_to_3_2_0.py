"""Upgrade custom overridden models from oauth2_provider from 1.6.3 to 3.2.0.

Version Added:
    8.0
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField, ChangeField


MUTATIONS = [
    AddField('Application', 'allowed_origins', models.TextField,
             initial=''),
    AddField('Application', 'hash_client_secret', models.BooleanField,
             initial=True),
    AddField('Application', 'post_logout_redirect_uris', models.TextField,
             initial=''),
    ChangeField('Application', 'authorization_grant_type', max_length=44),
]
