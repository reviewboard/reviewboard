"""Service account creation, management, and registration.

Version Added:
    8.1
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone
from django.utils.translation import gettext as _
from djblets.avatars.services import URLAvatarService
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED,
                                         DEFAULT_ERRORS,
                                         NOT_REGISTERED,
                                         UNREGISTER)
from djblets.siteconfig.models import SiteConfiguration
from typelets.symbols import UNSET

from reviewboard.accounts.errors import ServiceAccountUserError
from reviewboard.accounts.models import Profile
from reviewboard.avatars import avatar_services
from reviewboard.registries.registry import Registry
from reviewboard.webapi.models import WebAPIToken

if TYPE_CHECKING:
    from collections.abc import Mapping

    from typelets.json import JSONDictImmutable
    from typelets.symbols import Unsettable

    from reviewboard.site.models import LocalSite


logger = logging.getLogger(__name__)


class ServiceAccount:
    """A service account used for automation and integration purposes.

    Service accounts are special entities that are allowed to perform
    operations using the Review Board API, but cannot otherwise log in,
    and do not take a seat on the license.

    They're intended for extensions and integrations that need to associate
    data with a managed user account or pass an API token to another service.

    Service accounts are created by either providing the necessary attributes
    in a subclass or when constructing an instance. In either case, the
    instance needs to be registered in :py:data:`service_account_registry`
    prior to use.

    Version Added:
        8.1
    """

    ##########################################
    # Class customization/instance variables #
    ##########################################

    #: The unique ID of the service account.
    #:
    #: This must be in :term:`slug` format.
    #:
    #: This ID will be used as the username for new accounts if
    #: :py:attr:`preferred_username` is not provided on the class or
    #: during construction.
    service_account_id: str = ''

    #: The name of this service account.
    #:
    #: This will be used for any managed users.
    name: str = 'Service Account'

    #: The e-mail address for the service account.
    #:
    #: This will be used for any managed users. If not provided, the
    #: default e-mail address for the server will be used.
    email: str = ''

    #: The preferred username for managed users.
    #:
    #: This will be used instead of :py:attr:`service_account_id` as the
    #: username used when attempting to look up or create a user account.
    preferred_username: str = ''

    #: Explicit avatars to use for managed accounts.
    #:
    #: This is a mapping of resolution indicators (e.g., ``1x``, ``2x``,
    #: ``3x``) to image URLs (absolute or relative).
    #:
    #: If not set, avatars will not be configured.
    avatar_urls: (Mapping[str, str] | None) = None

    #: The version of the profile state.
    #:
    #: Service accounts should explicitly increment this value whenever they
    #: need to ensure new state (e-mail address, name, or avatars) is
    #: saved to the managed user.
    profile_version: int = 1

    #: The expiration time for any created API tokens, in seconds.
    #:
    #: When creating a new API token for access, this will be used to
    #: set the expiration for the token.
    #:
    #: This defaults to 30 days.
    api_token_expiration_secs: (int | None) = 60 * 60 * 24 * 30

    #: The token policy document to use for any created API tokens.
    #:
    #: It's recommended that a token policy document is set that covers
    #: the minimum set of permissions needed for the service account to
    #: perform its responsibilities.
    #:
    #: To ensure older tokens with an outdated policy are not used,
    #: increment :py:attr:`api_token_version` when updating the policy.
    api_token_policy: (JSONDictImmutable | None) = None

    #: The version of the API token state.
    #:
    #: Service accounts should explicitly increment this value whenever they
    #: need to ensure a new expiration or token policy is used the next time
    #: a token is accessed.
    api_token_version: int = 1

    ######################
    # Instance variables #
    ######################

    #: Whether an explicit username is claimed during construction.
    _claim_username: bool

    #: The cached managed user for this service account.
    _user: User | None

    def __init__(
        self,
        *,
        api_token_expiration_secs: Unsettable[int] = UNSET,
        api_token_policy: Unsettable[JSONDictImmutable] = UNSET,
        api_token_version: Unsettable[int] = UNSET,
        avatar_urls: Unsettable[Mapping[str, str]] = UNSET,
        claim_username: bool = False,
        email: Unsettable[str] = UNSET,
        name: Unsettable[str] = UNSET,
        preferred_username: Unsettable[str | None] = UNSET,
        profile_version: Unsettable[int] = UNSET,
        service_account_id: Unsettable[str] = UNSET,
    ) -> None:
        """Initialize the service account.

        This can override any default attributes on the class, allowing
        extensions to either maintain service accounts fully or partly
        as subclasses or through instantiation.

        To claim a specific username (typically when one was already created
        and stored in the extension's settings), pass ``claim_username=True``
        and :samp:`preferred_username={username}`.

        Args:
            api_token_expiration_secs (int, optional):
                The expiration time for any created API tokens, in seconds.

                See :py:attr:`api_token_expiration`.

            api_token_policy (dict, optional):
                The token policy document to use for any created API tokens.

                See :py:attr:`api_token_policy`.

            api_token_version (dict, optional):
                The version of the API token state.

                See :py:attr:`api_token_version`.

            avatar_urls (dict, optional):
                Explicit avatars to use for managed accounts.

                See :py:attr:`avatar_urls`.

            claim_username (bool, optional):
                Whether to claim the preferred username as the managed
                service account user, if it already exists in the database.

                If set to ``True``, it's best to pass ``preferred_username``.

            email (str, optional):
                The e-mail address for the service account.

                See :py:attr:`email`.

            name (str, optional):
                The name of this service account.

                See :py:attr:`name`.

            preferred_username (str, optional):
                The preferred username for managed users.

                This should be provided if passing ``claim_username=True``.

                See :py:attr:`preferred_username``.

            profile_version (int, optional):
                The version of the profile state.

                See :py:attr:`profile_version`.

            service_account_id (str, optional):
                The unique ID of the service account.

                See :py:attr:`service_account_id`.

        Raises:
            ValueError:
                A required argument or attribute was not provided.
        """
        if service_account_id is not UNSET:
            self.service_account_id = service_account_id

        if not self.service_account_id:
            raise ValueError(
                f'{type(self).__name__}.service_account_id must be set or '
                f'provided during construction.'
            )

        if name is not UNSET:
            self.name = name

        if avatar_urls is not UNSET:
            self.avatar_urls = avatar_urls

        if email and email is not UNSET:
            self.email = email
        elif not self.email:
            siteconfig = SiteConfiguration.objects.get_current()
            noreply_email = siteconfig.get('mail_default_from')

            if noreply_email and isinstance(noreply_email, str):
                self.email = noreply_email

        if preferred_username and preferred_username is not UNSET:
            self.preferred_username = preferred_username
        elif not self.preferred_username:
            self.preferred_username = self.service_account_id

        if profile_version is not UNSET:
            self.profile_version = profile_version

        if api_token_expiration_secs is not UNSET:
            self.api_token_expiration_secs = api_token_expiration_secs

        if api_token_policy is not UNSET:
            self.api_token_policy = api_token_policy

        if api_token_version is not UNSET:
            self.api_token_version = api_token_version

        self._claim_username = claim_username
        self._user = None

    def get_user(
        self,
        *,
        _claim_map: (dict[str, ServiceAccount] | None) = None,
        _max_attempts: int = 100,
    ) -> User:
        """Return a user managed by this service account.

        If the user was already fetched from the database, it will be
        returned as-is. Otherwise, a new user will be looked up or created.
        This works as follows:

        1. If the service account is registered as claiming a specific
           username that already exists (such as one stored from a prior
           creation), that user will be returned.

        2. If one is not claimed, this will attempt to look up an existing
           user that's recorded as being associated with
           :py:attr:`service_account_id`.

        3. If the user was not found, one will be created.

        The username defined by :py:attr:`preferred_username` (or, if not set,
        :py:attr:`service_account_id`) will be used for lookup or creation.
        If a user is not being claimed by this service account, and another
        user already has this username, this will add a number to the username
        (starting with 1, then 2, etc.) until it finds a user that it can
        fetch or create.

        Args:
            _claim_map (dict, optional):
                A map for storing a claim for a username.

                This is meant only for internal use and is not considered
                part of the stable API.

            _max_attempts (int, optional):
                The default maximum number of attempts for claiming a user.

                This is meant only for internal use and is not considered
                part of the stable API.

        Returns:
            django.contrib.auth.models.User:
            The resulting user.

        Raises:
            reviewboard.accounts.errors.ServiceAccountUserError:
                A user could not be fetched, created, or claimed, and the
                maximum number of attempts have run out.
        """
        user = self._user

        if user is not None:
            return user

        # We'll set a default claim map if one isn't provided (the
        # non-registry case). Any username we may create will go in here
        # until we get a result. In the registry case, this will happen
        # within a thread lock, so there's no risk of two threads trying
        # to fetch or create the same user at the same time.
        if _claim_map is not None:
            claim_map = _claim_map
        else:
            claim_map = {}

        # If we're claiming the username, then we'll only need/want to
        # consider the explicit username given. If something goes wrong
        # here, we need to fail early instead of trying other variations,
        # otherwise state can get out of sync.
        #
        # Note that if the username has been claimed by multiple service
        # accounts, this is going to prevent the user from being fetched.
        preferred_username = self.preferred_username
        claim_username = self._claim_username

        if claim_username:
            if preferred_username in claim_map:
                # This username was already claimed somewhere else, but is
                # being claimed here. This is a fatal error.
                raise ServiceAccountUserError(
                    _(
                        'Cannot claim the service account username '
                        '"{username}". It has already been claimed by another '
                        'service account. This may be a conflict between two '
                        'extensions or a configuration error. Contact '
                        'support if you need assistance.'
                    ).format(username=preferred_username),
                )

            max_attempts = 1
        else:
            max_attempts = _max_attempts

        attempts = 0
        service_account_id = self.service_account_id
        base_username = preferred_username
        username = base_username
        created = False

        while attempts < max_attempts and user is None:
            attempts += 1

            # Try to fetch the user, creating if it doesn't exist. Django
            # will handle any IntegrityError checks from the creation and
            # attempt a re-fetch if needed.
            #
            # Note that unlike the service account code that existed in our
            # other implementations that preceded this, we're not creating an
            # object with the first/last names and e-mail populated, so we're
            # not going to be in a situation where the username matches but
            # the others don't, which would have triggered an IntegrityError.
            attempt_claim = False

            if username not in claim_map:
                attempt_claim = True

                try:
                    claim_map[username] = self
                    user, created = (
                        User.objects
                        .select_related('profile')
                        .get_or_create(username=username)
                    )
                except IntegrityError as e:
                    # This really should not happen, but we want to guard
                    # against it and try another variation (if we have
                    # attempts left).
                    user = None
                    created = False

                    logger.exception(
                        'Unexpected database integrity error fetching or '
                        'creating the service account user "%s". Trying '
                        'another variant. Error: %s',
                        username, e,
                    )

                if user:
                    # We got a user.
                    #
                    # This may be a user we explicitly want to claim (in which
                    # case we'll ensure the right state), a user matching the
                    # service ID (in which case we'll use it), or someone
                    # else's user (in which case we'll skip it).
                    if created or claim_username:
                        # We'll finish the loop and prepare this user.
                        break

                    # Check the implicit case.
                    if ((profile := user.get_profile(cached_only=True)) and
                        (service_account_id ==
                         profile.extra_data.get('service_account_id'))):
                        # This matches the service account, so finish the loop
                        # and prepare this user.
                        break

            # This was not a success. Remove from the claim map, clean
            # up state, and prepare for the next one.
            if attempt_claim:
                del claim_map[username]

            user = None
            created = False
            username = f'{base_username}-{attempts}'

        # We're out of the loop.
        #
        # At this point, we either have a user we can prepare and return,
        # or we've hit our max attempts.
        if user is None:
            # We've hit our max attempts. Log that.
            trace_id = str(uuid4())

            logger.error(
                '[%s] Failed to create a unique service account user for '
                '"%s". Tried %s variants, which were all taken. '
                'You may need to remove a user or contact support '
                'for help',
                trace_id, base_username, max_attempts,
            )

            raise ServiceAccountUserError(_(
                'Failed to create a unique service account user for '
                '"{username}" (error ID {error_id}). Please contact support.'
            ).format(error_id=trace_id,
                     username=base_username))

        # We have a user.
        if created:
            profile = Profile(user=user)
        else:
            profile = user.get_profile(cached_only=True) or Profile(user=user)

        profile_version = self.profile_version

        # If the user is newly-created, or has outdated state, then set
        # everything on the user.
        if (created or
            not profile.extra_data.get('service_account_id') or
            profile.extra_data.get('_profile_ver') != profile_version):
            # Create some default identifying information for the account.
            name = self.name
            email = self.email

            if name:
                # Default the name to the service account's name, but split
                # along spaces about half-way through to distribute across
                # the first/last name fields.
                name_parts = name.split(' ')

                if len(name_parts) > 1:
                    mid = len(name_parts) // 2
                    first_name = ' '.join(name_parts[:mid])
                    last_name = ' '.join(name_parts[mid:])
                else:
                    first_name = name
                    last_name = ''
            else:
                # Or if there's no name set, just use "Service Account".
                first_name = 'Service'
                last_name = 'Account'

            # Update the user to reflect that.
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.set_unusable_password()
            user.save(update_fields=(
                'email',
                'first_name',
                'last_name',
                'password',
            ))

            profile.should_send_email = False
            profile.extra_data['service_account_id'] = service_account_id
            profile.extra_data['_profile_ver'] = profile_version

            if profile.pk is None:
                profile.save()
                setattr(user, '_profile', profile)
            else:
                profile.save(update_fields=(
                    'extra_data',
                    'should_send_email',
                ))

            # If any avatars are set, associate them now.
            avatar_urls = self.avatar_urls

            if avatar_urls:
                avatar_service = avatar_services.get_avatar_service(
                    URLAvatarService.avatar_service_id,
                )
                avatar_service.setup(user, avatar_urls)

        self._user = user

        return user

    def get_api_token(
        self,
        *,
        local_site: LocalSite | None,
        min_validity_secs: int = 60 * 60 * 2,
    ) -> WebAPIToken:
        """Return an API token for the service account.

        If a matching token already exists, and will remain valid for a
        minimum amount of time (2 hours by default, if the configured
        expiration is more than that), then the token will be returned.

        If a valid token does not already exist, a new one will be created
        with policy document and expiration time provided on the service
        account.

        The API token will be keyed off from the :py:attr:`api_token_version`
        number.

        Note that this does not check if the expiration time or policy
        document has been modified to be different from those set on this
        service account. What's in the database will be returned as-is.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site the token must be tied to.

            min_validity_secs (int, optional):
                The minimum number of seconds left in any existing token
                considered for a result.

                This defaults to 2 hours.

        Returns:
            reviewboard.webapi.models.WebAPIToken:
            The resulting API token.
        """
        user = self.get_user()

        if expires_secs := self.api_token_expiration_secs:
            expires = timezone.now() + timedelta(seconds=expires_secs)

            if expires_secs < min_validity_secs:
                # The configured expiration time for the token is less than
                # the minimum time we're looking for, so ignore the minimum.
                min_validity_secs = 0
        else:
            expires = None

        return WebAPIToken.objects.get_or_create_client_token(
            client_name=(
                f'{self.service_account_id}_'
                f'v{self.api_token_version}'
            ),
            default_policy=self.api_token_policy,
            ignore_deprecated=True,
            expires=expires,
            min_validity_secs=min_validity_secs,
            local_site=local_site,
            user=user,
        )[0]


class ServiceAccountRegistry(Registry[ServiceAccount]):
    """A registry tracking service accounts.

    This tracks all service accounts registered via Review Board or
    extensions. Registered service accounts can only log in via API tokens,
    and do not take a seat on the license.

    Version Added:
        8.1
    """

    lookup_attrs = ('service_account_id',)

    default_errors = {
        **DEFAULT_ERRORS,
        ALREADY_REGISTERED: _(
            'Could not register service account %(item)s. It is already '
            'registered.'
        ),
        ATTRIBUTE_REGISTERED: _(
            'Could not register service account %(item)s: Another service '
            'account (%(duplicate)s) is already registered with the same ID.'
        ),
        NOT_REGISTERED: _(
            'No service account was found with the ID "%(attr_value)s".'
        ),
        UNREGISTER: _(
            'Could not unregister service account %(item)s: This service '
            'account was not yet registered.'
        ),
    }

    ######################
    # Instance variables #
    ######################

    #: A mapping of usernames to their service accounts.
    _by_username: dict[str, ServiceAccount]

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the registry.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent.

            **kwargs (tuple):
                Keyword arguments to pass to the parent.
        """
        self._by_username = {}

        super().__init__(*args, **kwargs)

    def get_for_service_account_id(
        self,
        service_account_id: str,
    ) -> ServiceAccount | None:
        """Return a service account with the given ID.

        Args:
            service_account_id (str):
                The ID of the service account.

        Returns:
            ServiceAccount:
            The registered service account, or ``None`` if not found.
        """
        return self.get('service_account_id', service_account_id)

    def get_for_username(
        self,
        username: str,
    ) -> ServiceAccount | None:
        """Return a service account for a given username.

        Args:
            username (str):
                The username to check for.

        Returns:
            ServiceAccount:
            The registered service account, or ``None`` if not found.
        """
        self.populate()

        return self._by_username.get(username)

    def on_item_registered(
        self,
        item: ServiceAccount,
    ) -> None:
        """Handle post-registration of a service account.

        This will fetch or create the managed user and add it to the
        username map.

        Args:
            item (ServiceAccount):
                The service account that was registered.
        """
        # Fetch or create the user, caching it in the process. This is being
        # done in this registration thread lock, preventing collisions
        try:
            item.get_user(_claim_map=self._by_username)
        except ServiceAccountUserError:
            return

    def on_item_unregistered(
        self,
        item: ServiceAccount,
    ) -> None:
        """Handle post-unregistration of a service account.

        This will remove its claim from the username map.

        Args:
            item (ServiceAccount):
                The service account that was unregistered.
        """
        # Remove the username claim from the map.
        if (user := item._user) is not None:
            self._by_username.pop(user.username, None)


#: The main service account registry for Review Board.
#:
#: Version Added:
#:     8.1
service_account_registry = ServiceAccountRegistry()
