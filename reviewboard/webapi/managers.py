"""Managers for Web API related models.

Version Added:
    5.0.5
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from django.db.models import F, Q
from django.utils import timezone
from djblets.secrets.token_generators import token_generator_registry
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.symbols import UNSET, Unsettable
from djblets.webapi.managers import (
    WebAPITokenManager as DjbletsWebAPITokenManager)
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard10_0Warning
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet
    from typelets.json import JSONDict, JSONDictImmutable

    from reviewboard.webapi.models import WebAPIToken


class WebAPITokenManager(DjbletsWebAPITokenManager):
    """Manager for the reviewboard.webapi.managers.WebAPIToken model.

    Version Added:
        5.0.5
    """

    @deprecate_non_keyword_only_args(RemovedInReviewBoard10_0Warning)
    def get_or_create_client_token(
        self,
        *,
        user: AbstractBaseUser | AnonymousUser,
        client_name: str,
        expires: Unsettable[datetime.datetime | None] = UNSET,
        min_validity_secs: int = 5 * 60,
        default_extra_data: Unsettable[JSONDictImmutable | None] = UNSET,
        default_policy: Unsettable[JSONDictImmutable | None] = UNSET,
        local_site: (LocalSite | None) = None,
        ignore_deprecated: bool = False,
    ) -> tuple[WebAPIToken, bool]:
        """Return an API token for authenticating a client to Review Board.

        If the token does not already exist for the client, this will create
        one. If multiple client tokens already exist, this will return the
        one that has no expiration date or the furthest expiration date.
        If the eligible client token is expired or invalid, a new one will
        be created.

        By default, tokens with less than 5 minutes of validity left are
        excluded from results, which may cause another token to be used or
        a new token to be created. This helps avoid issues with tokens
        being returned that are immediately unusable. This validity window
        can be increased for longer-running operations.

        Version Changed:
            8.1:
            * By default, tokens with less than 5 minutes of validity left
              are excluded.

            * All arguments are now keyword-only. This will be required in
              Review Board 10.

            * Added the ``default_extra_data``, ``default_policy``,
              ``ignore_deprecated``, ``local_site``, and ``min_validity_secs``
              arguments.

        Args:
            user (django.contrib.auth.models.User):
                The user who owns the token.

            client_name (str):
                The name of the client that the token is for.

            expires (datetime.datetime, optional):
                The expiration datetime of new tokens.

                This defaults to the ``client_token_expiration`` value in the
                site configuration added to the creation datetime of the token.

                For example, if the ``client_token_expiration`` is set to 5,
                the token will expire in 5 days from when it is created.

            min_validity_secs (int, optional):
                The minimum number of seconds left in any existing token
                considered for a result.

                This defaults to 5 minutes.

                Version Added:
                    8.1

            default_extra_data (dict, optional):
                Extra data to set for new tokens.

                Version Added:
                    8.1

            default_policy (dict, optional):
                An explicit policy to set for new tokens.

                Version Added:
                    8.1

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site to associate with this token.

                Version Added:
                    8.1

            ignore_deprecated (bool, optional):
                Whether to ignore deprecated existing tokens.

                Version Added:
                    8.1

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
        valid_until = timezone.now()

        if min_validity_secs > 0:
            valid_until += datetime.timedelta(seconds=min_validity_secs)

        tokens: QuerySet[WebAPIToken] = (
            self.filter(
                Q(user=user) &
                Q(valid=True) &
                (Q(expires__isnull=True) |
                 Q(expires__gt=valid_until)) &
                LocalSite.objects.build_q(local_site=local_site)
            )
            .order_by(F('expires').desc(nulls_first=True))
        )

        for token in tokens:
            if (token.extra_data.get('client_name') == client_name and
                (not ignore_deprecated or not token.is_deprecated())):
                # This is an active token. Return it as-is.
                return token, False

        if expires is UNSET:
            siteconfig = SiteConfiguration.objects.get_current()
            expire_amount = siteconfig.get('client_token_expiration')

            if expire_amount and isinstance(expire_amount, int):
                expires = (timezone.now() +
                           datetime.timedelta(days=expire_amount))
            else:
                expires = None

        if default_policy is UNSET:
            policy = None
        else:
            policy = default_policy

        extra_data: JSONDict = {}

        if default_extra_data and default_extra_data is not UNSET:
            extra_data.update(default_extra_data)

        extra_data['client_name'] = client_name

        generator = token_generator_registry.get_default().token_generator_id
        token = self.generate_token(
            expires=expires,
            extra_data=extra_data,
            local_site=local_site,
            note=f'API token automatically created for {client_name}.',
            token_generator_id=generator,
            token_info={
                'token_type': 'rbp',
            },
            user=user,
            policy=policy,
        )

        return token, True
