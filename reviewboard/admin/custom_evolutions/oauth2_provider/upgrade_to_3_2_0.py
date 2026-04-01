"""Upgrade oauth2_provider from 1.6.3 to 3.2.0.

This is roughly equivalent to the following migrations in oauth2_provider
3.2.0:

* ``0006_alter_application_client_secret``
* ``0007_application_post_logout_redirect_uris``
* ``0008_alter_accesstoken_token``
* ``0009_add_hash_client_secret``
* ``0010_application_allowed_origins``
* ``0011_refreshtoken_token_family``
* ``0012_add_token_checksum``
* ``0013_alter_application_authorization_grant_type_device``

These migrations are recorded in
:py:func:`~reviewboard.upgrade.post_upgrade_reset_oauth2_provider`.

Version Added:
    9.0
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from django.db import models
from django_evolution.mutations import AddField, ChangeField, SQLMutation
from oauth2_provider.models import TokenChecksumField

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.backends.utils import CursorWrapper
    from django_evolution.mutations.base import Simulation
    from django_evolution.utils.sql import SQLStatement


def _simulate_populate_token_checksums(
    simulation: Simulation,
) -> None:
    """Simulate the token checksum population.

    This is a no-op, as the data migration does not affect the database
    schema signature. The schema changes are handled by the surrounding
    :py:class:`~django_evolution.mutations.AddField` and
    :py:class:`~django_evolution.mutations.ChangeField` mutations.

    Args:
        simulation (django_evolution.evolve.evolve_app_task.Simulation):
            The simulation state.
    """
    pass


def _populate_token_checksums(
    cursor: CursorWrapper,
) -> Sequence[SQLStatement]:
    """Compute and store token checksums for all existing access tokens.

    This replicates the data migration in oauth2_provider's
    ``0012_add_token_checksum`` migration, computing SHA-256 checksums in
    Python to remain database-agnostic.

    Args:
        cursor (django.db.backends.utils.CursorWrapper):
            The database cursor.

    Returns:
        list of tuple:
        A list of SQL update statements with parameters to set each
        access token's checksum.
    """
    qn = cursor.db.ops.quote_name

    cursor.execute(
        f'SELECT {qn("id")}, {qn("token")} FROM '
        f'{qn("oauth2_provider_accesstoken")}'
    )

    return [
        (
            (
                f'UPDATE {qn("oauth2_provider_accesstoken")}'
                f' SET {qn("token_checksum")} = %s'
                f' WHERE {qn("id")} = %s'
            ),
            (
                hashlib.sha256(row[1].encode('utf-8')).hexdigest(),
                row[0],
            ),
        )
        for row in cursor.fetchall()
    ]


MUTATIONS = [
    # Changes to the oauth2_provider_application table.
    AddField('Application', 'allowed_origins', models.TextField,
             initial=''),
    AddField('Application', 'hash_client_secret', models.BooleanField,
             initial=True),
    AddField('Application', 'post_logout_redirect_uris', models.TextField,
             initial=''),
    ChangeField('Application', 'authorization_grant_type', max_length=44),

    # Changes to the oauth2_provider_accesstoken table.
    #
    # This is a multi-step process equivalent to oauth2_provider's
    # 0012_add_token_checksum migration:
    #
    # 1. Add token_checksum as nullable (no unique constraint yet).
    # 2. Populate checksums for all existing tokens via Python.
    # 3. Make token_checksum non-null, unique, and indexed.
    AddField('AccessToken', 'token_checksum', TokenChecksumField,
             max_length=64, null=True),
    SQLMutation('populate_token_checksums', [_populate_token_checksums],
                update_func=_simulate_populate_token_checksums),
    ChangeField('AccessToken', 'token_checksum', null=False, unique=True,
                db_index=True, initial='_'),

    ChangeField('AccessToken', 'token', field_type=models.TextField,
                max_length=None, unique=False),

    # Changes to the oauth2_provider_refreshtoken table.
    AddField('RefreshToken', 'token_family', models.UUIDField, null=True,
             max_length=32),
]
