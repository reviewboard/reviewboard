"""Change WebAPIToken to allow for different token formats.

This increases the max length for tokens and adds a ``token_generator_id``
field to allow for new token formats other than the existing SHA1 format.
This also adds fields to support the expiration and invalidation of tokens.

Version Added:
    5.0
"""

from django_evolution.mutations import AddField, ChangeField
from django.db import models


MUTATIONS = [
    ChangeField('WebAPIToken', 'token', max_length=255),
    AddField('WebAPIToken', 'token_generator_id', models.CharField,
             max_length=255, initial='legacy_sha1'),
    AddField('WebAPIToken', 'last_used', models.DateTimeField, null=True),
    AddField('WebAPIToken', 'expires', models.DateTimeField, null=True),
    AddField('WebAPIToken', 'valid', models.BooleanField, initial=True),
    AddField('WebAPIToken', 'invalid_date', models.DateTimeField, null=True),
    AddField('WebAPIToken', 'invalid_reason', models.TextField, initial=''),
]
