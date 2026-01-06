"""Built-in actions for the admins app.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Model, QuerySet
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from djblets.cache.backend import cache_memoize, make_cache_key

from reviewboard.actions import (ActionPlacement,
                                 AttachmentPoint,
                                 BaseAction,
                                 BaseGroupAction,
                                 actions_registry)
from reviewboard.actions.base import ActionAttachmentPoint
from reviewboard.actions.renderers import (SidebarActionGroupRenderer,
                                           SidebarItemActionRenderer)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.notifications.models import WebHookTarget
from reviewboard.oauth.models import Application
from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.scmtools.models import Repository

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any, ClassVar, Final

    from django.http.request import HttpRequest
    from django.template import Context
    from typelets.django.strings import StrOrPromise


logger = logging.getLogger(__name__)


class BaseAdminSidebarGroupAction(BaseGroupAction):
    """Base class for sidebar group actions.

    This allows for additional metadata for template hooks that render
    at the end of the items for the group.

    Version Added:
        7.1
    """

    #: A template hook point to include at the bottom of the items.
    sidebar_hook_point: ClassVar[str | None] = None


class BaseAdminSidebarManageItemAction(BaseAction):
    """Base class for sidebar item actions.

    This allows for additional metadata for optional Add Item URLs/titles
    and item counts.

    Version Added:
        7.1
    """

    #: The admin site name used for URL resolution.
    #:
    #: Extensions should set this to their extension's main module name
    #: containing the admin site.
    admin_site_name: ClassVar[str] = 'admin'

    #: URL name for an Add Item icon.
    add_item_url_name: ClassVar[str | None] = None

    #: Title text used for an Add Item icon.
    add_item_title: ClassVar[StrOrPromise | None] = None

    #: Queryset used to count items in the database.
    #:
    #: If not set, a default queryset based on :py:attr:`model` will be used.
    item_queryset: ClassVar[QuerySet | None] = None

    #: The model represented by this sidebar item.
    model: ClassVar[type[Model] | None] = None

    def get_add_item_url(self) -> str | None:
        """Return the URL to add a new item.

        If :py:attr:`add_item_url_name` is set, it will be used as a URL
        name and resolved. Otherwise, a URL will be derived from
        :py:attr:`model` using the default database.

        Extensions must override to generate a path suitable for their own
        database.

        Returns:
            str:
            The Add Item URL, or ``None`` if one is not set or can't be looked
            up.
        """
        if (url_name := self.add_item_url_name):
            return reverse(url_name)
        elif self.model is not None:
            return reverse(self._get_admin_url_name('add'))

        return None

    def get_url(
        self,
        *,
        context: Context,
    ) -> str:
        """Return the URL for the navigation item.

        If :py:attr:`url` or :py:attr:`url_name` are not explicitly set,
        a URL will be generated based on :py:attr:`model`.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The URL to use for the action.
        """
        url = super().get_url(context=context)

        if url == '#' and self.model is not None:
            url = reverse(self._get_admin_url_name('changelist'))

        return url

    def get_item_count(self) -> int | None:
        """Return the number of items to show in the sidebar.

        This will default to performing a query using
        :py:attr:`item_queryset`, returning ``None`` if not set.

        Returns:
            int:
            The number of items, or ``None`` if it can't be queried.
        """
        if (item_queryset := self.get_item_queryset()) is not None:
            return item_queryset.count()

        return None

    def get_item_queryset(self) -> QuerySet | None:
        """Return the queryset for the items.

        This will default to returning a copy of :py:attr:`item_queryset`,
        if set, or a queryset based on :py:attr:`model`.

        Returns:
            django.db.models.query.QuerySet:
            The queryset used to perform item lookups.
        """
        if (queryset := self.item_queryset) is not None:
            # Create a local copy of the queryset defined on the class.
            return queryset.all()
        elif (model := self.model) is not None:
            return model.objects.all()

        return None

    def _get_admin_url_name(
        self,
        page_name: str,
    ) -> str:
        """Return a URL name for an admin page.

        This will generate the name based on :py:attr:`admin_site_name`,
        :py:attr:`model`, and the provided page name within the admin site.

        Args:
            page_name (str):
                The name of the page to link to.

        Returns:
            str:
            The resulting admin URL name.
        """
        model = self.model
        assert model is not None

        meta = model._meta

        return (
            f'{self.admin_site_name}:{meta.app_label}_{meta.model_name}_'
            f'{page_name}'
        )


class AdminSidebarActionGroupRenderer(SidebarActionGroupRenderer):
    """Renderer for admin sidebar groups.

    This provides additional CSS for the group based on whether there are
    icons shown in group items.

    It also provides a template hook for post-group rendering, if the
    action group has a ``sidebar_hook_point`` attribute.

    Version Added:
        7.1
    """

    template_name = 'admin/actions/sidebar_group_action.html'


#
# "Administration" nav group actions.
#

class AdminMainNavGroupAction(BaseAdminSidebarGroupAction):
    """Administration navigation group action.

    Version Added:
        7.1
    """

    action_id = 'admin-main-nav-group'
    label = _('Administration')
    sidebar_hook_point = 'admin-sidebar-administration'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV),
    ]


class AdminDashboardNavAction(BaseAction):
    """Administration -> Dashboard navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-dashboard-nav'
    label = _('Dashboard')
    url_name = 'admin-dashboard'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminMainNavGroupAction.action_id),
    ]


