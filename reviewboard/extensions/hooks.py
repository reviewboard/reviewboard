from __future__ import unicode_literals

import logging
import warnings

from django.utils import six
from django.utils.translation import ugettext as _
from djblets.extensions.hooks import (AppliesToURLMixin,
                                      BaseRegistryHook,
                                      BaseRegistryMultiItemHook,
                                      DataGridColumnsHook,
                                      ExtensionHook,
                                      ExtensionHookPoint,
                                      SignalHook,
                                      TemplateHook,
                                      URLHook)
from djblets.integrations.hooks import BaseIntegrationHook
from djblets.privacy.consent.hooks import ConsentRequirementHook
from djblets.registries.errors import ItemLookupError
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.accounts.backends import auth_backends
from reviewboard.accounts.pages import AccountPage
from reviewboard.admin.widgets import admin_widgets_registry, Widget
from reviewboard.attachments.mimetypes import (register_mimetype_handler,
                                               unregister_mimetype_handler)
from reviewboard.avatars import avatar_services
from reviewboard.datagrids.grids import (DashboardDataGrid,
                                         UserPageReviewRequestDataGrid)
from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.hostingsvcs.service import (register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.integrations.base import GetIntegrationManagerMixin
from reviewboard.notifications.email import (register_email_hook,
                                             unregister_email_hook)
from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction)
from reviewboard.reviews.features import class_based_actions_feature
from reviewboard.reviews.fields import (get_review_request_fieldset,
                                        register_review_request_fieldset,
                                        unregister_review_request_fieldset)
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.reviews.ui.base import register_ui, unregister_ui
from reviewboard.urls import (diffviewer_url_names,
                              main_review_request_url_name)
from reviewboard.webapi.server_info import (register_webapi_capabilities,
                                            unregister_webapi_capabilities)


logger = logging.getLogger(__name__)


@six.add_metaclass(ExtensionHookPoint)
class AuthBackendHook(BaseRegistryHook):
    """A hook for registering an authentication backend.

    Authentication backends control user authentication, registration, user
    lookup, and user data manipulation.

    This hook takes the class of an authentication backend that should
    be made available to the server.
    """

    registry = auth_backends

    def initialize(self, backend_cls):
        """Initialize the hook.

        This will register the provided authentication backend.

        Args:
            backend_cls (type):
                The authentication backend to register. This should be a
                subclass of
                :py:class:`~reviewboard.accounts.backends.AuthBackend`.
        """
        super(AuthBackendHook, self).initialize(backend_cls)


@six.add_metaclass(ExtensionHookPoint)
class AvatarServiceHook(BaseRegistryHook):
    """"A hook for adding avatar services.

    This hook will register services with the avatar services registry and
    unregister them when the hook is shut down.
    """

    registry = avatar_services

    def initialize(self, service):
        """Initialize the avatar service hook with the given service.

        Args:
            service (type):
                The avatar service class to register.

                This must be a subclass of
                :py:class:`djblets.avatars.services.base.AvatarService`.
        """
        super(AvatarServiceHook, self).initialize(service)


@six.add_metaclass(ExtensionHookPoint)
class AccountPagesHook(BaseRegistryMultiItemHook):
    """A hook for adding new pages to the My Account page.

    A page can contain one or more forms or even a custom template allowing
    for configuration of an extension.

    This takes a list of AccountPage classes as parameters, which it will
    later instantiate as necessary. Each page can be pre-populated with
    one or more custom AccountPageForm classes.
    """

    registry = AccountPage.registry

    def initialize(self, page_classes):
        """Initialize the hook.

        This will register each of the provided account page classes.

        Args:
            page_classes (list of type):
                The list of page classes to register. Each must be a subclass
                of :py:class:`~reviewboard.accounts.pages.AccountPage`.
        """
        super(AccountPagesHook, self).initialize(page_classes)


