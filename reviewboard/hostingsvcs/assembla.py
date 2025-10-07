"""Hosting service for Assembla."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.admin.server import get_hostname
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)

if TYPE_CHECKING:
    from reviewboard.scmtools.core import SCMTool


class AssemblaForm(BaseHostingServiceRepositoryForm):
    assembla_project_id = forms.CharField(
        label=_('Project ID'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_(
            "The project ID, as shown in the URL "
            "(https://www.assembla.com/spaces/<b>&lt;project_id&gt;</b>), or "
            "your Perforce repository's Depot Host."))

    def save(self, repository):
        """Save the Assembla repository form.

        This will force the Perforce host and ticket authentication settings
        to values required for Assembla.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository being saved.
        """
        super(AssemblaForm, self).save(repository)

        if repository.get_scmtool().name == 'Perforce':
            project_id = self.cleaned_data['assembla_project_id']
            client_name = Assembla.make_p4_client_name(project_id)

            repository.extra_data.update({
                'use_ticket_auth': True,
                'p4_host': project_id,
                'p4_client': client_name,
            })


class Assembla(BaseHostingService):
    """Hosting service support for Assembla.com.

    Assembla is a hosting service that offers, amongst other features,
    Perforce, Subversion, and Git repository support.

    They do not have much of an API that we can take advantage of, so it's
    impossible for us to support Git. However, Perforce and Subversion work.
    """

    name = 'Assembla'
    hosting_service_id = 'assembla'

    needs_authorization = True
    supports_bug_trackers = True
    supports_repositories = True
    supported_scmtools = ['Perforce', 'Subversion']

    form = AssemblaForm

    repository_fields = {
        'Perforce': {
            'path': 'perforce.assembla.com:1666',
        },
        'Subversion': {
            'path': 'https://subversion.assembla.com/svn/'
                    '%(assembla_project_id)s/',
        },
    }

    bug_tracker_field = (
        'https://www.assembla.com/spaces/%(assembla_project_id)s/'
        'tickets/%%s'
    )

    @classmethod
    def make_p4_client_name(cls, project_id):
        """Return a new P4CLIENT value from the hostname and project ID.

        The client name will consist of the Review Board server's hostname
        and a sanitized version of the project ID.

        Args:
            project_id (unicode):
                The project ID provided by Assembla. This is equivalent to the
                P4HOST value for Perforce.

        Returns:
            unicode:
            A new Perforce client name.
        """
        return '%s-%s' % (get_hostname(), project_id.replace('/', '-'))

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def check_repository(
        self,
        *,
        path: str | None,
        username: str | None,
        password: str | None,
        scmtool_class: type[SCMTool],
        local_site_name: str | None,
        assembla_project_id: str,
        **kwargs,
    ) -> None:
        """Check the validity of a repository hosted on Assembla.

        Perforce repositories are handled specially. The Assembla project ID
        will be used as the Perforce host, which is needed to tell Assembla
        which repository on the server to use.

        Version Changed:
            7.1:
            Made arguments keyword-only.

        Args:
            path (str):
                The repository path.

            username (str):
                The username used for authenticating.

            password (str):
                The password used for authenticating.

            scmtool_class (type):
                The SCMTool for the repository.

            local_site_name (str):
                The name of the Local Site, if any.

            assembla_project_id (str):
                The project ID for the Assembla team.

            **kwargs (dict):
                Additional keyword arguments passed by the repository form.

        Raises:
            ValueError:
                The value of a field was incorrect.
        """
        # We want to use the configured username and other information from
        # the account.
        username = self.account.username
        password = self.get_password()

        if path is None:
            raise ValueError('path cannot be None')

        if scmtool_class.name == 'Perforce':
            scmtool_class.check_repository(
                path=path,
                username=username,
                password=password,
                local_site_name=local_site_name,
                p4_host=assembla_project_id,
                p4_client=self.make_p4_client_name(assembla_project_id))
        else:
            super().check_repository(
                path=path,
                username=username,
                password=password,
                local_site_name=local_site_name,
                scmtool_class=scmtool_class,
                **kwargs)

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def authorize(
        self,
        *,
        username: str | None,
        password: str | None,
        **kwargs,
    ) -> None:
        """Authorize the Assembla account.

        For Assembla, we simply use the native SCMTool support, as there's
        no useful API available. We just store the password encrypted, which
        will be used by the SCMTool.

        Version Changed:
            7.1:
            Made arguments keyword-only.

        Args:
            username (str):
                The username for authentication.

            password (str):
                The password for authentication.

            **kwargs (dict, unused):
                Additional keyword arguments.
        """
        self.account.data['password'] = encrypt_password(password)
        self.account.save()

    def is_authorized(self):
        """Return if the account has a password set.

        Returns:
            bool:
            ``True`` if a password is set, or ``False`` if one has not yet
            been set.
        """
        return self.account.data.get('password') is not None

    def get_password(self):
        """Return the password for this account.

        This is needed for Perforce and Subversion.

        Returns:
            unicode:
            The stored password for the account.
        """
        return decrypt_password(self.account.data['password'])

    @classmethod
    def get_repository_fields(cls, tool_name=None, *args, **kwargs):
        """Return values for the fields in the repository form.

        This forces the encoding value to "utf8" on Perforce, which is needed
        by Assembla.

        Args:
            tool_name (unicode):
                The name of the SCMTool for the repository.

            *args (tuple):
                Additional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The resulting repository field values.
        """
        data = super(Assembla, cls).get_repository_fields(tool_name=tool_name,
                                                          *args, **kwargs)

        if tool_name == 'Perforce':
            data['encoding'] = 'utf8'

        return data