class AdminLicensesNavAction(BaseAction):
    """Administration -> Licenses navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-licenses-nav'
    label = _('Licenses')
    url_name = 'admin-licenses'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminMainNavGroupAction.action_id),
    ]


class AdminSecurityCenterNavAction(BaseAction):
    """Administration -> Security navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-security-center-nav'
    label = _('Security Center')
    url_name = 'admin-security-checks'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminMainNavGroupAction.action_id),
    ]


class AdminExtensionsNavAction(BaseAction):
    """Administration -> Extensions navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-extensions-nav'
    label = _('Extensions')
    url_name = 'extension-list'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminMainNavGroupAction.action_id),
    ]


class AdminIntegrationsNavAction(BaseAction):
    """Administration -> Integrations navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-integrations-nav'
    label = _('Integrations')
    url_name = 'integration-list'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminMainNavGroupAction.action_id),
    ]


class AdminDatabaseNavAction(BaseAction):
    """Administration -> Database navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-database-nav'
    label = _('Database')
    url_name = 'admin:index'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminMainNavGroupAction.action_id),
    ]


#
# "Settings" nav group actions.
#

class AdminSettingsNavGroupAction(BaseAdminSidebarGroupAction):
    """Settings navigation group action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-nav-group'
    label = _('Settings')
    sidebar_hook_point = 'admin-sidebar-settings'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV),
    ]


class AdminSettingsGeneralNavAction(BaseAction):
    """Settings -> General navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-general-nav'
    label = _('General')
    url_name = 'settings-general'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsAuthenticationNavAction(BaseAction):
    """Settings -> Authentication navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-auth-nav'
    label = _('Authentication')
    url_name = 'settings-authentication'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsAvatarsNavAction(BaseAction):
    """Settings -> Avatars navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-avatars-nav'
    label = _('Avatars')
    url_name = 'settings-avatars'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsEmailNavAction(BaseAction):
    """Settings -> E-Mail navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-email-nav'
    label = _('E-Mail')
    url_name = 'settings-email'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsReviewsNavAction(BaseAction):
    """Settings -> Review Workflow navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-reviews-nav'
    label = _('Review Workflow')
    url_name = 'settings-reviews'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsDiffsNavAction(BaseAction):
    """Settings -> Diff Viewer navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-diffs-nav'
    label = _('Diff Viewer')
    url_name = 'settings-diffs'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsLoggingNavAction(BaseAction):
    """Settings -> Logging navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-logging-nav'
    label = _('Logging')
    url_name = 'settings-logging'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsSSHNavAction(BaseAction):
    """Settings -> SSH navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-ssh-nav'
    label = _('SSH')
    url_name = 'settings-ssh'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsStorageNavAction(BaseAction):
    """Settings -> File Storage navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-storage-nav'
    label = _('File Storage')
    url_name = 'settings-storage'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsPrivacyNavAction(BaseAction):
    """Settings -> User Privacy navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-privacy-nav'
    label = _('User Privacy')
    url_name = 'settings-privacy'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsSupportNavAction(BaseAction):
    """Settings -> Support navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-support-nav'
    label = _('Support')
    url_name = 'settings-support'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


class AdminSettingsSearchNavAction(BaseAction):
    """Settings -> Search navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-settings-search-nav'
    label = _('Search')
    url_name = 'settings-search'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminSettingsNavGroupAction.action_id),
    ]