@six.add_metaclass(ExtensionHookPoint)
class AccountPageFormsHook(ExtensionHook):
    """A hook for adding new forms to a page in the My Account page.

    This is used to add custom forms to a page in the My Account page. The
    form can be used to provide user-level customization of an extension,
    through a traditional form-based approach or even through custom
    JavaScript.

    This hook takes the ID of a registered page where the form should be
    placed. Review Board supplies the following built-in page IDs:

    * ``settings``
    * ``authentication``
    * ``profile``
    * ``groups``

    Any registered page ID can be provided, whether from this extension
    or another.

    Form classes can only be added to a single page.
    """

    def initialize(self, page_id, form_classes):
        """Initialize the hook.

        This will register each of the provided page form classes on the
        account page matching the provided ID.

        Args:
            page_id (unicode):
                The page ID corresponding to a registered
                :py:class:`~reviewboard.accounts.pages.AccountPage`.

            form_classes (list of type):
                The list of form classes to register on the page. Each class
                must be a subclass of
                :py:class:`~reviewboard.accounts.forms.pages.AccountPageForm`.
        """
        self.page_id = page_id
        self.form_classes = form_classes

        page_class = AccountPage.registry.get('page_id', page_id)

        for form_class in form_classes:
            page_class.add_form(form_class)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the page form classes from the associated
        page.
        """
        page_class = AccountPage.registry.get('page_id', self.page_id)

        for form_class in self.form_classes:
            page_class.remove_form(form_class)


@six.add_metaclass(ExtensionHookPoint)
class AdminWidgetHook(BaseRegistryHook):
    """A hook for adding a new widget to the administration dashboard.

    Version Changed::
        4.0:
        Widget classes should now subclass
        :py:class:`~reviewboard.admin.widgets.AdminBaseWidget` instead of
        :py:class:`~reviewboard.admin.widgets.Widget`. Note that this will
        require a full rewrite of the widget.

        The ``primary`` argument is no longer supported when instantiating
        the hook, and will be ignored. Callers should remove it.

        Support for legacy widgets and arguments will be removed in
        Review Board 5.0.
    """

    registry = admin_widgets_registry

    def initialize(self, widget_cls, **kwargs):
        """Initialize the hook.

        This will register the provided administration widget as either a
        primary or secondary widget.

        Args:
            widget_cls (type):
                The widget class to register. This must be a subclass of
                :py:class:`~reviewboard.admin.widgets.AdminBaseWidget`.

            **kwargs (dict):
                Additional keyword arguments. These are ignored.
        """
        if issubclass(widget_cls, Widget):
            warnings.warn(
                "AdminWidgetHook's support for legacy "
                "reviewboard.admin.widgets.Widget subclasses is deprecated "
                "and will be removed in Review Board 5.0. Rewrite %r "
                "to subclass the modern "
                "reviewboard.admin.widgets.baseAdminWidget instead. This "
                "will require a full rewrite of the widget's functionality."
                % widget_cls,
                RemovedInReviewBoard50Warning,
                stacklevel=2)

        super(AdminWidgetHook, self).initialize(widget_cls)


@six.add_metaclass(ExtensionHookPoint)
class DataGridSidebarItemsHook(ExtensionHook):
    """A hook for adding items to the sidebar of a datagrid.

    Extensions can use this hook to plug new items into the sidebar of
    any datagrid supporting sidebars.

    The items can be any subclass of
    :py:class:`reviewboard.datagrids.sidebar.BaseSidebarItem`, including the
    built-in :py:class:`reviewboard.datagrids.sidebar.BaseSidebarSection` and
    built-in :py:class:`reviewboard.datagrids.sidebar.SidebarNavItem`.
    """

    def initialize(self, datagrid, item_classes):
        """Initialize the hook.

        This will register the provided datagrid sidebar item classes in the
        provided datagrid.

        Args:
            datagrid (type):
                The datagrid class to register the items on. The datagrid
                must have a sidebar, or an error will occur.

            item_classes (list of type):
                The list of item classes to register on the datagrid's
                sidebar. Each must be a subclass of
                :py:class:`~reviewboard.datagrids.sidebar.BaseSidebarItem`.

        Raises:
            ValueError:
                A datagrid was provided that does not contain a sidebar.
        """
        if not hasattr(datagrid, 'sidebar'):
            raise ValueError('The datagrid provided does not have a sidebar')

        self.datagrid = datagrid
        self.item_classes = item_classes

        for item in item_classes:
            datagrid.sidebar.add_item(item)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each item class from the datagrid's sidebar.
        """
        for item in self.item_classes:
            self.datagrid.sidebar.remove_item(item)


# We don't use the ExtensionHookPoint metaclass here, because we actually
# want these to register in the base DataGridColumnsHook point.
class DashboardColumnsHook(DataGridColumnsHook):
    """A hook for adding custom columns to the dashboard.

    Extensions can use this hook to provide one or more custom columns
    in the dashboard. These columns can be added by users, moved around,
    and even sorted, like other columns.

    Each value passed to ``columns`` must be an instance of
    :py:class:`djblets.datagrid.grids.Column`.

    It also must have an ``id`` attribute set. This must be unique within
    the dashboard. It is recommended to use a vendor-specific prefix to the
    ID, in order to avoid conflicts.
    """

    def initialize(self, columns):
        """Initialize the hook.

        This will register each of the provided columns on the Dashboard.

        Args:
            columns (list of djblets.datagrid.grids.Column):
                The list of column instances to register on the Dashboard.
        """
        super(DashboardColumnsHook, self).initialize(DashboardDataGrid,
                                                     columns)


@six.add_metaclass(ExtensionHookPoint)
class DashboardSidebarItemsHook(DataGridSidebarItemsHook):
    """A hook for adding items to the sidebar of the dashboard.

    Extensions can use this hook to plug new items into the sidebar of
    the dashboard. These will appear below the built-in items.

    The items can be any subclass of
    :py:class:`reviewboard.datagrids.sidebar.BaseSidebarItem`, including the
    built-in :py:class:`reviewboard.datagrids.sidebar.BaseSidebarSection` and
    built-in :py:class:`reviewboard.datagrids.sidebar.SidebarNavItem`.
    """

    def initialize(self, item_classes):
        """Initialize the hook.

        This will register the provided datagrid sidebar item classes in the
        Dashboard.

        Args:
            item_classes (list of type):
                The list of item classes to register on the datagrid's
                sidebar. Each must be a subclass of
                :py:class:`~reviewboard.datagrids.sidebar.BaseSidebarItem`.
        """
        super(DashboardSidebarItemsHook, self).initialize(DashboardDataGrid,
                                                          item_classes)


@six.add_metaclass(ExtensionHookPoint)
class HostingServiceHook(ExtensionHook):
    """A hook for registering a hosting service."""

    def initialize(self, service_cls):
        """Initialize the hook.

        This will register the hosting service.

        Args:
            service_cls (type):
                The hosting service class to register. This must be a
                subclass of
                :py:class:`~reviewboard.hostingsvcs.service.HostingService`.

        Raises:
            ValueError:
                The service's :py:attr:`~reviewboard.hostingsvcs.service
                .HostingService.hosting_service_id` attribute was not set.
        """
        hosting_service_id = service_cls.hosting_service_id

        if hosting_service_id is None:
            raise ValueError(_('%s.hosting_service_id must be set.')
                             % (service_cls.__name__))

        self.hosting_service_id = hosting_service_id
        register_hosting_service(hosting_service_id, service_cls)

    def shutdown(self):
        """Shut down the hook.

        This will unregister the hosting service.
        """
        unregister_hosting_service(self.hosting_service_id)


@six.add_metaclass(ExtensionHookPoint)
class IntegrationHook(GetIntegrationManagerMixin, BaseIntegrationHook):
    """A hook for registering new integration classes.

    Integrations enable Review Board to connect with third-party services in
    specialized ways. This class makes it easy to register new integrations on
    an extension, binding their lifecycles to that of the extension.
    """


