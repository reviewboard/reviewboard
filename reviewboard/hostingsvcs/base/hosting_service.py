"""Base communication client support for hosting services.

Version Added:
    6.0:
    This replaces the hosting service code in the old
    :py:mod:`reviewboard.hostingsvcs.service` module.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, TYPE_CHECKING
from urllib.parse import urlparse

from django.utils.translation import gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args
from typing_extensions import TypedDict

from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.hostingsvcs.base.client import HostingServiceClient

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar

    from django.http import HttpRequest
    from django.urls import _AnyURL
    from django.utils.safestring import SafeString
    from paramiko import PKey
    from typelets.django.strings import StrOrPromise
    from typing_extensions import NotRequired, TypeAlias

    from reviewboard.hostingsvcs.base.forms import (
        BaseHostingServiceAuthForm,
        BaseHostingServiceRepositoryForm)
    from reviewboard.hostingsvcs.base.paginator import BasePaginator
    from reviewboard.hostingsvcs.models import HostingServiceAccount
    from reviewboard.hostingsvcs.repository import RemoteRepository
    from reviewboard.scmtools.core import Branch, Commit, SCMTool
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class HostingServicePlan(TypedDict):
    """Information on a hosting service plan.

    Version Added:
        6.0
    """

    #: The display name of the plan.
    #:
    #: This is required for all plans.
    #:
    #: Type:
    #:     str
    name: StrOrPromise

    #: A templated value for the bug tracker field.
    #:
    #: The value will be filled in based on the cleaned bug tracker form
    #: data. It must take templated keys in the form of ``%(key_name)s``.
    #:
    #: Type:
    #:     str
    bug_tracker_field: NotRequired[str]

    #: Optional form used to configure repository settings.
    #:
    #: If not provided, a default form will be used.
    #:
    #: This value can also be set within :py:attr:`repository_plans`.
    #:
    #: Type:
    #:     type
    form: NotRequired[type[BaseHostingServiceRepositoryForm]]

    #: Templated values to set for model repository fields.
    #:
    #: Each key corresponds to a SCMTool ID or name, and each value to a
    #: mapping of model attribute names to templates for values to populate
    #: based on cleaned repository form data. It must take templated keys
    #: in the form of ``%(key_name)s``.
    #:
    #: Type:
    #:     dict
    repository_fields: NotRequired[SCMToRepositoryFields]


#: Credentials used to authenticate with a hosting service.
#:
#: Version Added:
#:     6.0
HostingServiceCredentials: TypeAlias = Dict[str, Any]


#: Information on fields in a repository.
#:
#: These will map model or form attributes to values or templates for
#: processing when saving a repository.
#:
#: Version Added:
#:     6.0
RepositoryFields: TypeAlias = Dict[str, Any]


#: A mapping of SCMTool IDs to repository fields.
#:
#: Version Added:
#:     6.0
SCMToRepositoryFields: TypeAlias = Mapping[str, RepositoryFields]


class BaseHostingService:
    """An interface to a hosting service for repositories and bug trackers.

    Subclasses are used to more easily configure repositories and to make use
    of third party APIs to perform special operations not otherwise usable by
    generic repositories.

    A hosting service can specify forms for authentication, repository, and bug
    tracker configuration.

    It can also provide a list of repository "plans" (such as public
    repositories, private repositories, or other types available to the hosting
    service), along with configuration specific to the plan. These plans will
    be available when configuring the repository.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.service` to
          :py:mod:`reviewboard.hostingsvcs.base.hosting_service` and
          renamed from ``HostingService`` to ``BaseHostingService``.
    """

    #: The unique ID of the hosting service.
    #:
    #: This should be lowercase, and only consist of the characters a-z, 0-9,
    #: ``_``, and ``-``.
    #:
    #: Version Added:
    #:     3.0.16:
    #:     This should now be set on all custom hosting services. It will be
    #:     required in Review Board 4.0.
    #:
    #: Type:
    #:     str
    hosting_service_id: ClassVar[str | None] = None

    #: The display name for the hosting service.
    #:
    #: Type:
    #:     str
    name: ClassVar[StrOrPromise | None] = None

    #: A list of available hosting service plans.
    #:
    #: Each plan may map to different configuration forms and saved state,
    #: helping subclasses support different APIs or data models provided
    #: by the server, and better helping users supply the information needed
    #: to configure the repository.
    #:
    #: Type:
    #:     list
    plans: ClassVar[Sequence[tuple[str, HostingServicePlan]] | None] = None

    #: Whether this service supports bug trackers.
    #:
    #: This should be set to ``True`` if the service provides its own bug
    #: tracker and the subclass implements all of the following methods:
    #:
    #: * :py:meth:`get_bug_tracker_field`
    #: * :py:meth:`get_bug_tracker_requires_username`
    #:
    #: Type:
    #:     bool
    supports_bug_trackers: ClassVar[bool] = False

    #: Whether this service supports post-commit requests.
    #:
    #: This should be set to ``True`` if the subclass implements all of the
    #: following methods:
    #:
    #: * :py:meth:`get_branches`
    #: * :py:meth:`get_change`
    #: * :py:meth:`get_commits`
    #:
    #: Type:
    #:     bool
    supports_post_commit: ClassVar[bool] = False

    #: Whether this service supports source code repositories.
    #:
    #: This should be set to ``True`` if the service provides a compatible
    #: source code repository and the subclass implements all of the
    #: following methods:
    #:
    #: * :py:meth:`get_file`
    #: * :py:meth:`get_file_exists`
    #: * :py:meth:`get_repository_fields`
    #:
    #: Several other optional methods may also be defined and used if this
    #: is set.
    #:
    #: Type:
    #:     bool
    supports_repositories: ClassVar[bool] = False

    #: Whether this service supports automatic association of SSH keys.
    #:
    #: This should be set to ``True`` if the service provides any way of
    #: automatically assigning an SSH key for a user for repository access,
    #: and the subclass implements the following methods:
    #:
    #: * :py:meth:`associate_ssh_key`.
    #: * :py:meth:`is_ssh_key_associated`.
    #:
    #: Type:
    #:     bool
    supports_ssh_key_association: ClassVar[bool] = False

    #: Whether this service supports two-factor authentication.
    #:
    #: This should be set to ``True`` if the service supports two-factor
    #: authentication when communicating with the API and the service
    #: implements support in :py:meth:`authorize`.
    #:
    #: Type:
    #:     bool
    supports_two_factor_auth: ClassVar[bool] = False

    #: Whether this service supports listing remote repositories.
    #:
    #: This should be set to ``True`` if the service supports looking up
    #: repositories via the API and the subclass implements all of the
    #: following methods:
    #:
    #: * :py:meth:`get_remote_repositories`
    #: * :py:meth:`get_remote_repository`
    #:
    #: Type:
    #:     bool
    supports_list_remote_repositories: ClassVar[bool] = False

    #: Whether this service provides repository hook instructions.
    #:
    #: This should be set to ``True`` if the subclass implements instructions'
    #: on configuring useful repository hooks in the following method:
    #:
    #: * :py:meth:`get_repository_hook_instructions`
    #:
    #: Type:
    #:     bool
    has_repository_hook_instructions: ClassVar[bool] = False

    #: Whether this service should be shown as an available option.
    #:
    #: This should be set to ``False`` when a service is no longer available
    #: to use, and should be hidden from repository configuration. The
    #: implementation can then be largely stubbed out. Users will see a
    #: message in the repository configuration page.
    #:
    #: Version Added:
    #:     3.0.17
    #:
    #: Type:
    #:     bool
    visible: ClassVar[bool] = True

    #: Whether this service can be self-hosted.
    #:
    #: This should be set to ``True`` if the service can be hosted at a
    #: custom URL.
    #:
    #: Type:
    #:     bool
    self_hosted: ClassVar[bool] = False

    #: Custom URL patterns to include for the hosting service.
    #:
    #: This can be used to create URLs for hooks or other utility purposes.
    #: These will be installed under:
    #:
    #: * ``/repos/<repository_id>/<hosting_service_id>/``
    #: * ``/s/<local_site>/repos/<repository_id>/<hosting_service_id>/``
    #:
    #: Type:
    #:     list
    repository_url_patterns: ClassVar[list[_AnyURL] | None] = None

    #: The utility class used to perform client functionality.
    #:
    #: Client classes are responsible for communicating with the hosting
    #: service at an API level. Instance of this hosting service will receive
    #: a client instance.
    #:
    #: Subclasses should set this to a subclass of
    #: :py:class:`HostingServiceClient`.
    #:
    #: Type:
    #:     type
    client_class: ClassVar[type[HostingServiceClient]] = HostingServiceClient

    #: Optional form used to configure authentication settings for an account.
    #:
    #: If not provided, a default form will be used.
    #:
    #: Type:
    #:     type
    auth_form: ClassVar[type[BaseHostingServiceAuthForm] | None] = None

    #: Whether usage of this hosting service requires authorization.
    #:
    #: This value can also be set within :py:attr:`repository_plans`.
    #:
    #: Type:
    #:     bool
    needs_authorization: ClassVar[bool] = False

    #: Optional form used to configure repository settings.
    #:
    #: If not provided, a default form will be used.
    #:
    #: This value can also be set within :py:attr:`repository_plans`.
    #:
    #: Type:
    #:     type
    form: ClassVar[type[BaseHostingServiceRepositoryForm] | None] = None

    #: Templated values to set for model repository fields.
    #:
    #: Each key corresponds to a SCMTool ID or name, and each value to a
    #: mapping of model attribute names to templates for values to populate
    #: based on cleaned repository form data. It must take templated keys
    #: in the form of ``%(key_name)s``.
    #:
    #: Type:
    #:     dict
    repository_fields: ClassVar[SCMToRepositoryFields] = {}

    #: A templated value for the bug tracker field.
    #:
    #: The value will be filled in based on the cleaned bug tracker form
    #: data. It must take templated keys in the form of ``%(key_name)s``.
    #:
    #: Type:
    #:     str
    bug_tracker_field: ClassVar[str | None] = None

    #: A list of SCMTools IDs or names that are supported by this service.
    #:
    #: This should contain a list of SCMTool IDs that this service can work
    #: with. For backwards-compatibility, it may instead contain a list of
    #: SCMTool names (corresponding to database registration names).
    #:
    #: This may also be specified per-plan in the :py:attr:`plans`.
    #:
    #: Version Changed:
    #:     3.0.16:
    #:     Added support for SCMTool IDs. A future version will deprecate
    #:     using SCMTool names here.
    #:
    #: Type:
    #:     list of str
    supported_scmtools: ClassVar[Sequence[str]] = []

    #: A list of SCMTool IDs that are visible when configuring the service.
    #:
    #: This should contain a list of SCMTool IDs that this service will show
    #: when configuring a repository. It can be used to offer continued
    #: legacy support for an SCMTool without offering it when creating new
    #: repositories. If not specified, all SCMTools listed
    #: in :py:attr:`supported_scmtools` are assumed to be visible.
    #:
    #: If explicitly set, this should always be equal to or a subset of
    #: :py:attr:`supported_scmtools`.
    #:
    #: This may also be specified per-plan in the :py:attr:`plans`.
    #:
    #: Version Added:
    #:     3.0.17
    #:
    #: Type:
    #:     list of str
    visible_scmtools: ClassVar[Sequence[str] | None] = None

    ######################
    # Instance variables #
    ######################

    #: The client instance for talking to the hosting service.
    #:
    #: Type:
    #:     HostingServiceClient
    client: HostingServiceClient

    def __init__(
        self,
        account: HostingServiceAccount,
    ) -> None:
        """Initialize the hosting service.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to use with the service.
        """
        assert account
        self.account = account

        self.client = self.client_class(self)

    def is_authorized(self) -> bool:
        """Return whether or not the account is currently authorized.

        An account may no longer be authorized if the hosting service
        switches to a new API that doesn't match the current authorization
        records. This function will determine whether the account is still
        considered authorized.

        Returns:
            bool:
            Whether or not the associated account is authorized.
        """
        return False

    def get_password(self) -> str | None:
        """Return the raw password for this hosting service.

        Not all hosting services provide this, and not all would need it.
        It's primarily used when building a Subversion client, or other
        SCMTools that still need direct access to the repository itself.

        Returns:
            str:
            The password.
        """
        return None

    def is_ssh_key_associated(
        self,
        repository: Repository,
        key: PKey,
    ) -> bool:
        """Return whether or not the key is associated with the repository.

        If the given key is present amongst the hosting service's deploy keys
        for the given repository, then it is considered to be associated.

        Subclasses should implement this when the hosting service supports
        SSH key association.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the key must be associated with.

            key (paramiko.PKey):
                The key to check for association.

        Returns:
            bool:
            Whether or not the key is associated with the repository.

        Raises:
            reviewboard.hostingsvcs.errors.SSHKeyAssociationError:
                If an error occurred during communication with the hosting
                service.
        """
        raise NotImplementedError

    def associate_ssh_key(
        self,
        repository: Repository,
        key: PKey,
    ) -> None:
        """Associate an SSH key with a given repository.

        Subclasses should implement this when the hosting service supports
        SSH key association.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to associate the key with.

            key (paramiko.PKey):
                The key to add to the repository's list of deploy keys.

        Raises:
            reviewboard.hostingsvcs.errors.SSHKeyAssociationError:
                If an error occurred during key association.
        """
        raise NotImplementedError

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def authorize(
        self,
        *,
        username: str | None,
        password: str | None,
        hosting_url: (str | None) = None,
        credentials: (HostingServiceCredentials | None) = None,
        two_factor_auth_code: (str | None) = None,
        local_site_name: (str | None) = None,
        **kwargs,
    ) -> None:
        """Authorize an account for the hosting service.

        Version Changed:
            7.1:
            Made arguments keyword-only.

        Args:
            username (str):
                The username for the account.

            password (str):
                The password for the account.

            hosting_url (str, optional):
                The hosting URL for the service, if self-hosted.

            credentials (dict, optional):
                All credentials provided by the authentication form.

                This will contain the username, password, and anything else
                provided by that form.

            two_factor_auth_code (str, optional):
                The two-factor authentication code provided by the user.

            local_site_name (str, optional):
                The Local Site name, if any, that the account should be
                bound to.

            **kwargs (dict):
                Extra keyword arguments containing values from the
                repository's configuration.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.

            reviewboard.hostingsvcs.errors.TwoFactorAuthCodeRequiredError:
                A two-factor authentication code is required to authorize
                this account. The request must be retried with the same
                credentials and with the ``two_factor_auth_code`` parameter
                provided.
        """
        raise NotImplementedError

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def check_repository(
        self,
        *,
        path: str | None,
        username: str | None,
        password: str | None,
        scmtool_class: type[SCMTool],
        local_site_name: str | None,
        **kwargs,
    ) -> None:
        """Check the validity of a repository configuration.

        This performs a check against the hosting service or repository
        to ensure that the information provided by the user represents
        a valid repository.

        This is passed in the repository details, such as the path and
        raw credentials, as well as the SCMTool class being used, the
        LocalSite's name (if any), and all field data from the
        HostingServiceForm as keyword arguments.

        Version Changed:
            7.1:
            Made arguments keyword-only.

        Args:
            path (str):
                The repository URL.

            username (str):
                The username to use.

            password (str):
                The password to use.

            scmtool_class (type):
                The subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`
                that should be used.

            local_site_name (str):
                The name of the local site associated with the repository, or
                ``None``.

            **kwargs (dict):
                Additional keyword arguments, unique to each hosting service.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository is not valid.
        """
        assert path is not None
        scmtool_class.check_repository(path, username, password,
                                       local_site_name)

    def get_file(
        self,
        repository: Repository,
        path: str,
        revision: str,
        *args,
        **kwargs,
    ) -> bytes:
        """Return the requested file.

        Files can only be returned from hosting services that support
        repositories.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (str):
                The file path.

            revision (str):
                The revision the file should be retrieved from.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Additional keyword arguments to pass to the SCMTool.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            NotImplementedError:
                If this hosting service does not support repositories.
        """
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().get_file(path, revision, **kwargs)

    def get_file_exists(
        self,
        repository: Repository,
        path: str,
        revision: str,
        *args,
        **kwargs,
    ) -> bool:
        """Return whether or not the given path exists in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to check for file existence.

            path (str):
                The file path.

            revision (str):
                The revision to check for file existence.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Additional keyword arguments to be passed to the SCMTool.

        Returns:
            bool:
            Whether or not the file exists at the given revision in the
            repository.

        Raises:
            NotImplementedError:
                If this hosting service does not support repositories.
        """
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().file_exists(path, revision, **kwargs)

    def get_branches(
        self,
        repository: Repository,
    ) -> Sequence[Branch]:
        """Return a list of all branches in the repositories.

        This should be implemented by subclasses, and is expected to return a
        list of Branch objects. One (and only one) of those objects should have
        the "default" field set to True.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository for which branches should be returned.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching branches.
        """
        raise NotImplementedError

    def get_commits(
        self,
        repository: Repository,
        branch: (str | None) = None,
        start: (str | None) = None,
    ) -> Sequence[Commit]:
        """Return a list of commits backward in history from a given point.

        This should be implemented by subclasses, and is expected to return a
        list of Commit objects (usually 30, but this is flexible depending on
        the limitations of the APIs provided.

        This can be called multiple times in succession using the "parent"
        field of the last entry as the start parameter in order to paginate
        through the history of commits in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve commits from.

            branch (str, optional):
                The branch to retrieve from.

                If this is not provided, the default branch will be used.

            start (str, optional):
                An optional starting revision.

                If this is not provided, the most recent commits will be
                returned.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching commits.
        """
        raise NotImplementedError

    def get_change(
        self,
        repository: Repository,
        revision: str,
    ) -> Commit:
        """Return an individual change.

        This method should be implemented by subclasses.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to get the change from.

            revision (str):
                The revision to retrieve.

        Returns:
            reviewboard.scmtools.core.Commit:
            The change.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the commit.
        """
        raise NotImplementedError

    def get_remote_repositories(
        self,
        owner: (str | None) = None,
        owner_type: (str | None) = None,
        filter_type: (str | None) = None,
        start: (int | None) = None,
        per_page: (int | None) = None,
        **kwargs,
    ) -> BasePaginator[RemoteRepository, Any]:
        """Return a list of remote repositories for the owner.

        This method should be implemented by subclasses.

        Args:
            owner (str, optional):
                The owner of the repositories.

                This is usually a username.

            owner_type (str, optional):
                A hosting service-specific indicator of what the owner is (such
                as a user or a group).

            filter_type (str, optional):
                Some hosting service-specific criteria to filter by.

            start (int, optional):
                The index to start at.

            per_page (int, optional):
                The number of results per page.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            reviewboard.hostingsvcs.utils.BasePaginator:
            A paginator for the returned repositories.
        """
        raise NotImplementedError

    def get_remote_repository(
        self,
        repository_id: str,
    ) -> RemoteRepository:
        """Return the remote repository for the ID.

        This method should be implemented by subclasses.

        Args:
            repository_id (str):
                The repository's identifier.

                This is unique to each hosting service.

        Returns:
            reviewboard.hostingsvcs.repository.RemoteRepository:
            The remote repository.

        Raises:
            django.core.excptions.ObjectDoesNotExist:
                If the remote repository does not exist.
        """
        raise NotImplementedError

    def normalize_patch(
        self,
        repository: Repository,
        patch: bytes,
        filename: str,
        revision: str,
    ) -> bytes:
        """Normalize a diff/patch file before it's applied.

        This can be used to take an uploaded diff file and modify it so that
        it can be properly applied. This may, for instance, uncollapse
        keywords or remove metadata that would confuse :command:`patch`.

        By default, this passes along the normalization to the repository's
        :py:class:`~reviewboard.scmtools.core.SCMTool`.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the patch is meant to apply to.

            patch (bytes):
                The diff/patch file to normalize.

            filename (str):
                The name of the file being changed in the diff.

            revision (str):
                The revision of the file being changed in the diff.

        Returns:
            bytes:
            The resulting diff/patch file.
        """
        return repository.get_scmtool().normalize_patch(patch=patch,
                                                        filename=filename,
                                                        revision=revision)

    @classmethod
    def get_repository_fields(
        cls,
        username: str,
        hosting_url: str | None,
        plan: str | None,
        tool_name: str,
        field_vars: dict[str, str],
    ) -> RepositoryFields:
        """Return the repository fields based on the given plan and tool.

        If the ``plan`` argument is specified, that will be used to fill in
        some tool-specific field values. Otherwise they will be retrieved from
        the :py:class:`HostingService`'s defaults.

        Args:
            username (str):
                The username.

            hosting_url (str):
                The URL of the repository.

            plan (str):
                The name of the plan.

            tool_name (str):
                The :py:attr:`~reviewboard.scmtools.core.SCMTool.name` of the
                :py:class:`~reviewboard.scmtools.core.SCMTool`.

            field_vars (dict):
                The field values from the hosting service form.

        Returns:
            dict:
            The filled in repository fields.

        Raises:
            KeyError:
               The provided plan is not valid for the hosting service.
        """
        if not cls.supports_repositories:
            raise NotImplementedError

        # Grab the list of fields for population below. We have to do this
        # differently depending on whether or not this hosting service has
        # different repository plans.
        fields: RepositoryFields = cls.get_field(plan, 'repository_fields')

        new_vars = field_vars.copy()
        new_vars['hosting_account_username'] = username

        if cls.self_hosted:
            assert hosting_url is not None

            new_vars['hosting_url'] = hosting_url
            new_vars['hosting_domain'] = urlparse(hosting_url)[1]

        results: RepositoryFields = {}

        assert tool_name in fields

        for field, value in fields[tool_name].items():
            try:
                results[field] = value % new_vars
            except KeyError as e:
                logger.exception('Failed to generate %s field for hosting '
                                 'service %s using %s and %r: Missing key %s',
                                 field, cls.name, value, new_vars, e)
                raise KeyError(
                    _('Internal error when generating %(field)s field '
                      '(Missing key "%(key)s"). Please report this.') % {
                        'field': field,
                        'key': e,
                    })

        return results

    def get_repository_hook_instructions(
        self,
        request: HttpRequest,
        repository: Repository,
    ) -> SafeString:
        """Return instructions for setting up incoming webhooks.

        Subclasses can override this (and set
        `has_repository_hook_instructions = True` on the subclass) to provide
        instructions that administrators can see when trying to configure an
        incoming webhook for the hosting service.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            repository (reviewboard.scmtools.models.Repository):
                The repository for webhook setup instructions.

        Returns:
            django.utils.text.SafeString:
            Rendered and escaped HTML for displaying to the user.
        """
        raise NotImplementedError

    @classmethod
    def get_bug_tracker_requires_username(
        cls,
        plan: (str | None) = None,
    ) -> bool:
        """Return whether or not the bug tracker requires usernames.

        Args:
            plan (str, optional):
                The name of the plan associated with the account.

        Returns:
            bool:
            ``True`` if a username is required. ``False`` if it is not.

        Raises:
            NotImplementedError:
                If the hosting service does not support bug tracking.
        """
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        return (
            plan is not None and
            ('%(hosting_account_username)s' in
             cls.get_field(plan, 'bug_tracker_field', ''))
        )

    @classmethod
    def get_bug_tracker_field(
        cls,
        plan: str | None,
        field_vars: dict[str, str],
    ) -> str:
        """Return the bug tracker field for the given plan.

        Args:
            plan (str):
                The name of the plan associated with the account.

            field_vars (dict):
                The field values from the hosting service form.

        Returns:
            str:
            The value of the bug tracker field.

        Raises:
            KeyError:
               The provided plan is not valid for the hosting service.
        """
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        bug_tracker_field = cls.get_field(plan, 'bug_tracker_field')

        if not bug_tracker_field:
            return ''

        try:
            return bug_tracker_field % field_vars
        except KeyError as e:
            logger.exception('Failed to generate %s field for hosting '
                             'service %s using %r: Missing key %s',
                             bug_tracker_field, cls.name, field_vars, e)
            raise KeyError(
                _('Internal error when generating %(field)s field '
                  '(Missing key "%(key)s"). Please report this.') % {
                    'field': bug_tracker_field,
                    'key': e,
                })

    @classmethod
    def get_field(
        cls,
        plan: str | None,
        name: str,
        default: (str | None) = None,
    ) -> Any:
        """Return the value of the field for the given plan.

        If ``plan`` is not ``None``, the field will be looked up in the plan
        configuration for the service. Otherwise the hosting service's default
        value will be used.

        Args:
            plan (str):
                The plan name.

            name (str):
                The field name.

            default (str, optional):
                A default value if the field is not present.

        Returns:
            str:
            The field value.
        """
        if cls.plans:
            assert plan

            for plan_name, info in cls.plans:
                if plan_name == plan and name in info:
                    return info[name]

        return getattr(cls, name, default)