#
# "Manage" nav group actions.
#

class AdminSidebarManageActionRenderer(SidebarItemActionRenderer):
    """Admin sidebar renderer for items in the Manage section.

    This renders the sidebar item with an Add Item icon and an item
    count, if found. Data is pulled from cache, and recomputed if missing
    from cache.

    Version Added:
        7.1
    """

    template_name = 'admin/actions/sidebar_item_action.html'

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict[str, Any]:
        """Return extra template context for the action.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        extra_context = super().get_extra_context(request=request,
                                                  context=context)

        action = self.action
        action_id = action.action_id

        add_item_url: (str | None) = None
        add_item_title: (str | None) = None
        item_count: (int | None) = None

        # Determine the Add Item URL to show.
        try:
            add_item_url = context['add_item_urls'][action_id]
        except KeyError:
            add_item_url = _get_manage_action_item_url(action)

        # Determine the item count.
        try:
            item_count = context['item_counts'][action_id]
        except KeyError:
            item_count = _get_manage_action_item_count(action)

        if add_item_url:
            # Determine a title.
            add_item_title = getattr(action, 'add_item_title', None)

            if (not add_item_title and
                (model := getattr(action, 'model', None)) is not None):
                # Compute a default title for the model.
                add_item_title = (
                    _('Add a new {model}')
                    .format(model=model._meta.verbose_name)
                )

        extra_context.update({
            'add_item_url': add_item_url,
            'add_item_title': add_item_title,
            'item_count': item_count,
        })

        return extra_context


class AdminSidebarManageActionGroupRenderer(AdminSidebarActionGroupRenderer):
    """Admin sidebar renderer for the Manage section.

    This is a special action group that looks up and caches both the
    Add Item URLs for each type of action and the number of items currently
    in the database.

    State is cached especially to reduce the number of database queries
    across page loads. Caches are only valid for 5 minutes, ensuring that
    manual modifications to the database won't retain old counts for long.

    Cached state is opportunistic. URLs and counts for any given item are
    fetched by the item renderer as needed if not found in the cache.

    Version Added:
        7.1
    """

    default_item_renderer_cls = AdminSidebarManageActionRenderer

    #: The cache key used to store item counts.
    _STATE_CACHE_KEY: Final[str] = 'admin-sidebar-manage-state'

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict[str, Any]:
        """Return extra template context for the action.

        This includes precomputed state for our default actions, containing
        Add Item URLs and item counts.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        extra_context = super().get_extra_context(request=request,
                                                  context=context)

        # Cache item counts to avoid repeated database queries during
        # navigation. This cache will be invalidated when tracked objects
        # are created or deleted.
        sidebar_state = cache_memoize(self._STATE_CACHE_KEY,
                                      self._get_sidebar_state)

        extra_context.update(sidebar_state)

        return extra_context

    def _get_sidebar_state(self) -> dict[str, Any]:
        """Return state for items in the sidebar.

        This iterates through all the items within the Manage section of
        the admin sidebar and computed URLs and counts for each, returning
        dictionary for the context.

        The result can be cached for future page lookups.

        Returns:
            dict:
            Context state for the cache.
        """
        # We're precomputing URLs in here, rather than computing them in the
        # template, because we need to always ensure that reverse() will be
        # searching all available URL patterns and not just the ones bound to
        # request.current_app.
        #
        # current_app gets set by AdminSite views, and if we're in an
        # extension's AdminSite view, we'll fail to resolve these URLs from
        # within the template. We don't have that problem if calling reverse()
        # ourselves.
        add_item_urls: dict[str, str] = {}
        item_counts: dict[str, int] = {}
        models: set[type[Model]] = set()

        for action in self.placement.child_actions:
            action_id = action.action_id

            if (url := _get_manage_action_item_url(action)) is not None:
                add_item_urls[action_id] = url

            if (count := _get_manage_action_item_count(action)) is not None:
                item_counts[action_id] = count

            if (model := getattr(action, 'model', None)) is not None:
                models.add(model)

        setattr(self.action, '_managed_models', models)

        return {
            'add_item_urls': add_item_urls,
            'item_counts': item_counts,
        }