@six.add_metaclass(ExtensionHookPoint)
class NavigationBarHook(ExtensionHook):
    """A hook for adding entries to the main navigation bar.

    This takes a list of entries. Each entry represents something
    on the navigation bar, and is a dictionary with the following keys:

    ``label``:
        The label to display

    ``url``:
        The URL to point to.

    ``url_name``:
        The name of the URL to point to.

    Only one of ``url`` or ``url_name`` is required. ``url_name`` will
    take precedence.

    Optionally, a callable can be passed in for ``is_enabled_for``, which takes
    a single argument (the user) and returns True or False, indicating whether
    the entries should be shown. If this is not passed in, the entries are
    always shown (including for anonymous users).

    If your hook needs to access the template context, it can override
    :py:meth:`get_entries` and return results from there.
    """

    def initialize(self, entries=[], is_enabled_for=None, *args, **kwargs):
        """Initialize the hook.

        This will register each of the entries in the navigation bar.

        Args:
            entries (list of dict):
                The list of dictionary entries representing navigation
                bar items, as documented above.

            is_enabled_for (callable, optional):
                The optional function used to determine if these entries
                should appear for a given page. This is in the format of:

                .. code-block:: python

                   def is_enabled_for(user, request, local_site_name,
                                      **kwargs):
                       return True

                If not provided, the entries will be visible on every page.

            *args (tuple):
                Additional positional arguments. Subclasses should always
                pass these to this class.

            **kwargs (dict):
                Additional keyword arguments. Subclasses should always pass
                these to this class.
        """
        self.entries = entries
        self.is_enabled_for = is_enabled_for

    def get_entries(self, context):
        """Return the navigation bar entries defined in this hook.

        This can be overridden by subclasses if they need more control over
        the entries or need to access the template context.

        Args:
            context (django.template.RequestContext):
                The template context for the page.

        Returns:
            list of dict:
            The list of navigation bar entries. This will be empty if the
            entries are not enabled for this page.
        """
        request = context['request']

        if (not callable(self.is_enabled_for) or
            self.is_enabled_for(user=request.user,
                                request=request,
                                local_site_name=context['local_site_name'])):
            return self.entries
        else:
            return []


@six.add_metaclass(ExtensionHookPoint)
class ReviewRequestApprovalHook(ExtensionHook):
    """A hook for determining if a review request is approved.

    Extensions can use this to hook into the process for determining
    review request approval, which may impact any scripts integrating
    with Review Board to, for example, allow committing to a repository.
    """

    def is_approved(self, review_request, prev_approved, prev_failure):
        """Determine if the review request is approved.

        This function is provided with the review request and the previously
        calculated approved state (either from a prior hook, or from the
        base state of ``ship_it_count > 0 and issue_open_count == 0``).

        If approved, this should return True. If unapproved, it should
        return a tuple with False and a string briefly explaining why it's
        not approved. This may be displayed to the user.

        It generally should also take the previous approved state into
        consideration in this choice (such as returning False if the previous
        state is False). This is, however, fully up to the hook.

        The approval decision may be overridden by any following hooks.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being checked for approval.

            prev_approved (bool):
                The previously-calculated approval result, either from another
                hook or by Review Board.

            prev_failure (unicode):
                The previously-calculated approval failure message, either
                from another hook or by Review Board.

        Returns:
            bool or tuple:
            Either a boolean indicating approval (re-using ``prev_failure``,
            if not approved), or a tuple in the form of
            ``(approved, failure_message)``.
        """
        raise NotImplementedError


@six.add_metaclass(ExtensionHookPoint)
class ReviewRequestFieldSetsHook(ExtensionHook):
    """A hook for creating fieldsets on the side of the review request page.

    A fieldset contains one or more fields, and is mainly used to separate
    groups of fields from each other.

    This takes a list of fieldset classes as parameters, which it will
    later instantiate as necessary. Each fieldset can be pre-populated with
    one or more custom field classes.
    """

    def initialize(self, fieldsets):
        """Initialize the hook.

        This will register each of the provided fieldsets for review
        requests.

        Args:
            fieldsets (list of type):
                The list of fieldset classes to register. Each must be a
                subclass of
                :py:class:`~reviewboard.reviews.fields.BaseReviewRequestFieldSet`.

        Raises:
            djblets.registries.errors.ItemLookupError:
                A fieldset was already registered matching an ID from this
                list.
        """
        self.fieldsets = fieldsets

        for fieldset in fieldsets:
            register_review_request_fieldset(fieldset)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the fieldsets from the review requests.
        """
        for fieldset in self.fieldsets:
            unregister_review_request_fieldset(fieldset)


@six.add_metaclass(ExtensionHookPoint)
class ReviewRequestFieldsHook(ExtensionHook):
    """A hook for creating fields on the review request page.

    This is used to create custom fields on a review request page for
    requesting and storing data. A field can be editable, or it can be only
    for display purposes. See the classes in
    :py:mod:`reviewboard.reviews.fields` for more information and
    documentation.

    This hook takes the ID of a registered fieldset where the provided
    field classes should be added. Review Board supplies three built-in
    fieldset IDs:

    ``main``:
        The fieldset with Description and Testing Done.

    ``info``:
        The "Information" fieldset on the side.

    ``reviewers``:
        The "Reviewers" fieldset on the side.

    Any registered fieldset ID can be provided, whether from this extension
    or another.

    Field classes can only be added to a single fieldset.
    """

    def initialize(self, fieldset_id, fields):
        """Initialize the hook.

        This will register each of the provided field classes into the
        fieldset with the given ID.

        Args:
            fieldset_id (unicode):
                The ID of the
                :py:class:`~reviewboard.reviews.fields.BaseReviewRequestFieldSet`
                to register.

            fields (list of type):
                The list of fields to register into the fieldset. Each must be
                a subclass of
                :py:class:`~reviewboard.reviews.fields.BaseReviewRequestField`.
        """
        self.fieldset_id = fieldset_id
        self.fields = fields

        fieldset = get_review_request_fieldset(fieldset_id)

        for field_cls in fields:
            fieldset.add_field(field_cls)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the field classes from the fieldset.
        """
        fieldset = get_review_request_fieldset(self.fieldset_id)

        for field_cls in self.fields:
            fieldset.remove_field(field_cls)


