"""Hosting service for Forgejo.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING
from urllib.parse import quote as urlquote, urljoin, urlparse

from django.template.loader import render_to_string
from django.urls import path
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.errors import HostingServiceError
from reviewboard.hostingsvcs.forgejo.client import ForgejoClient
from reviewboard.hostingsvcs.forgejo.errors import APITokenNameInUseError
from reviewboard.hostingsvcs.forgejo.forms import ForgejoForm
from reviewboard.hostingsvcs.forgejo.views import WebHookView
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.http import HttpRequest
    from django.utils.safestring import SafeString

    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.scmtools.core import Branch, Commit
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class Forgejo(BaseHostingService, BaseBugTracker):
    """Hosting service for Forgejo.

    Version Added:
        7.1
    """

    hosting_service_id = 'forgejo'
    name = _('Forgejo')

    client_class = ForgejoClient
    form = ForgejoForm

    has_repository_hook_instructions = True
    needs_authorization = True
    self_hosted = True
    supported_scmtools = ['Git']
    supports_bug_trackers = True
    supports_post_commit = True
    supports_repositories = True
    supports_two_factor_auth = True

    bug_tracker_field = \
        '%(hosting_url)s/%(repository_owner)s/%(repository_name)s/issues/%%s'
    repository_fields = {
        'Git': {
            'path': '%(hosting_url)s/%(repository_owner)s/'
                    '%(repository_name)s.git',
        },
    }

    repository_url_patterns = [
        path('hooks/close-submitted/',
             view=WebHookView.as_view(),
             name='forgejo-hooks-close-submitted'),
    ]

    # Set this for typing.
    client: ForgejoClient

    def is_authorized(self) -> bool:
        """Return whether the account has stored authorization.

        This will check to see if we have stored an API token for the account.
        It does not validate that the token still works.

        Returns:
            bool:
            ``True`` if the account has a saved API token. ``False``,
            otherwise.
        """
        return 'api_token' in self.account.data

    def authorize(
        self,
        *,
        username: str | None,
        password: str | None,
        hosting_url: str | None,
        two_factor_auth_code: (str | None) = None,
        **kwargs,
    ) -> None:
        """Authorize an account for Forgejo.

        Args:
            username (str):
                The username for the account.

            password (str):
                The password for the account.

            hosting_url (str):
                The URL of the Forgejo server.

            two_factor_auth_code (str, optional):
                The two-factor authentication code provided by the user.

            **kwargs (dict, unused):
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

            reviewboard.hostingsvcs.errors.HostingServiceError:
                A non-authentication error occurred.
        """
        assert username is not None
        assert password is not None
        assert hosting_url is not None

        attempts = 0
        max_tries = 5

        server_name = urlparse(get_server_url()).hostname
        assert server_name is not None

        while attempts < max_tries:
            token_name = self._create_api_token_name(server_name)

            try:
                api_token = self.client.create_api_token(
                    token_name=token_name,
                    hosting_url=hosting_url,
                    username=username,
                    password=password,
                    two_factor_auth_code=two_factor_auth_code)
            except APITokenNameInUseError:
                attempts += 1
                continue

            break
        else:
            logger.error('Failed to create an API token with a unique name '
                         'for user %s on server %s after %d attempts.',
                         username, hosting_url, max_tries)

            raise HostingServiceError(
                _(
                    'Unable to create a Forgejo API token with a unique name '
                    'after {tries} attempts for user {username} on server '
                    '{hosting_url}'
                ).format(
                    tries=max_tries,
                    username=username,
                    hosting_url=hosting_url,
                )
            )

        self.account.data['api_token'] = encrypt_password(api_token)
        self.account.save()

    def check_repository(
        self,
        *,
        repository_owner: str,
        repository_name: str,
        **kwargs,
    ) -> None:
        """Check the validity of a repository configuration.

        This checks that the data provided in the repository form is valid.

        Args:
            repository_owner (str):
                The repository owner.

            repository_name (str):
                The name of the repository.

            **kwargs (dict):
                Additional keyword arguments from the repository form.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository is not valid.
        """
        self.client.check_repository(
            hosting_url=self.account.hosting_url,
            repository_owner=repository_owner,
            repository_name=repository_name)

    def get_file(
        self,
        repository: Repository,
        path: str,
        revision: str,
        *args,
        **kwargs,
    ) -> bytes:
        """Return the requested file.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (str):
                The file path.

            revision (str):
                The revision the file should be retrieved from.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found or the API could not be accessed.
        """
        return self.client.get_blob(
            hosting_url=self.account.hosting_url,
            repository=repository,
            path=path,
            sha=revision)

    def get_branches(
        self,
        repository: Repository,
    ) -> Sequence[Branch]:
        """Return a list of all branches in the repositories.

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
        return self.client.get_branches(
            hosting_url=self.account.hosting_url,
            repository=repository)

    def get_commits(
        self,
        repository: Repository,
        branch: (str | None) = None,
        start: (str | None) = None,
    ) -> Sequence[Commit]:
        """Return a list of commits backward in history from a given point.

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
        return self.client.get_commits(
            hosting_url=self.account.hosting_url,
            repository=repository,
            branch=branch,
            start=start)

    def get_change(
        self,
        repository: Repository,
        revision: str,
    ) -> Commit:
        """Return an individual change.

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
        return self.client.get_change(
            hosting_url=self.account.hosting_url,
            repository=repository,
            revision=revision)

    def get_bug_info_uncached(
        self,
        repository: Repository,
        bug_id: str,
    ) -> BugInfo:
        """Return the information for the specified bug

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug to fetch.

        Returns:
            reviewboard.hostingsvcs.bugtracker.BugInfo:
            Information about the bug.
        """
        return self.client.get_bug_info(
            hosting_url=self.account.hosting_url,
            repository=repository,
            bug_id=bug_id)

    def get_repository_hook_instructions(
        self,
        request: HttpRequest,
        repository: Repository,
    ) -> SafeString:
        """Return instructions for setting up incoming WebHooks.

        Args:
            request (django.http.HttpRequest):
                The request from the client.

            repository (reviewboard.scmtools.models.Repository):
                The repository to return instructions for.

        Returns:
            django.utils.safestring.SafeString:
            The HTML to send to the client for hook instructions.
        """
        repository_owner = urlquote(repository.extra_data['repository_owner'])
        repository_name = urlquote(repository.extra_data['repository_name'])

        add_webhook_url = urljoin(
            self.account.hosting_url,
            f'{repository_owner}/{repository_name}/settings/hooks/forgejo/new')

        webhook_endpoint_url = build_server_url(local_site_reverse(
            'forgejo-hooks-close-submitted',
            local_site=repository.local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': repository.hosting_account.service_name,
            },
        ))

        example_id = 123
        example_url = build_server_url(local_site_reverse(
            'review-request-detail',
            local_site=repository.local_site,
            kwargs={
                'review_request_id': example_id,
            }))

        return render_to_string(
            template_name='hostingsvcs/forgejo/repo_hook_instructions.html',
            request=request,
            context={
                'example_id': example_id,
                'example_url': example_url,
                'repository': repository,
                'server_url': get_server_url(),
                'add_webhook_url': add_webhook_url,
                'webhook_endpoint_url': webhook_endpoint_url,
                'hook_uuid': repository.get_or_create_hooks_uuid(),
            })

    def _create_api_token_name(
        self,
        server_name: str,
    ) -> str:
        """Return a name to use for a new API token.

        Args:
            server_name (str):
                The hostname of the Review Board server.

        Returns:
            str:
            A name to use for the new API token.
        """
        id = uuid.uuid4().hex[:6]

        # API token names are limited to 255 chars. It's pretty unlikely that
        # someone's server name will be this long, but just in case:
        server_name = server_name[:236]

        return f'reviewboard-{server_name}-{id}'
