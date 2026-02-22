"""Errors for hosting service operations."""

from __future__ import annotations

from typing import Dict, Optional

from django.utils.translation import gettext, gettext_lazy as _


class HostingServiceError(Exception):
    """Base class for errors related to a hosting service."""

    ######################
    # Instance variables #
    ######################

    #: The optional HTTP status code for the error.
    http_code: Optional[int]

    #: An optional URL for further information on the error.
    help_link: Optional[str]

    #: A label for the optional URL for further information on the error.
    #:
    #: This will always be provided if :py:attr:`help_link` is set.
    help_link_text: Optional[str]

    def __init__(
        self,
        message: str,
        http_code: Optional[int] = None,
        help_link: Optional[str] = None,
        help_link_text: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The error message.

            http_code (int, optional):
                An optional HTTP status code for the error.

            help_link (str, optional):
                An optional URL for further information on the error.

            help_link_text (str, optional):
                A label for the optional URL for further information on the
                error.

                This must be provided if ``help_link`` is set.

        Raises:
            ValueError:
                ``help_link`` was provided but ``help_link_text`` was not.
        """
        super().__init__(message)

        self.http_code = http_code
        self.help_link = help_link
        self.help_link_text = help_link_text

        if help_link and not help_link_text:
            raise ValueError('help_link_text cannot be empty')


class HostingServiceAPIError(HostingServiceError):
    """An API error from a hosting service.

    This represents an error from the hosting service's API. It contains
    the error message, HTTP code, and the parsed response payload.

    HostingServiceAPIError instances can be further turned into other error
    types, or raised directly, if the error message is suitable for display.
    """

    ######################
    # Instance variables #
    ######################

    #: The HTTP status code for the error, if available.
    http_code: Optional[int]

    #: The parsed payload for the error, if available.
    rsp: Optional[Dict]

    def __init__(
        self,
        msg: Optional[str] = None,
        http_code: Optional[int] = None,
        rsp: Optional[Dict] = None,
    ) -> None:
        """Initialize the error.

        Args:
            msg (unicode, optional):
                The error message from the service.

            http_code (int, optional):
                The HTTP code for the error.

            rsp (object, optional):
                The parsed payload for the error.
        """
        super().__init__(msg or '')

        self.http_code = http_code
        self.rsp = rsp


class RepositoryError(HostingServiceError):
    """An error validating, configuring or using a repository."""


class AuthorizationError(HostingServiceError):
    """An error authorizing an account with a hosting service."""


class MissingHostingServiceError(HostingServiceError):
    """Indicates that the hosting service could not be loaded."""

    ######################
    # Instance variables #
    ######################

    #: The ID of the hosting service associated with this error.
    #:
    #: Type:
    #:     str
    hosting_service_id: str

    def __init__(
        self,
        hosting_service_id: str,
        repository: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Args:
            hosting_service_id (str):
                The ID of the hosting service that cannot be loaded.

            repository (str, optional):
                The name of the repository that is loading the hosting service.
        """
        if repository is not None:
            message = _(
                'The repository "%(repository)s" cannot load the hosting '
                'service "%(hosting_service)s". An administrator should '
                'ensure all necessary packages and extensions are installed.'
            ) % {
                'repository': repository,
                'hosting_service': hosting_service_id,
            }
        else:
            message = _(
                'The hosting service "%s" could not be loaded. An '
                'administrator should ensure all necessary packages and '
                'extensions are installed.'
            ) % hosting_service_id

        super().__init__(message)

        self.hosting_service_id = hosting_service_id


class TwoFactorAuthCodeRequiredError(AuthorizationError):
    """Response from a service indicating a two-factor auth code is required.

    Some services will indicate, after an authorization attempt, that a
    two-factor authorization code must be provided to complete authorization.
    Services can raise this error, along with a helpful message, to
    inform the user and the repository form of this.
    """


class InvalidPlanError(HostingServiceError):
    """Indicates an invalid plan name was used."""

    def __init__(
        self,
        plan: str,
    ) -> None:
        """Initialize the error.

        Args:
            plan (str):
                The ID of the plan.
        """
        super().__init__(
            gettext('%s is not a valid plan for this hosting service')
            % plan)


class SSHKeyAssociationError(HostingServiceError):
    """An error associating an SSH key with an account on a hosting service."""