@six.add_metaclass(ExtensionHookPoint)
class WebAPICapabilitiesHook(ExtensionHook):
    """This hook allows adding capabilities to the web API server info.

    Note that this does not add the functionality, but adds to the server
    info listing.

    Extensions may only provide one instance of this hook. All capabilities
    must be registered at once.
    """

    def initialize(self, caps):
        """Initialize the hook.

        This will register each of the capabilities for the API.

        Args:
            caps (dict):
                The dictionary of capabilities to register. Each key msut
                be a string, and each value should be a boolean or a
                dictionary of string keys to booleans.

        Raises:
            KeyError:
                Capabilities have already been registered by this extension.
        """
        register_webapi_capabilities(self.extension.id, caps)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the capabilities from the API.
        """
        unregister_webapi_capabilities(self.extension.id)


@six.add_metaclass(ExtensionHookPoint)
class CommentDetailDisplayHook(ExtensionHook):
    """This hook allows adding details to the display of comments.

    The hook can provide additional details to display for a comment in a
    review and e-mails.
    """

    def render_review_comment_detail(self, comment):
        """Render additional HTML for a comment on the page.

        Subclasses must implement this to provide HTML for use on the
        review request page or review dialog.

        The result is assumed to be HTML-safe. It's important that subclasses
        escape any data as needed.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to render HTML for,

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML for the comment. This can be an empty string.
        """
        raise NotImplementedError

    def render_email_comment_detail(self, comment, is_html):
        """Render additional text or HTML for a comment in an e-mail.

        Subclasses must implement this to provide text or HTML (depending on
        the ``is_html`` flag) for use in an e-mail.

        If rendering HTML, the result is assumed to be HTML-safe. It's
        important that subclasses escape any data as needed.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to render HTML for,

            is_html (bool):
                Whether this must return HTML content.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML for the comment. This can be an empty string.
        """
        raise NotImplementedError


@six.add_metaclass(ExtensionHookPoint)
class ReviewUIHook(ExtensionHook):
    """This hook allows integration of Extension-defined Review UIs.

    This accepts a list of Review UIs specified by the Extension and
    registers them when the hook is created. Likewise, it unregisters
    the same list of Review UIs when the Extension is disabled.
    """

    def initialize(self, review_uis):
        """Initialize the hook.

        This will register the list of review UIs for use in reviewing
        file attachments.

        Args:
            review_uis (list of type):
                The list of review UI classes to register. Each must be a
                subclass of
                :py:class:`~reviewboard.reviews.ui.base.FileAttachmentReviewUI`.

        Raises:
            TypeError:
                The provided review UI class is not of a compatible type.
        """
        self.review_uis = review_uis

        for review_ui in self.review_uis:
            register_ui(review_ui)

    def shutdown(self):
        """Shut down the hook.

        This will unregister the list of review UIs.
        """
        for review_ui in self.review_uis:
            unregister_ui(review_ui)


@six.add_metaclass(ExtensionHookPoint)
class FileAttachmentThumbnailHook(ExtensionHook):
    """This hook allows custom thumbnails to be defined for file attachments.

    This accepts a list of mimetype handlers specified by the Extension
    that must:

    * Subclass :py:class:`reviewboard.attachments.mimetypes.MimetypeHandler`
    * Define a list of file mimetypes it can handle in a class variable
      called ``supported_mimetypes``
    * Define how to generate a thumbnail of that mimetype by overriding
      the instance function ``def get_thumbnail(self):``

    These mimetype handlers are registered when the hook is created. Likewise,
    it unregisters the same list of mimetype handlers when the extension is
    disabled.
    """

    def initialize(self, mimetype_handlers):
        """Initialize the hook.

        This will register each of the provided mimetype handler classes.

        Args:
            mimetype_handlers (list of type):
                The list of mimetype handlers to register. Each must be a
                subclass of
                :py:class:`~reviewboard.attachments.mimetypes.MimetypeHandler`.

        Raises:
            TypeError:
                One or more of the provided classes are not of the correct
                type.
        """
        self.mimetype_handlers = mimetype_handlers

        for mimetype_handler in self.mimetype_handlers:
            register_mimetype_handler(mimetype_handler)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the mimetype handler classes.
        """
        for mimetype_handler in self.mimetype_handlers:
            unregister_mimetype_handler(mimetype_handler)


class ActionHook(ExtensionHook):
    """A hook for injecting clickable actions into the UI.

    Actions are displayed either on the action bar of each review request or in
    the page header.

    The provided ``actions`` parameter must be a list of actions. Each action
    may be a :py:class:`dict` with the following keys:

    ``id`` (optional):
        The ID of the action.

    ``label``:
        The label for the action.

    ``url``:
        The URL to invoke when the action is clicked.

        If we want to invoke a JavaScript action, then this should be ``#``,
        and there should be a selector on the ``id`` field to attach the
        handler (as opposed to a ``javascript:`` URL, which doesn't work on all
        browsers).

    ``image`` (optional):
        The path to the image used for the icon.

    ``image_width`` (optional):
        The width of the image.

    ``image_height`` (optional):
        The height of the image.

    If our hook needs to access the template context, then it can override
    :py:meth:`get_actions` and return results from there.
    """

    def initialize(self, actions=None, *args, **kwargs):
        """Initialize this action hook.

        Args:
            actions (list, optional):
                The list of actions (of type :py:class:`dict` or
                :py:class:`~.actions.BaseReviewRequestAction`) to be added.

            *args (tuple):
                Extra positional arguments.

            **kwargs (dict):
                Extra keyword arguments.
        """
        self.actions = actions or []

    def get_actions(self, context):
        """Return the list of action information for this action hook.

        Args:
            context (django.template.Context):
                The collection of key-value pairs available in the template.

        Returns:
            list: The list of action information for this action hook.
        """
        return self.actions