class AdminManageNavGroupAction(BaseAdminSidebarGroupAction):
    """Manage navigation group action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-nav-group'
    label = _('Manage')
    sidebar_hook_point = 'admin-sidebar-manage'

    default_renderer_cls = AdminSidebarManageActionGroupRenderer

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV),
    ]


class AdminManageUsersNavAction(BaseAdminSidebarManageItemAction):
    """Manage -> Users navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-users-nav'
    label = _('Users')
    model = User

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminManageNavGroupAction.action_id),
    ]


class AdminManageReviewGroupsNavAction(BaseAdminSidebarManageItemAction):
    """Manage -> Review Groups navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-review-groups-nav'
    label = _('Review Groups')
    model = Group

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminManageNavGroupAction.action_id),
    ]


class AdminManageDefaultReviewersNavAction(BaseAdminSidebarManageItemAction):
    """Manage -> Default Reviewers navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-default-reviewers-nav'
    label = _('Default Reviewers')
    model = DefaultReviewer

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminManageNavGroupAction.action_id),
    ]


class AdminManageRepositoriesNavAction(BaseAdminSidebarManageItemAction):
    """Manage -> Repositories navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-repositories-nav'
    label = _('Repositories')
    model = Repository

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminManageNavGroupAction.action_id),
    ]


class AdminManageWebHooksNavAction(BaseAdminSidebarManageItemAction):
    """Manage -> WebHooks navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-webhooks-nav'
    label = _('WebHooks')
    model = WebHookTarget

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminManageNavGroupAction.action_id),
    ]


