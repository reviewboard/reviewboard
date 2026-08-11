"""UI interfaces for connecting to hosting services.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from django.utils.translation import gettext as _, ngettext

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any, ClassVar

    from django.http import HttpRequest
    from django.utils.safestring import SafeString

    from reviewboard.hostingsvcs.base.forms import BaseHostingServiceAuthForm
    from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
    from reviewboard.hostingsvcs.models import HostingServiceAccount


class BaseHostingServiceConnectUI:
    """Base class for the UI implementation of connecting to hosting services.

    Version Added:
        9.0
    """

    #: The template to use for rendering the services list entry.
    connected_services_list_entry_template: ClassVar[str] = \
        'admin/connected_services/_parts/list_entry_hosting_service.html'

    #: The template to use for rendering the connect UI.
    #:
    #: This is the per-service step of the "Connect a service" flow. The
    #: default template renders the service's authentication form. Services
    #: that need to offer additional or alternative connection methods can
    #: override this template or :py:meth:`render_connect_ui`.
    connect_ui_template: ClassVar[str] = \
        'admin/connected_services/_parts/connect_form.html'

    ######################
    # Instance variables #
    ######################

    #: The hosting service class.
    _hosting_service_cls: type[BaseHostingService]

    def __init__(
        self,
        hosting_service_cls: type[BaseHostingService],
    ) -> None:
        """Initialize the object.

        Args:
            hosting_service_cls (type):
                The hosting service class.
        """
        self._hosting_service_cls = hosting_service_cls

    def render_connected_services_list_entry(
        self,
        request: HttpRequest,
        *,
        accounts: Sequence[HostingServiceAccount],
    ) -> SafeString:
        """Render the services list entry for this hosting service.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            accounts (list of
                      reviewboard.hostingsvcs.models.HostingServiceAccount):
                The accounts for this hosting service.

        Returns:
            django.utils.safestring.SafeString:
            The rendered entry for the connected services list page.
        """
        return render_to_string(
            self.connected_services_list_entry_template,
            self.make_connected_services_list_entry_context(
                request,
                accounts=accounts),
            request=request)

    def make_connected_services_list_entry_context(
        self,
        request: HttpRequest,
        *,
        accounts: Sequence[HostingServiceAccount],
    ) -> dict[str, Any]:
        """Return template context for rendering the services list entry.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            accounts (list of
                      reviewboard.hostingsvcs.models.HostingServiceAccount):
                The accounts for this hosting service.

        Returns:
            dict:
            Template context to use when rendering the entry.
        """
        service = self._hosting_service_cls

        # TODO: create a central enum for these and let each hosting service
        # mark what they are?
        if service.supports_repositories:
            service_type = _('Source hosting')
        elif service.supports_bug_trackers:
            service_type = _('Issue tracking')
        else:
            service_type = None

        return {
            'service_name': service.name,
            'service_logo': service.logo_image,
            'service_type': service_type,
            'accounts_data': [
                {
                    'account': account,
                    'detail':
                        self.get_connected_services_list_account_detail(
                            account=account),
                }
                for account in accounts
            ],
        }

    def get_connected_services_list_account_detail(
        self,
        *,
        account: HostingServiceAccount,
    ) -> str | None:
        """Return a detail string describing an account in the admin list.

        This is shown beside the account in the "Connected Services" page.
        Services that support repositories show the number of repositories
        associated with the account. Other services currently show nothing.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to describe. This is expected to be annotated
                with a ``repository_count`` attribute (see
                :py:class:`reviewboard.admin.views.ConnectedServicesListView`).

        Returns:
            str:
            The detail string, or ``None`` if there is nothing to show.
        """
        if not self._hosting_service_cls.supports_repositories:
            return None

        count = getattr(account, 'repository_count', 0)

        return (
            ngettext('{count} repository',
                     '{count} repositories',
                     count)
            .format(count=count)
        )

    def get_auth_form_class(self) -> type[BaseHostingServiceAuthForm]:
        """Return the authentication form class for this service.

        This returns the service's :py:attr:`auth_form`, falling back to
        the default :py:class:`~reviewboard.hostingsvcs.base.forms.
        BaseHostingServiceAuthForm` if one is not set.

        Returns:
            type:
            The authentication form class to use for this service.
        """
        from reviewboard.hostingsvcs.base.forms import \
            BaseHostingServiceAuthForm

        return (
            self._hosting_service_cls.auth_form or
            BaseHostingServiceAuthForm
        )

    def render_connect_ui(
        self,
        request: HttpRequest,
        *,
        form: (BaseHostingServiceAuthForm | None) = None,
    ) -> SafeString:
        """Render the connect UI for this hosting service.

        This is the per-service step of the "Connect a service" flow. The
        default implementation renders the service's authentication form.
        Services can override this method (or :py:attr:`connect_ui_template`)
        to offer additional or alternative connection methods.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            form (reviewboard.hostingsvcs.base.forms.
                  BaseHostingServiceAuthForm, optional):
                The authentication form to render. If not provided, a new
                unbound form will be created.

        Returns:
            django.utils.safestring.SafeString:
            The rendered connect UI.
        """
        if form is None:
            form = self.get_auth_form_class()(
                hosting_service_cls=self._hosting_service_cls,
                local_site=request.local_site)

        return render_to_string(
            self.connect_ui_template,
            self.make_connect_ui_context(request, form=form),
            request=request)

    def make_connect_ui_context(
        self,
        request: HttpRequest,
        *,
        form: BaseHostingServiceAuthForm,
    ) -> dict[str, Any]:
        """Return template context for rendering the connect UI.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            form (reviewboard.hostingsvcs.base.forms.
                  BaseHostingServiceAuthForm):
                The authentication form to render.

        Returns:
            dict:
            Template context to use when rendering the connect UI.
        """
        return {
            'form': form,
            'hosting_service_id': self._hosting_service_cls.hosting_service_id,
        }