class _DictAction(BaseReviewRequestAction):
    """An action for ActionHook-style dictionaries.

    For backwards compatibility, review request actions may also be supplied as
    :py:class:`ActionHook`-style dictionaries. This helper class is used by
    :py:meth:`convert_action` to convert these types of dictionaries into
    instances of :py:class:`BaseReviewRequestAction`.
    """

    def __init__(self, action_dict, applies_to):
        """Initialize this action.

        Args:
            action_dict (dict):
                A dictionary representing this action, as specified by the
                :py:class:`ActionHook` class.

            applies_to (callable):
                A callable that examines a given request and determines if this
                action applies to the page.
        """
        super(_DictAction, self).__init__()

        self.label = action_dict['label']
        self.action_id = action_dict.get(
            'id',
            '%s-dict-action' % self.label.lower().replace(' ', '-'))
        self.url = action_dict['url']
        self._applies_to = applies_to

    def should_render(self, context):
        """Return whether or not this action should render.

        Args:
            context (django.template.Context):
                The collection of key-value pairs available in the template
                just before this action is to be rendered.

        Returns:
            bool: Determines if this action should render.
        """
        return self._applies_to(context['request'])


class _DictMenuAction(BaseReviewRequestMenuAction):
    """A menu action for ReviewRequestDropdownActionHook-style dictionaries.

    For backwards compatibility, review request actions may also be supplied as
    :py:class:`ReviewRequestDropdownActionHook`-style dictionaries. This helper
    class is used by :py:meth:`convert_action` to convert these types of
    dictionaries into instances of :py:class:`BaseReviewRequestMenuAction`.
    """

    def __init__(self, child_actions, action_dict, applies_to):
        """Initialize this action.

        Args:
            child_actions (list of dict or list of BaseReviewRequestAction):
                The list of child actions to be contained by this menu action.

            action_dict (dict):
                A dictionary representing this menu action, as specified by the
                :py:class:`ReviewRequestDropdownActionHook` class.

            applies_to (callable):
                A callable that examines a given request and determines if this
                menu action applies to the page.
        """
        super(_DictMenuAction, self).__init__(child_actions)

        self.label = action_dict['label']
        self.action_id = action_dict.get(
            'id',
            '%s-dict-menu-action' % self.label.lower().replace(' ', '-'))
        self._applies_to = applies_to

    def should_render(self, context):
        """Return whether or not this action should render.

        Args:
            context (django.template.Context):
                The collection of key-value pairs available in the template
                just before this action is to be rendered.

        Returns:
            bool: Determines if this action should render.
        """
        return self._applies_to(context['request'])


@six.add_metaclass(ExtensionHookPoint)
class BaseReviewRequestActionHook(AppliesToURLMixin, ActionHook):
    """A base hook for adding review request actions to the action bar.

    Review request actions are displayed on the action bar (alongside default
    actions such as :guilabel:`Download Diff` and :guilabel:`Ship It!`) of each
    review request. This action bar is displayed on three main types of pages:

    **Review Request Pages**:
       Where reviews are displayed.

    **File Attachment Pages**:
       Where files like screenshots can be reviewed.

    **Diff Viewer Pages**:
       Where diffs/interdiffs can be viewed side-by-side.

    Each action should be an instance of
    :py:class:`~reviewboard.reviews.actions.BaseReviewRequestAction` (in
    particular, each action could be an instance of the subclass
    :py:class:`~reviewboard.reviews.actions.BaseReviewRequestMenuAction`). For
    backwards compatibility, actions may also be supplied as
    :py:class:`ActionHook`-style dictionaries.
    """

    def initialize(self, actions=None, apply_to=None, *args, **kwargs):
        """Initialize this action hook.

        Args:
            actions (list, optional):
                The list of actions (of type :py:class:`dict` or
                :py:class:`~.actions.BaseReviewRequestAction`) to be added.

            apply_to (list of unicode, optional):
                The list of URL names that this action hook will apply to.

            *args (tuple):
                Extra positional arguments.

            **kwargs (dict):
                Extra keyword arguments.

        Raises:
            KeyError:
                Some dictionary is not an :py:class:`ActionHook`-style
                dictionary.

            ValueError:
                Some review request action is neither a
                :py:class:`~.actions.BaseReviewRequestAction` nor a
                :py:class:`dict` instance.
        """
        super(BaseReviewRequestActionHook, self).initialize(
            apply_to=apply_to or [],
            *args, **kwargs)

        if actions is None:
            actions = []

        if (not class_based_actions_feature.is_enabled() and
            any(not isinstance(action, dict) for action in actions)):
            logger.error(
                'The class-based actions API is experimental and will '
                'change in a future release. It must be enabled before '
                'it can be used. The actions from %r will not be '
                'registered.'
                % self
            )
            actions = []

        self.actions = self._register_actions(actions)

    def shutdown(self):
        """Shutdown the hook and unregister all actions."""
        for action in self.actions:
            action.unregister()

    def _register_actions(self, actions):
        """Register the given list of review request actions.

        Args:
            actions (list, optional):
                The list of actions (of type :py:class:`dict` or
                :py:class:`~.actions.BaseReviewRequestAction`) to be added.

        Returns:
            list of BaseReviewRequestAction:
            The list of all registered actions.

        Raises:
            KeyError:
                Some dictionary is not an :py:class:`ActionHook`-style
                dictionary.

            ValueError:
                Some review request action is neither a
                :py:class:`~.actions.BaseReviewRequestAction` nor a
                :py:class:`dict` instance.
        """
        registered_actions = []

        # Since newly registered top-level actions are appended to the left of
        # the other previously registered top-level actions, we must iterate
        # through the actions in reverse. However, we don't want to mutate the
        # original actions and we want to preserve the order of the original
        # actions. Hence, we reverse twice in this method.
        for action in reversed(actions):
            action = self._normalize_action(action)
            action.register()
            registered_actions.append(action)

        registered_actions.reverse()

        return registered_actions

    def _normalize_action(self, action):
        """Normalize the given review request action.

        For backwards compatibility, review request actions may also be
        supplied as :py:class:`ActionHook`-style dictionaries. This helper
        method normalizes the given review request action so that each review
        request action is an instance of
        :py:class:`~.actions.BaseReviewRequestAction`.

        Args:
            action (dict or BaseReviewRequestAction):
                The review request action to be normalized.

        Returns:
            BaseReviewRequestAction: The normalized review request action.

        Raises:
            KeyError:
                The given dictionary is not an :py:class:`ActionHook`-style
                dictionary.

            ValueError:
                The given review request action is neither a
                :py:class:`~.actions.BaseReviewRequestAction` nor a
                :py:class:`dict` instance.
        """
        if isinstance(action, BaseReviewRequestAction):
            return action

        if isinstance(action, dict):
            return self.convert_action(action)

        raise ValueError('Only BaseReviewRequestAction and dict instances are '
                         'supported')

    def convert_action(self, action_dict):
        """Convert the given dictionary to a review request action instance.

        Args:
            action_dict (dict):
                A dictionary representing a review request action, as specified
                by the :py:class:`ActionHook` class.

        Returns:
            BaseReviewRequestAction:
            The corresponding review request action instance.

        Raises:
            KeyError:
                The given dictionary is not an :py:class:`ActionHook`-style
                dictionary.
        """
        for key in ('label', 'url'):
            if key not in action_dict:
                raise KeyError('ActionHook-style dicts require a %s key'
                               % repr(key))

        return _DictAction(action_dict, self.applies_to)


