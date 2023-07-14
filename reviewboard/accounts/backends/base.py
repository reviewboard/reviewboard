"""Base class for authentication backends."""

from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING, Type, Union

from django.contrib.auth.models import User
from djblets.db.query import get_object_or_none

if TYPE_CHECKING:
    from django.db.models import Q
    from django.http import HttpRequest
    from djblets.siteconfig.forms import SiteSettingsForm
    from djblets.util.typing import StrOrPromise


class BaseAuthBackend:
    """Base class for a Review Board authentication backend."""

    #: The unique ID for the authentication backend.
    #:
    #: Type:
    #:     str
    backend_id: Optional[str] = None

    #: The display name for the authentication backend.
    #:
    #: This will be shown in the list of backends in the administration UI.
    #:
    #: Type:
    #:     str
    name: Optional[StrOrPromise] = None

    #: The form class used for authentication settings.
    #:
    #: This must be a subclass of
    #: :py:class:`~djblets.siteconfig.forms.SiteSettingsForm`.
    #:
    #: Type:
    #:     type
    settings_form: Optional[Type[SiteSettingsForm]] = None

    #: Whether this backend supports registering new users.
    #:
    #: Type:
    #:     bool
    supports_registration: bool = False

    #: Whether this backend supports changing the user's full name.
    #:
    #: Type:
    #:     bool
    supports_change_name: bool = False

    #: Whether this backend supports changing the user's e-mail address.
    #:
    #: Type:
    #:     bool
    supports_change_email: bool = False

    #: Whether this backend supports changing the user's password.
    #:
    #: Type:
    #:     bool
    supports_change_password: bool = False

    #: Authentication instructions to display above the Login form.
    #:
    #: Type:
    #:     str
    login_instructions: Optional[StrOrPromise] = None

    #: A regex for matching invalid characters in usernames.
    #:
    #: Type:
    #:     re.Pattern
    INVALID_USERNAME_CHAR_REGEX: re.Pattern = re.compile(r'[^\w.@+-]')

    def authenticate(
        self,
        request: Optional[HttpRequest] = None,
        **credentials,
    ) -> Optional[User]:
        """Authenticate a user.

        This will authenticate a user identified by the provided credentials.
        object, or None.

        This must be implemented by subclasses.

        Version Changed:
            6.0:
            ``request`` is now optional.

        Version Changed:
            4.0:
            The ``request`` argument is now mandatory as the first positional
            argument, as per requirements in Django.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the caller. This may be ``None``.

            **credentials (dict):
                The credentials passed to the backend. This will often
                contain ``username`` and ``password`` keys.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user, or ``None`` if the user could not be
            authenticated for any reason.
        """
        raise NotImplementedError

    def get_or_create_user(
        self,
        username: str,
        request: Optional[HttpRequest] = None,
    ) -> Optional[User]:
        """Return an existing user or create one if it doesn't exist.

        This does not authenticate the user.

        If the user does not exist in the database, but does in the backend,
        its information will be stored in the database for later lookup.
        Subclasses can impose restrictions on this.

        This must be implemented by subclasses.

        Args:
            username (str):
                The username to fetch or create.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, or ``None`` if one could not be found.
        """
        raise NotImplementedError

    def get_user(
        self,
        user_id: Union[int, str],
    ) -> Optional[User]:
        """Return an existing user given a numeric user ID.

        Args:
            user_id (int or str):
                The ID of the user to retrieve.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, or ``None`` if one could not be found.
        """
        return get_object_or_none(User, pk=user_id)

    def update_password(
        self,
        user: User,
        password: str,
    ) -> None:
        """Update a user's password on the backend.

        Authentication backends can override this to update the password
        on the backend. By default, this is not supported.

        Callers should only call this after checking whether
        :py:attr:`supports_change_password` is ``True``.

        Args:
            user (django.contrib.auth.models.User):
                The user whose password will be changed.

            password (str):
                The new password.

        Raises:
            NotImplementedError:
                The backend does not support changing passwords.
        """
        raise NotImplementedError

    def update_name(
        self,
        user: User,
    ) -> None:
        """Update a user's full name on the backend.

        Authentication backends can override this to update the name on the
        backend based on the
        :py:attr:`~django.contrib.auth.models.User.first_name` and
        :py:attr:`~django.contrib.auth.models.User.last_name` values in
        ``user``. By default, this will do nothing.

        Callers should only call this after checking whether
        :py:attr:`supports_change_name` is ``True``.

        Args:
            user (django.contrib.auth.models.User):
                The user whose full name will be changed.
        """
        pass

    def update_email(
        self,
        user: User,
    ) -> None:
        """Update a user's e-mail address on the backend.

        Authentication backends can override this to update the e-mail
        address on the backend based on the
        :py:attr:`~django.contrib.auth.models.User.email` value in ``user``.
        NBy default, this will do nothing.

        Callers should only call this after checking whether
        :py:attr:`supports_change_email` is ``True``.

        Args:
            user (django.contrib.auth.models.User):
                The user whose full name will be changed.
        """
        pass

    def populate_users(
        self,
        query: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Populate users from the backend into the database based on a query.

        Authentication backends can override this to add users stored on the
        backend into the local database, based on a query string representing
        a full or partial first name, last name, or username. Each result
        that's found based on the query should be stored in the database by
        the backend, generally using the same creation logic as in
        :py:meth:`get_or_create_user`.

        Callers should use this when they need to look up all available users
        from a backend. After calling this, they should look up the results
        from the database.

        By default, this does nothing.

        Version Changed:
            6.0:
            ``request`` is now optional.

        Args:
            query (str):
                A search query for matching users. This will match the entirety
                or prefix of a username. It's expected that the match will be
                case-insensitive.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Extra positional arguments, for future use.

        Raises:
            reviewboard.accounts.errors.UserQueryError:
                There was an error processing the query or looking up users.
                Details will be in the error message.
        """
        pass

    def build_search_users_query(
        self,
        query: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> Optional[Q]:
        """Build a query for searching users in the database.

        This allows backends to construct specialized search queries (
        for use in :py:meth:`QuerySet.filter()
        <django.db.models.query.QuerySet.filter>` when searching for users
        via the :ref:`webapi2.0-user-list-resource`.

        By default, this will return ``None``.

        Version Changed:
            6.0:
            ``request`` is now optional.

        Args:
            query (str):
                A search query for matching users. This will match the entirety
                or prefix of a username. It's expected that the match will be
                case-insensitive.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Extra positional arguments, for future use.

        Returns:
            django.db.models.Q:
            The resulting query for the queryset, or ``None`` to use the
            query for the next available backend (eventually defaulting to
            the standard search query).
        """
        return None
