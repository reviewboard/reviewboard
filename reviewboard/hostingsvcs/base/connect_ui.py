"""UI interfaces for connecting to hosting services.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _, ngettext

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any, ClassVar

    from django.http import HttpRequest
    from django.utils.safestring import SafeString
    from typelets.django.strings import StrOrPromise
    from typing_extensions import NotRequired

    from reviewboard.hostingsvcs.base.forms import BaseHostingServiceAuthForm
    from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
    from reviewboard.hostingsvcs.models import HostingServiceAccount
    from reviewboard.scmtools.models import Repository


class AdminServicesListAccountMenuItem(TypedDict):
    """An item in an account's menu on the Connected Services page.

    Each item describes one entry in the per-account settings menu. The action
    the item performs on click is determined by which of the action fields is
    set. Exactly one of :py:attr:`dialogURL`, :py:attr:`url`, or
    :py:attr:`action` should be provided.

    Version Added:
        9.0
    """

    #: A unique identifier for the item within the menu.
    #:
    #: Type:
    #:     str
    id: str

    #: The label to show for the item.
    #:
    #: Type:
    #:     str
    label: StrOrPromise

    #: The name of a registered client-side handler to run when clicked.
    #:
    #: This is resolved against the client action registry at click time. Use
    #: this for custom behavior that a plain URL or dialog cannot express.
    #:
    #: Type:
    #:     str
    action: NotRequired[str]

    #: A connect-page URL to open in the services dialog when clicked.
    #:
    #: The dialog fetches this URL and shows the returned fragment, reusing the
    #: connect wizard's form and multi-step behavior.
    #:
    #: Type:
    #:     str
    dialogURL: NotRequired[str]

    #: The name of an optional icon to show beside the label.
    #:
    #: Type:
    #:     str
    iconName: NotRequired[str]

    #: A URL to navigate to when the item is clicked.
    #:
    #: Type:
    #:     str
    url: NotRequired[str]


class AdminServicesListAttentionItem(TypedDict):
    """A connection needing attention on the Connected Services page.

    Each item describes one account whose connection is in an error state, so
    the page can show an aggregate alert listing every failure. The item
    carries the account context and a fix action, so the alert can resolve the
    problem the same way the account's settings menu does.

    Version Added:
        9.0
    """

    #: The ID of the account, for dispatching the fix action.
    #:
    #: Type:
    #:     int
    account_id: int

    #: A label identifying the account, such as its username.
    #:
    #: Type:
    #:     str
    account_label: StrOrPromise

    #: A human-readable description of what is wrong.
    #:
    #: Type:
    #:     str
    message: StrOrPromise

    #: The ID of the hosting service, for dispatching the fix action.
    #:
    #: Type:
    #:     str
    service_id: str

    #: The name of the hosting service the account belongs to.
    #:
    #: Type:
    #:     str
    service_name: StrOrPromise

    #: The action that resolves the problem, when one is available.
    #:
    #: This is the same descriptor used for account menu items, so the client
    #: dispatches it the same way: opening a dialog, navigating to a URL, or
    #: running a registered handler.
    #:
    #: For example, a suspended GitHub install uses a ``url`` to reconnect,
    #: while a repository with bad credentials #: would use a ``dialogURL`` to
    #: open its credentials form.
    #:
    #: Type:
    #:     AdminServicesListAccountMenuItem
    action: NotRequired[AdminServicesListAccountMenuItem]


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

        accounts_data = [
            {
                'account': account,
                'menu_items':
                    self.get_connected_services_list_account_menu_items(
                        request,
                        account=account),
                'repository_count':
                    getattr(account, 'repository_count', 0),
            }
            for account in accounts
        ]

        # The accounts offered in the repository filter dropdown. This covers
        # every account contributing rows to the list, so any row can be
        # isolated. Accounts are not filtered by visibility here: the list
        # itself spans all accounts, so leaving one out would show rows that
        # no filter option could narrow down to.
        filter_accounts = [
            {
                'id': account.pk,
                'label': self.get_account_filter_label(account),
            }
            for account in accounts
            if getattr(account, 'repository_count', 0)
        ]

        return {
            'accounts_data': accounts_data,
            'filter_accounts': filter_accounts,
            'service_id': service.hosting_service_id,
            'service_name': service.name,
            'service_logo': service.logo_image,
            'service_type': service_type,
            'total_repository_count': sum(
                cast(int, entry['repository_count'])
                for entry in accounts_data
            ),
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

    def get_connected_services_list_account_menu_items(
        self,
        request: HttpRequest,
        *,
        account: HostingServiceAccount,
    ) -> Sequence[AdminServicesListAccountMenuItem]:
        """Return the menu items for an account in the admin list.

        These populate the per-account settings menu on the "Connected
        Services" page. The default is a single "Edit Credentials" item that
        opens the credentials form in a dialog. Subclasses can override this to
        add, remove, or reorder items based on the account.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account the menu is for.

        Returns:
            list of AdminServicesListAccountMenuItem:
            The menu items to show for the account.
        """
        service = self._hosting_service_cls

        return [
            {
                'id': 'edit-credentials',
                'label': _('Edit Credentials'),
                'dialogURL': reverse(
                    'connected-services-account-edit-credentials',
                    kwargs={
                        'service_id': service.hosting_service_id,
                        'account_id': account.pk,
                    }),
            },
        ]

    def get_account_filter_label(
        self,
        account: HostingServiceAccount,
    ) -> str:
        """Return the label for an account in the repository filter dropdown.

        This is shown in the account filter on the connected repositories
        list on the "Connected Services" page. By default it returns the
        account's string representation.

        Subclasses can override this to disambiguate accounts. For example, a
        service with both token-based and app-based accounts can mark which is
        which when they share a username.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to return a label for.

        Returns:
            str:
            The label to show for the account.
        """
        return str(account)

    def get_repository_display_path(
        self,
        repository: Repository,
    ) -> str:
        """Return the path to display for a repository in the admin UI.

        This is shown in the connected repositories list on the "Connected
        Services" page. By default it returns the repository's raw path.

        Subclasses can override this to show a friendlier identifier. For
        example, a service backed by GitHub can turn a clone URL into an
        ``owner/repo`` name.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to return a display path for.

        Returns:
            str:
            The path to display for the repository.
        """
        return repository.path

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

    def render_edit_credentials_ui(
        self,
        request: HttpRequest,
        account: HostingServiceAccount,
        *,
        form: (BaseHostingServiceAuthForm | None) = None,
    ) -> SafeString:
        """Render the edit-credentials UI for an existing account.

        This is the dialog shown by the account's "Edit Credentials" menu item.
        It renders the service's authentication form pre-populated from the
        account, so the credentials can be updated and re-authorized.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account whose credentials are being edited.

            form (BaseHostingServiceAuthForm, optional):
                The authentication form to render. If not provided, a new form
                bound to the account will be created.

        Returns:
            django.utils.safestring.SafeString:
            The rendered edit-credentials UI.
        """
        if form is None:
            form = self.get_auth_form_class()(
                hosting_service_cls=self._hosting_service_cls,
                hosting_account=account,
                local_site=account.local_site)

            # Populate the form's fields from the account (username, and the
            # hosting URL for self-hosted services).
            form.load()

        context = self.make_connect_ui_context(request, form=form)
        context['wizard_title'] = _('Edit Credentials')
        context['wizard_action_label'] = _('Save')

        return render_to_string(
            self.connect_ui_template,
            context,
            request=request)

    def get_connected_services_list_attention_items(
        self,
        request: HttpRequest,
        *,
        accounts: Sequence[HostingServiceAccount],
    ) -> Sequence[AdminServicesListAttentionItem]:
        """Return connections needing attention for the admin list.

        These drive the aggregate "needs attention" alert at the top of the
        "Connected Services" page. The default implementation returns nothing.
        Subclasses override this to report accounts whose connection is in an
        error state, along with an action to resolve it.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            accounts (list of
                      reviewboard.hostingsvcs.models.HostingServiceAccount):
                The connected accounts for this service.

        Returns:
            list of AdminServicesListAttentionItem:
            The connections needing attention.
        """
        return []