@six.add_metaclass(ExtensionHookPoint)
class ReviewRequestActionHook(BaseReviewRequestActionHook):
    """A hook for adding review request actions to review request pages.

    By default, actions that are passed into this hook will only be displayed
    on review request pages and not on any file attachment pages or diff
    viewer pages.
    """

    def initialize(self, actions=None, apply_to=None):
        """Initialize this action hook.

        Args:
            actions (list, optional):
                The list of actions (of type :py:class:`dict` or
                :py:class:`~.actions.BaseReviewRequestAction`) to be added.

            apply_to (list of unicode, optional):
                The list of URL names that this action hook will apply to.
                By default, this will apply to the main review request page
                only.

        Raises:
            KeyError:
                Some dictionary is not an :py:class:`ActionHook`-style
                dictionary.

            ValueError:
                Some review request action is neither a
                :py:class:`~.actions.BaseReviewRequestAction` nor a
                :py:class:`dict` instance.
        """
        super(ReviewRequestActionHook, self).initialize(
            actions=actions,
            apply_to=apply_to or [main_review_request_url_name])


@six.add_metaclass(ExtensionHookPoint)
class ReviewRequestDropdownActionHook(ReviewRequestActionHook):
    """A hook for adding dropdown menu actions to review request pages.

    Each menu action should be an instance of
    :py:class:`~reviewboard.reviews.actions.BaseReviewRequestMenuAction`. For
    backwards compatibility, menu actions may also be supplied as dictionaries
    with the following keys:

    ``id`` (optional):
        The ID of the action.

    ``label``:
        The label for the dropdown menu action.

    ``items``:
        A list of :py:class:`ActionHook`-style dictionaries.

    Example:
        .. code-block:: python

           actions = [{
               'id': 'sample-menu-action',
               'label': 'Sample Menu',
               'items': [
                   {
                       'id': 'first-item-action',
                       'label': 'Item 1',
                       'url': '#',
                   },
                   {
                       'label': 'Item 2',
                       'url': '#',
                   },
               ],
           }]
    """

    def convert_action(self, action_dict):
        """Convert the given dictionary to a review request action instance.

        Children action dictionaries are recursively converted to action
        instances.

        Args:
            action_dict (dict):
                A dictionary representing a review request menu action, as
                specified by the :py:class:`ReviewRequestDropdownActionHook`
                class.

        Returns:
            BaseReviewRequestMenuAction:
            The corresponding review request menu action instance.

        Raises:
            KeyError:
                The given review request menu action dictionary is not a
                :py:class:`ReviewRequestDropdownActionHook`-style dictionary.
        """
        for key in ('label', 'items'):
            if key not in action_dict:
                raise KeyError('ReviewRequestDropdownActionHook-style dicts '
                               'require a %s key' % repr(key))

        return _DictMenuAction(
            [
                super(ReviewRequestDropdownActionHook, self).convert_action(
                    child_action_dict)
                for child_action_dict in action_dict['items']
            ],
            action_dict,
            self.applies_to
        )


@six.add_metaclass(ExtensionHookPoint)
class DiffViewerActionHook(BaseReviewRequestActionHook):
    """A hook for adding review request actions to diff viewer pages.

    By default, actions that are passed into this hook will only be displayed
    on diff viewer pages and not on any review request pages or file attachment
    pages.
    """

    def initialize(self, actions=None, apply_to=diffviewer_url_names):
        """Initialize this action hook.

        Args:
            actions (list, optional):
                The list of actions (of type :py:class:`dict` or
                :py:class:`~.actions.BaseReviewRequestAction`) to be added.

            apply_to (list of unicode, optional):
                The list of URL names that this action hook will apply to.

        Raises:
            KeyError:
                Some dictionary is not an :py:class:`ActionHook`-style
                dictionary.

            ValueError:
                Some review request action is neither a
                :py:class:`~.actions.BaseReviewRequestAction` nor a
                :py:class:`dict` instance.
        """
        super(DiffViewerActionHook, self).initialize(
            actions,
            apply_to=apply_to or diffviewer_url_names)