class AdminManageHostingAccountsNavAction(BaseAdminSidebarManageItemAction):
    """Manage -> Hosting Accounts navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-hosting-accounts-nav'
    label = _('Hosting Accounts')
    model = HostingServiceAccount

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminManageNavGroupAction.action_id),
    ]


class AdminManageOAuth2AppsNavAction(BaseAdminSidebarManageItemAction):
    """Manage -> OAuth2 Applications navigation action.

    Version Added:
        7.1
    """

    action_id = 'admin-manage-oauth-app-nav'
    label = _('OAuth2 Applications')
    model = Application

    placements = [
        ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                        parent_id=AdminManageNavGroupAction.action_id),
    ]


def get_default_admin_actions() -> Iterator[BaseAction]:
    """Return the default actions registered for the admin UI.

    This supplies default data for the actions registry. It's not meant to
    be called by any other callers.

    Version Added:
        7.1

    Yields:
        reviewboard.actions.base.BaseAction:
        Each action to register.
    """
    yield from (
        # Administration section
        AdminMainNavGroupAction(),
        AdminDashboardNavAction(),
        AdminLicensesNavAction(),
        AdminSecurityCenterNavAction(),
        AdminExtensionsNavAction(),
        AdminIntegrationsNavAction(),
        AdminDatabaseNavAction(),

        # Settings section
        AdminSettingsNavGroupAction(),
        AdminSettingsGeneralNavAction(),
        AdminSettingsAuthenticationNavAction(),
        AdminSettingsAvatarsNavAction(),
        AdminSettingsEmailNavAction(),
        AdminSettingsReviewsNavAction(),
        AdminSettingsDiffsNavAction(),
        AdminSettingsLoggingNavAction(),
        AdminSettingsSSHNavAction(),
        AdminSettingsStorageNavAction(),
        AdminSettingsPrivacyNavAction(),
        AdminSettingsSupportNavAction(),
        AdminSettingsSearchNavAction(),

        # Manage section
        AdminManageNavGroupAction(),
        AdminManageUsersNavAction(),
        AdminManageReviewGroupsNavAction(),
        AdminManageDefaultReviewersNavAction(),
        AdminManageRepositoriesNavAction(),
        AdminManageWebHooksNavAction(),
        AdminManageHostingAccountsNavAction(),
        AdminManageOAuth2AppsNavAction(),
    )


def get_default_admin_attachment_points() -> Iterator[ActionAttachmentPoint]:
    """Return the default attachment points registered for the admin UI.

    This supplies default data for the attachment points registry. It's not
    meant to be called by any other callers.

    Version Added:
        7.1

    Yields:
        reviewboard.actions.base.ActionAttachmentPoint:
        Each attachment point to register.
    """
    yield ActionAttachmentPoint(
        AttachmentPoint.ADMIN_NAV,
        default_action_renderer_cls=SidebarItemActionRenderer,
        default_action_group_renderer_cls=AdminSidebarActionGroupRenderer,
    )


def _get_manage_action_item_url(
    action: BaseAction,
) -> str | None:
    """Return the URL to add a new item for an action.

    This will only return a URL for actions subclassing
    :py:class:`BaseAdminSidebarManageItemAction`.

    Any errors will be caught and logged.

    Version Added:
        7.1

    Args:
        action (reviewboard.actions.base.BaseAction):
            The action for which to return a URL.

    Returns:
        str:
        The Add Item URL, or ``None`` if one is not set or can't be looked
        up.
    """
    if isinstance(action, BaseAdminSidebarManageItemAction):
        try:
            return action.get_add_item_url()
        except Exception as e:
            logger.exception('Unexpected error getting Add Item URL for '
                             'action "%s": %s',
                             action.action_id, e)

    return None


def _get_manage_action_item_count(
    action: BaseAction,
) -> int | None:
    """Return the number of items backed by an action.

    This will only return a count for actions subclassing
    :py:class:`BaseAdminSidebarManageItemAction`.

    Any errors will be caught and logged.

    Version Added:
        7.1

    Args:
        action (reviewboard.actions.base.BaseAction):
            The action for which to return a count.

    Returns:
        str:
        The number of items, or ``None`` if a count can't be returned.
    """
    if isinstance(action, BaseAdminSidebarManageItemAction):
        try:
            return action.get_item_count()
        except Exception as e:
            logger.exception('Unexpected error querying item count for '
                             'action "%s": %s',
                             action.action_id, e)

    return None


def _invalidate_cache_for_model(
    model: type[Model],
) -> None:
    """Invalidate caches used for the sidebar state based on a model change.

    If the model is managed by the sidebar, the cache state will be
    invalidated.

    Version Added:
        7.1

    Args:
        model (type):
            The type of model required to invalidate the cache.
    """
    action = actions_registry.get_action(AdminManageNavGroupAction.action_id)

    if (action is not None and
        model in getattr(action, '_managed_models', [])):
        # This model's represented in the sidebar. The cache can be
        # invalidated.
        cache.delete(make_cache_key(
            AdminSidebarManageActionGroupRenderer._STATE_CACHE_KEY))


@receiver(post_save)
def _on_post_save(
    *,
    sender: type[Model],
    created: bool = False,
    **kwargs,
) -> None:
    """Clear cached action state when a model is saved.

    Whenever any model is created in the database, the cached state for the
    admin sidebar will be invalidated, preventing stale counts from being
    shown.

    Version Added:
        7.1

    Args:
        sender (type):
            The type of model that was saved.

        created (bool, optional):
            Whether the model was created.

        **kwargs (tuple, unused):
            Keyword arguments passed to the signal handler.
    """
    if created:
        _invalidate_cache_for_model(sender)


@receiver(post_delete)
def _on_post_delete(
    *,
    sender: type[Model],
    **kwargs,
) -> None:
    """Clear cached action state when a model is deleted.

    Whenever any model is deleted in the database, the cached state for the
    admin sidebar will be invalidated, preventing stale counts from being
    shown.

    Version Added:
        7.1

    Args:
        sender (type):
            The type of model that was saved.

        **kwargs (tuple, unused):
            Keyword arguments passed to the signal handler.
    """
    _invalidate_cache_for_model(sender)
