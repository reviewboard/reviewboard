"""Managers for Web API related models.

Version Added:
    5.0.5
"""

from __future__ import annotations

import datetime
from typing import Optional, TYPE_CHECKING, Tuple, Union

from django.db.models import F
from djblets.secrets.token_generators import token_generator_registry
from djblets.webapi.managers import (
    WebAPITokenManager as DjbletsWebAPITokenManager)

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from reviewboard.webapi.models import WebAPIToken


class WebAPITokenManager(DjbletsWebAPITokenManager):
    """Manager for the reviewboard.webapi.managers.WebAPIToken model.

    Version Added:
        5.0.5
    """

    def get_or_create_client_token(
        self,
        user: Union[AbstractBaseUser, AnonymousUser],
        client_name: str,
        expires: Optional[datetime.datetime] = None,
    ) -> Tuple[WebAPIToken, bool]:
        """Get a user's API token for authenticating a client to Review Board.

        If the token does not already exist for the client, this will create
        one. If multiple client tokens already exist, this will return the
        one that has no expiration date or the furthest expiration date.
        If the eligible client token is expired or invalid, a new one will
        be created.

        Args:
            user (django.contrib.auth.models.User):
                The user who owns the token.

            client_name (str):
                The name of the client that the token is for.

            expires (datetime.datetime, optional):
                The expiration date of the token. This defaults to no
                expiration.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (reviewboard.webapi.models.WebAPIToken):
                    The token for authenticating the client.

                1 (bool):
                    Whether a new token was created.

        Raises:
            djblets.webapi.errors.WebAPITokenGenerationError:
                The token was not able to be generated after the max
                number of collisions were hit.
        """
        tokens = self.filter(user=user, valid=True).order_by(
            F('expires').desc(nulls_first=True))

        for token in tokens:
            if (token.extra_data.get('client_name') == client_name and
                not token.is_expired()):
                return token, False
            elif token.is_expired():
                # The rest of the tokens are also expired.
                break

        generator = token_generator_registry.get_default().token_generator_id
        token = self.generate_token(
            expires=expires,
            extra_data={
                'client_name': client_name,
            },
            note=f'API token automatically created for {client_name}.',
            token_generator_id=generator,
            token_info={
                'token_type': 'rbp',
            },
            user=user)

        return token, True