@six.add_metaclass(ExtensionHookPoint)
class HeaderActionHook(ActionHook):
    """A hook for adding actions to the page header."""


@six.add_metaclass(ExtensionHookPoint)
class HeaderDropdownActionHook(ActionHook):
    """A hook for adding dropdown menu actions to the page header."""


@six.add_metaclass(ExtensionHookPoint)
class UserInfoboxHook(ExtensionHook):
    """A hook for adding information to the user infobox.

    Extensions can use this hook to add additional pieces of data to the box
    which pops up when hovering the mouse over a user.
    """

    def initialize(self, template_name=None):
        """Initialize the hook.

        Args:
            template_name (six.text_type):
                The template to render with the default :py:func:`render`
                method.
        """
        self.template_name = template_name

    def get_extra_context(self, user, request, local_site, **kwargs):
        """Return extra context to use when rendering the template.

        This may be overridden in order to make use of the default
        :py:func:`render` method.

        Args:
            user (django.contrib.auth.models.User):
                The user whose infobox is being shown.

            request (django.http.HttpRequest):
                The request for the infobox view.

            local_site (reviewboard.site.models.LocalSite):
                The local site, if any.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            Additional context to include when rendering the template.
        """
        return {}

    def get_etag_data(self, user, request, local_site, **kwargs):
        """Return data to be included in the user infobox ETag.

        The infobox view uses an ETag to enable browser caching of the content.
        If the extension returns data which can change, this method should
        return a string which is unique to that data.

        Args:
            user (django.contrib.auth.models.User):
                The user whose infobox is being shown.

            request (django.http.HttpRequest):
                The request for the infobox view.

            local_site (reviewboard.site.models.LocalSite):
                The local site, if any.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            unicode:
            A string to be included in the ETag for the view.
        """
        return ''

    def render(self, user, request, local_site, **kwargs):
        """Return content to include in the user infobox.

        This may be overridden in the case where providing a custom template
        and overriding :py:func:`get_extra_context` is insufficient.

        Args:
            user (django.contrib.auth.models.User):
                The user whose infobox is being shown.

            request (django.http.HttpRequest):
                The request for the infobox view.

            local_site (reviewboard.site.models.LocalSite):
                The local site, if any.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.utils.safestring.SafeText:
            Text to include in the infobox HTML.
        """
        assert self.template_name is not None

        context = {
            'extension': self.extension,
            'user': user,
        }
        context.update(self.get_extra_context(user=user,
                                              request=request,
                                              local_site=local_site))
        return render_to_string(
            template_name=self.template_name,
            context=context,
            request=request)


@six.add_metaclass(ExtensionHookPoint)
class UserPageSidebarItemsHook(DataGridSidebarItemsHook):
    """A hook for adding items to the sidebar of the user page.

    Extensions can use this hook to plug new items into the sidebar of
    the user page. These will appear below the built-in items.

    The items can be any subclass of
    :py:class:`reviewboard.datagrids.sidebar.BaseSidebarItem`, including the
    built-in :py:class:`reviewboard.datagrids.sidebar.BaseSidebarSection` and
    built-in :py:class:`reviewboard.datagrids.sidebar.SidebarNavItem`.
    """

    def initialize(self, item_classes):
        """Initialize the hook.

        This will register the provided datagrid sidebar item classes in the
        user page's datagrid.

        Args:
            item_classes (list of type):
                The list of item classes to register on the datagrid's
                sidebar. Each must be a subclass of
                :py:class:`~reviewboard.datagrids.sidebar.BaseSidebarItem`.
        """
        super(UserPageSidebarItemsHook, self).initialize(
            UserPageReviewRequestDataGrid, item_classes)


