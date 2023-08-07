"""Representations of remote repositories.

Version Added:
    6.0
    This replaces the old :py:mod:`reviewboard.hostingsvcs.repository` module.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from djblets.util.typing import JSONDict
    from reviewboard.hostingsvcs.base import BaseHostingService
    from reviewboard.hostingsvcs.models import HostingServiceAccount


class RemoteRepository:
    """A representation of a remote repository.

    This is used to represent the configuration for a repository that already
    exists on the hosting service. It does not necessarily match a repository
    configured on Review Board, but can be used to create one.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.repository` to
          :py:mod:`reviewboard.hostingsvcs.base.repository`.
    """

    ######################
    # Instance variables #
    ######################

    #: Extra data about the repository.
    #:
    #: Type:
    #:     dict
    extra_data: JSONDict

    #: The hosting service that owns the repository.
    #:
    #: Type:
    #:     reviewboard.hostingsvcs.base.hosting_service.BaseHostingService
    hosting_service: BaseHostingService

    #: The account used for the hosting service.
    #:
    #: Type:
    #:     reviewboard.hostingsvcs.models.HostingServiceAccount
    hosting_service_account: HostingServiceAccount

    #: The service-specific ID of the repository.
    #:
    #: Type:
    #:     str
    id: str

    #: The mirror (alternate) path of the repository.
    #:
    #: Type:
    #:     str
    mirror_path: Optional[str]

    #: The displayed name of the repository.
    #:
    #: Type:
    #:     str
    name: str

    #: The identifier of the owner of the repository.
    #:
    #: Type:
    #:     str
    owner: str

    #: The repository path.
    #:
    #: Type:
    #:     str
    path: str

    #: The service-specific identifier for the type of repository.
    #:
    #: Type:
    #:     str
    scm_type: str

    def __init__(
        self,
        hosting_service: BaseHostingService,
        repository_id: str,
        name: str,
        owner: str,
        scm_type: str,
        path: str,
        mirror_path: Optional[str] = None,
        extra_data: JSONDict = {},
    ) -> None:
        """Initialize the remote repository representation.

        Args:
            hosting_service (reviewboard.hostingsvcs.base.hosting_service.
                             BaseHostingService):
                The hosting service that owns the repository.

            repository_id (str):
                The service-specific identifier for the type of repository.

            name (str):
                The displayed name of the repository.

            owner (str):
                The identifier of the owner of the repository.

            scm_type (str):
                The service-specific identifier for the type of repository.

            path (str):
                The repository path.

            mirror_path (str, optional):
                The mirror (alternate) path of the repository.

            extra_data (dict, optional):
                Extra data about the repository.
        """
        self.hosting_service = hosting_service
        self.hosting_service_account = hosting_service.account
        self.id = repository_id
        self.name = name
        self.owner = owner
        self.scm_type = scm_type
        self.path = path
        self.mirror_path = mirror_path
        self.extra_data = extra_data

    def __repr__(self) -> str:
        """Return a representation of the remote repository information.

        Returns:
            str:
            The string representation.
        """
        return ('<RemoteRepository: "%s" (owner=%s, scm_type=%s)>'
                % (self.name, self.owner, self.scm_type))
