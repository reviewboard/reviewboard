"""Upgrade oauth2_provider from 0.9 to 1.6.3.

This is roughly equivalent to the following migrations in oauth2_provider
1.6.3:

* ``0001_initial``
* ``0002_auto_20190406_1805``
* ``0003_auto_20201211_1314``
* ``0004_auto_20200902_2022``
* ``0005_auto_20211222_2352``

These migrations are recorded in
:py:func:`~reviewboard.upgrade.post_upgrade_reset_oauth2_provider`.

Version Added:
    5.0
"""

from django.db import models
from django.utils import timezone
from django_evolution.mutations import AddField, ChangeField, ChangeMeta


MUTATIONS = [
    # Changes to the oauth2_provider_application table.
    AddField('Application', 'created', models.DateTimeField,
             initial=timezone.now),
    AddField('Application', 'updated', models.DateTimeField,
             initial=timezone.now),
    AddField('Application', 'algorithm', models.CharField,
             max_length=5, initial=''),
    ChangeField('Application', 'user', initial=None, null=True),
    ChangeField('Application', 'id', field_type=models.BigAutoField,
                primary_key=True),

    # Changes to the oauth2_provider_grant table.
    AddField('Grant', 'created', models.DateTimeField, initial=timezone.now),
    AddField('Grant', 'updated', models.DateTimeField, initial=timezone.now),
    AddField('Grant', 'code_challenge', models.CharField,
             max_length=128, initial=''),
    AddField('Grant', 'code_challenge_method', models.CharField,
             max_length=10, initial=''),
    AddField('Grant', 'nonce', models.CharField, max_length=255, initial=''),
    AddField('Grant', 'claims', models.TextField, initial=''),
    ChangeField('Grant', 'code', max_length=255, unique=True, db_index=False),
    ChangeField('Grant', 'redirect_uri', field_type=models.TextField),
    ChangeField('Grant', 'id', field_type=models.BigAutoField,
                primary_key=True),

    # Changes to the oauth2_provider_accesstoken table.
    AddField('AccessToken', 'source_refresh_token', models.OneToOneField,
             null=True, unique=True,
             related_model='oauth2_provider.RefreshToken'),
    AddField('AccessToken', 'id_token', models.OneToOneField,
             null=True, unique=True, related_model='oauth2_provider.IDToken'),
    AddField('AccessToken', 'created', models.DateTimeField,
             initial=timezone.now),
    AddField('AccessToken', 'updated', models.DateTimeField,
             initial=timezone.now),
    ChangeField('AccessToken', 'application', null=True),
    ChangeField('AccessToken', 'token', max_length=255, unique=True,
                db_index=False),
    ChangeField('AccessToken', 'id', field_type=models.BigAutoField,
                primary_key=True),

    # Changes to the oauth2_provider_refreshtoken table.
    AddField('RefreshToken', 'created', models.DateTimeField,
             initial=timezone.now),
    AddField('RefreshToken', 'updated', models.DateTimeField,
             initial=timezone.now),
    AddField('RefreshToken', 'revoked', models.DateTimeField, null=True),
    ChangeField('RefreshToken', 'access_token', null=True),
    ChangeField('RefreshToken', 'token', max_length=255, db_index=False),
    ChangeField('RefreshToken', 'id', field_type=models.BigAutoField,
                primary_key=True),
    ChangeMeta('RefreshToken', 'unique_together', [('token', 'revoked')]),
]