@six.add_metaclass(ExtensionHookPoint)
class EmailHook(ExtensionHook):
    """A hook for changing the recipients of e-mails.

    Extensions can use this hook to change the contents of the To and CC fields
    of e-mails. This should be subclassed in an extension to provide the
    desired behaviour. This class is a base class for more specialized
    extension hooks. If modifying only one type of e-mail's fields is desired,
    one of the following classes should be subclassed instead.

    * :py:class:`ReviewPublishedEmailHook`
    * :py:class:`ReviewReplyPublishedEmailHook`
    * :py:class:`ReviewRequestPublishedEmailHook`
    * :py:class:`ReviewRequestClosedEmailHook`

    However, if more specialized behaviour is desired, this class can be
    subclassed.
    """

    def initialize(self, signals):
        """Initialize the hook.

        Args:
            signals (list):
                A list of :py:class:`Signals <django.dispatch.Signal>` that,
                when triggered, will cause e-mails to be sent. Valid signals
                are:

                * :py:data:`~reviewboard.reviews.signals.review_request_published`
                * :py:data:`~reviewboard.reviews.signals.review_request_closed`
                * :py:data:`~reviewboard.reviews.signals.review_published`
                * :py:data:`~reviewboard.reviews.signals.reply_published`
        """
        self.signals = signals

        for signal in signals:
            register_email_hook(signal, self)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the e-mail handlers.
        """
        for signal in self.signals:
            unregister_email_hook(signal, self)

    def get_to_field(self, to_field, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            kwargs (dict):
                Additional keyword arguments that will be passed based on the
                type of e-mail being sent.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            cc_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive a carbon copy of the e-mail.

            kwargs (dict):
                Additional keyword arguments that will be passed based on the
                type of e-mail being sent.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review publishing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook."""
        super(ReviewPublishedEmailHook, self).initialize(
            signals=[review_published])

    def get_to_field(self, to_field, review, user, review_request,
                     to_owner_only, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            review (reviewboard.reviews.models.Review):
                The review that was published.

            user (django.contrib.auth.models.User):
                The user who published the review.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            to_owner_only (bool):
                Whether or not the review was marked as being targeted at only
                the submitter.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review, user, review_request,
                     to_owner_only, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            cc_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive a carbon copy of the e-mail.

            review (reviewboard.reviews.models.Review):
                The review that was published.

            user (django.contrib.auth.models.User):
                The user who published the review.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            to_owner_only (bool):
                Whether or not the review was marked as being targeted at only
                the submitter.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewReplyPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review reply publishing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook."""
        super(ReviewReplyPublishedEmailHook, self).initialize(
            signals=[reply_published])

    def get_to_field(self, to_field, reply, user, review_request, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            reply (reviewboard.reviews.models.Review):
                The review reply that was published.

            user (django.contrib.auth.models.User):
                The user who published the review reply.

            review (reviewboard.reviews.model.Review):
                The review the reply is in reply to.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, reply, user, review_request, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive a carbon copy of the e-mail

            reply (reviewboard.reviews.models.Review):
                The review reply that was published.

            user (django.contrib.auth.models.User):
                The user who published the reply.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewRequestClosedEmailHook(EmailHook):
    """A hook for changing the recipients of review request closing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook."""
        super(ReviewRequestClosedEmailHook, self).initialize(
            signals=[review_request_closed])

    def get_to_field(self, to_field, review_request, user, close_type,
                     **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who closed the review request.

            close_type (unicode):
                How the review request was closed. This is one of
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.SUBMITTED`
                or
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.DISCARDED`.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review_request, user, close_type,
                     **kwargs):
        """Return the CC field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>` that
                will receive a carbon copy of the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who closed the review request.

            close_type (unicode):
                How the review request was closed. This is one of
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.SUBMITTED`
                or
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.DISCARDED`.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewRequestPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review request publishing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook. """
        super(ReviewRequestPublishedEmailHook, self).initialize(
            signals=[review_request_published])

    def get_to_field(self, to_field, review_request, user, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>` that
                will receive the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who published the review request.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review_request, user, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>` that
                will receive a carbon copy of the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who published the review request.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field


@six.add_metaclass(ExtensionHookPoint)
class APIExtraDataAccessHook(ExtensionHook):
    """A hook for setting access states to extra data fields.

    Extensions can use this hook to register ``extra_data`` fields with
    certain access states on subclasses of
    :py:data:`~reviewboard.webapi.base.WebAPIResource`.

    This accepts a list of ``field_set`` values specified by the Extension and
    registers them when the hook is created. Likewise, it unregisters the same
    list of ``field_set`` values when the Extension is disabled.

    Each element of ``field_set`` is a 2-:py:class:`tuple` where the first
    element of the tuple is the field's path (as a :py:class:`tuple`) and the
    second is the field's access state (as one of
    :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PUBLIC`
    or :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PRIVATE`).

    Example:
        .. code-block:: python

            obj.extra_data = {
                'foo': {
                    'bar' : 'private_data',
                    'baz' : 'public_data'
                }
            }

            ...

            APIExtraDataAccessHook(
                extension,
                resource,
                [
                    (('foo', 'bar'), ExtraDataAccessLevel.ACCESS_STATE_PRIVATE,
                ])
    """

    def initialize(self, resource, field_set):
        """Initialize the APIExtraDataAccessHook.

        Args:
            resource (reviewboard.webapi.base.WebAPIResource):
                The resource to modify access states for.

            field_set (list):
                Each element of ``field_set`` is a 2-:py:class:`tuple` where
                the first element of the tuple is the field's path (as a
                :py:class:`tuple`) and the second is the field's access state
                (as one of
                :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PUBLIC`
                or :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PRIVATE`).
        """
        self.resource = resource
        self.field_set = field_set

        resource.extra_data_access_callbacks.register(
            self.get_extra_data_state)

    def get_extra_data_state(self, key_path):
        """Return the state of an extra_data field.

        Args:
            key_path (tuple):
                A tuple of strings representing the path of an extra_data
                field.

        Returns:
            int:
            The access state of the provided field or ``None``.
        """
        for path, access_state in self.field_set:
            if path == key_path:
                return access_state

        return None

    def shutdown(self):
        """Shut down the hook.

        This will unregister the access levels from the resource.
        """
        try:
            self.resource.extra_data_access_callbacks.unregister(
                self.get_extra_data_state)
        except ItemLookupError:
            pass


__all__ = [
    'AccountPageFormsHook',
    'AccountPagesHook',
    'ActionHook',
    'AdminWidgetHook',
    'APIExtraDataAccessHook',
    'AuthBackendHook',
    'AvatarServiceHook',
    'BaseReviewRequestActionHook',
    'CommentDetailDisplayHook',
    'ConsentRequirementHook',
    'DashboardColumnsHook',
    'DashboardSidebarItemsHook',
    'DataGridColumnsHook',
    'DataGridSidebarItemsHook',
    'DiffViewerActionHook',
    'EmailHook',
    'ExtensionHook',
    'FileAttachmentThumbnailHook',
    'HeaderActionHook',
    'HeaderDropdownActionHook',
    'HostingServiceHook',
    'IntegrationHook',
    'NavigationBarHook',
    'ReviewRequestActionHook',
    'ReviewRequestApprovalHook',
    'ReviewRequestClosedEmailHook',
    'ReviewRequestDropdownActionHook',
    'ReviewRequestFieldSetsHook',
    'ReviewRequestFieldsHook',
    'ReviewRequestPublishedEmailHook',
    'ReviewPublishedEmailHook',
    'ReviewReplyPublishedEmailHook',
    'ReviewUIHook',
    'SignalHook',
    'TemplateHook',
    'URLHook',
    'UserInfoboxHook',
    'UserPageSidebarItemsHook',
    'WebAPICapabilitiesHook',
]
