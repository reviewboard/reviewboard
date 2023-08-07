"""Base communication client support for hosting services.

Version Added:
    6.0:
    This replaces the hosting service code in the old
    :py:mod:`reviewboard.hostingsvcs.service` module.
"""

import logging
from urllib.parse import urlparse

from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.base.client import HostingServiceClient


logger = logging.getLogger(__name__)


class BaseHostingService(object):
    """An interface to a hosting service for repositories and bug trackers.

    HostingService subclasses are used to more easily configure repositories
    and to make use of third party APIs to perform special operations not
    otherwise usable by generic repositories.

    A HostingService can specify forms for repository and bug tracker
    configuration.

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
    hosting_service_id = None

    name = None
    plans = None
    supports_bug_trackers = False
    supports_post_commit = False
    supports_repositories = False
    supports_ssh_key_association = False
    supports_two_factor_auth = False
    supports_list_remote_repositories = False
    has_repository_hook_instructions = False

    #: Whether this service should be shown as an available option.
    #:
    #: This should be set to ``False`` when a service is no longer available
    #: to use, and should be hidden from repository configuration. The
    #: implementation can then be largely stubbed out. Users will see a
    #: message in the repository configuration page.
    #:
    #: Version Added:
    #:     3.0.17
    visible = True

    self_hosted = False
    repository_url_patterns = None

    client_class = HostingServiceClient

    #: Optional form used to configure authentication settings for an account.
    auth_form = None

    # These values are defaults that can be overridden in repository_plans
    # above.
    needs_authorization = False
    form = None
    fields = []
    repository_fields = {}
    bug_tracker_field = None

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
    supported_scmtools = []

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
    visible_scmtools = None

    def __init__(self, account):
        """Initialize the hosting service.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to use with the service.
        """
        assert account
        self.account = account

        self.client = self.client_class(self)

    def is_authorized(self):
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

    def get_password(self):
        """Return the raw password for this hosting service.

        Not all hosting services provide this, and not all would need it.
        It's primarily used when building a Subversion client, or other
        SCMTools that still need direct access to the repository itself.

        Returns:
            unicode:
            The password.
        """
        return None

    def is_ssh_key_associated(self, repository, key):
        """Return whether or not the key is associated with the repository.

        If the given key is present amongst the hosting service's deploy keys
        for the given repository, then it is considered to be associated.

        Sub-classes should implement this when the hosting service supports
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

    def associate_ssh_key(self, repository, key):
        """Associate an SSH key with a given repository.

        Sub-classes should implement this when the hosting service supports
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

    def authorize(self, username, password, hosting_url, credentials,
                  two_factor_auth_code=None, local_site_name=None,
                  *args, **kwargs):
        """Authorize an account for the hosting service.

        Args:
            username (unicode):
                The username for the account.

            password (unicode):
                The password for the account.

            hosting_url (unicode):
                The hosting URL for the service, if self-hosted.

            credentials (dict):
                All credentials provided by the authentication form. This
                will contain the username, password, and anything else
                provided by that form.

            two_factor_auth_code (unicode, optional):
                The two-factor authentication code provided by the user.

            local_site_name (unicode, optional):
                The Local Site name, if any, that the account should be
                bound to.

            *args (tuple):
                Extra unused positional arguments.

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

    def check_repository(self, path, username, password, scmtool_class,
                         local_site_name, *args, **kwargs):
        """Checks the validity of a repository configuration.

        This performs a check against the hosting service or repository
        to ensure that the information provided by the user represents
        a valid repository.

        This is passed in the repository details, such as the path and
        raw credentials, as well as the SCMTool class being used, the
        LocalSite's name (if any), and all field data from the
        HostingServiceForm as keyword arguments.

        Args:
            path (unicode):
                The repository URL.

            username (unicode):
                The username to use.

            password (unicode):
                The password to use.

            scmtool_class (type):
                The subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`
                that should be used.

            local_site_name (unicode):
                The name of the local site associated with the repository, or
                ``None``.

            *args (tuple):
                Additional positional arguments, unique to each hosting
                service.

            **kwargs (dict):
                Additional keyword arguments, unique to each hosting service.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository is not valid.
        """
        scmtool_class.check_repository(path, username, password,
                                       local_site_name)

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Return the requested file.

        Files can only be returned from hosting services that support
        repositories.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (unicode):
                The file path.

            revision (unicode):
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

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        """Return whether or not the given path exists in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to check for file existence.

            path (unicode):
                The file path.

            revision (unicode):
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

    def get_branches(self, repository):
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

    def get_commits(self, repository, branch=None, start=None):
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

            branch (unicode, optional):
                The branch to retrieve from. If this is not provided, the
                default branch will be used.

            start (unicode, optional):
                An optional starting revision. If this is not provided, the
                most recent commits will be returned.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching commits.
        """
        raise NotImplementedError

    def get_change(self, repository, revision):
        """Return an individual change.

        This method should be implemented by subclasses.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to get the change from.

            revision (unicode):
                The revision to retrieve.

        Returns:
            reviewboard.scmtools.core.Commit:
            The change.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the commit.
        """
        raise NotImplementedError

    def get_remote_repositories(self, owner=None, owner_type=None,
                                filter_type=None, start=None, per_page=None,
                                **kwargs):
        """Return a list of remote repositories for the owner.

        This method should be implemented by subclasses.

        Args:
            owner (unicode, optional):
                The owner of the repositories. This is usually a username.

            owner_type (unicode, optional):
                A hosting service-specific indicator of what the owner is (such
                as a user or a group).

            filter_type (unicode, optional):
                Some hosting service-specific criteria to filter by.

            start (int, optional):
                The index to start at.

            per_page (int, optional):
                The number of results per page.

        Returns:
            reviewboard.hostingsvcs.utils.APIPaginator:
            A paginator for the returned repositories.
        """
        raise NotImplementedError

    def get_remote_repository(self, repository_id):
        """Return the remote repository for the ID.

        This method should be implemented by subclasses.

        Args:
            repository_id (unicode):
                The repository's identifier. This is unique to each hosting
                service.

        Returns:
            reviewboard.hostingsvcs.repository.RemoteRepository:
            The remote repository.

        Raises:
            django.core.excptions.ObjectDoesNotExist:
                If the remote repository does not exist.
        """
        raise NotImplementedError

    def normalize_patch(self, repository, patch, filename, revision):
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

            filename (unicode):
                The name of the file being changed in the diff.

            revision (unicode):
                The revision of the file being changed in the diff.

        Returns:
            bytes:
            The resulting diff/patch file.
        """
        return repository.get_scmtool().normalize_patch(patch=patch,
                                                        filename=filename,
                                                        revision=revision)

    @classmethod
    def get_repository_fields(cls, username, hosting_url, plan, tool_name,
                              field_vars):
        """Return the repository fields based on the given plan and tool.

        If the ``plan`` argument is specified, that will be used to fill in
        some tool-specific field values. Otherwise they will be retrieved from
        the :py:class:`HostingService`'s defaults.

        Args:
            username (unicode):
                The username.

            hosting_url (unicode):
                The URL of the repository.

            plan (unicode):
                The name of the plan.

            tool_name (unicode):
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
        fields = cls.get_field(plan, 'repository_fields')

        new_vars = field_vars.copy()
        new_vars['hosting_account_username'] = username

        if cls.self_hosted:
            new_vars['hosting_url'] = hosting_url
            new_vars['hosting_domain'] = urlparse(hosting_url)[1]

        results = {}

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

    def get_repository_hook_instructions(self, request, repository):
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
            django.utils.text.SafeText:
            Rendered and escaped HTML for displaying to the user.
        """
        raise NotImplementedError

    @classmethod
    def get_bug_tracker_requires_username(cls, plan=None):
        """Return whether or not the bug tracker requires usernames.

        Args:
            plan (unicode, optional):
                The name of the plan associated with the account.

        Raises:
            NotImplementedError:
                If the hosting service does not support bug tracking.
        """
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        return ('%(hosting_account_username)s' in
                cls.get_field(plan, 'bug_tracker_field', ''))

    @classmethod
    def get_bug_tracker_field(cls, plan, field_vars):
        """Return the bug tracker field for the given plan.

        Args:
            plan (unicode):
                The name of the plan associated with the account.

            field_vars (dict):
                The field values from the hosting service form.

        Returns:
            unicode:
            The value of the bug tracker field.

        Raises
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
    def get_field(cls, plan, name, default=None):
        """Return the value of the field for the given plan.

        If ``plan`` is not ``None``, the field will be looked up in the plan
        configuration for the service. Otherwise the hosting service's default
        value will be used.

        Args:
            plan (unicode):
                The plan name.

            name (unicode):
                The field name.

            default (unicode, optional):
                A default value if the field is not present.

        Returns:
            unicode:
            The field value.
        """
        if cls.plans:
            assert plan

            for plan_name, info in cls.plans:
                if plan_name == plan and name in info:
                    return info[name]

        return getattr(cls, name, default)
