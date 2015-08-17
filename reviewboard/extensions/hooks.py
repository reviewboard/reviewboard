from __future__ import unicode_literals

import inspect
import warnings

from django.utils import six
from djblets.extensions.hooks import (DataGridColumnsHook, ExtensionHook,
                                      ExtensionHookPoint, SignalHook,
                                      TemplateHook, URLHook)

from reviewboard.accounts.backends import (register_auth_backend,
                                           unregister_auth_backend)
from reviewboard.accounts.pages import (get_page_class,
                                        register_account_page_class,
                                        unregister_account_page_class)
from reviewboard.attachments.mimetypes import (register_mimetype_handler,
                                               unregister_mimetype_handler)
from reviewboard.datagrids.grids import DashboardDataGrid, UserPageDataGrid
from reviewboard.hostingsvcs.service import (register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.notifications.email import (register_email_hook,
                                             unregister_email_hook)
from reviewboard.reviews.fields import (get_review_request_fieldset,
                                        register_review_request_fieldset,
                                        unregister_review_request_fieldset)
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.reviews.ui.base import register_ui, unregister_ui


@six.add_metaclass(ExtensionHookPoint)
class AuthBackendHook(ExtensionHook):
    """A hook for registering an authentication backend.

    Authentication backends control user authentication, registration, and
    user lookup, and user data manipulation.

    This hook takes the class of an authentication backend that should
    be made available to the server.
    """
    def __init__(self, extension, backend_cls):
        super(AuthBackendHook, self).__init__(extension)

        self.backend_cls = backend_cls
        register_auth_backend(backend_cls)

    def shutdown(self):
        super(AuthBackendHook, self).shutdown()

        unregister_auth_backend(self.backend_cls)


@six.add_metaclass(ExtensionHookPoint)
class AccountPagesHook(ExtensionHook):
    """A hook for adding new pages to the My Account page.

    A page can contain one or more forms or even a custom template allowing
    for configuration of an extension.

    This takes a list of AccountPage classes as parameters, which it will
    later instantiate as necessary. Each page can be pre-populated with
    one or more custom AccountPageForm classes.
    """
    def __init__(self, extension, page_classes):
        super(AccountPagesHook, self).__init__(extension)

        self.page_classes = page_classes

        for page_class in page_classes:
            register_account_page_class(page_class)

    def shutdown(self):
        super(AccountPagesHook, self).shutdown()

        for page_class in self.page_classes:
            unregister_account_page_class(page_class)


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
    def __init__(self, extension, page_id, form_classes):
        super(AccountPageFormsHook, self).__init__(extension)

        self.page_id = page_id
        self.form_classes = form_classes

        page_class = get_page_class(page_id)

        for form_class in form_classes:
            page_class.add_form(form_class)

    def shutdown(self):
        super(AccountPageFormsHook, self).shutdown()

        page_class = get_page_class(self.page_id)

        for form_class in self.form_classes:
            page_class.remove_form(form_class)


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
    def __init__(self, extension, datagrid, item_classes):
        super(DataGridSidebarItemsHook, self).__init__(extension)

        if not hasattr(datagrid, 'sidebar'):
            raise ValueError('The datagrid provided does not have a sidebar')

        self.datagrid = datagrid
        self.item_classes = item_classes

        for item in item_classes:
            datagrid.sidebar.add_item(item)

    def shutdown(self):
        super(DataGridSidebarItemsHook, self).shutdown()

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
    def __init__(self, extension, columns):
        super(DashboardColumnsHook, self).__init__(
            extension, DashboardDataGrid, columns)


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
    def __init__(self, extension, item_classes):
        super(DashboardSidebarItemsHook, self).__init__(
            extension, DashboardDataGrid, item_classes)


@six.add_metaclass(ExtensionHookPoint)
class HostingServiceHook(ExtensionHook):
    """A hook for registering a hosting service."""
    def __init__(self, extension, service_cls):
        super(HostingServiceHook, self).__init__(extension)

        self.name = service_cls.name
        register_hosting_service(service_cls.name, service_cls)

    def shutdown(self):
        super(HostingServiceHook, self).shutdown()

        unregister_hosting_service(self.name)


@six.add_metaclass(ExtensionHookPoint)
class NavigationBarHook(ExtensionHook):
    """A hook for adding entries to the main navigation bar.

    This takes a list of entries. Each entry represents something
    on the navigation bar, and is a dictionary with the following keys:

        * ``label``:    The label to display
        * ``url``:      The URL to point to.
        * ``url_name``: The name of the URL to point to.

    Only one of ``url`` or ``url_name`` is required. ``url_name`` will
    take precedence.

    Optionally, a callable can be passed in for ``is_enabled_for``, which takes
    a single argument (the user) and returns True or False, indicating whether
    the entries should be shown. If this is not passed in, the entries are
    always shown (including for anonymous users).

    If your hook needs to access the template context, it can override
    get_entries and return results from there.
    """
    def __init__(self, extension, entries={}, is_enabled_for=None,
                 *args, **kwargs):
        super(NavigationBarHook, self).__init__(extension, *args,
                                                **kwargs)
        self.entries = entries
        self.is_enabled_for = is_enabled_for

        if callable(is_enabled_for):
            argspec = inspect.getargspec(is_enabled_for)

            if argspec.keywords is None:
                warnings.warn(
                    'NavigationBarHook.is_enabled_for is being passed '
                    'a function without keyword arguments by %r. This '
                    'is deprecated.'
                    % extension,
                    DeprecationWarning)

                self.is_enabled_for = \
                    lambda user, **kwargs: is_enabled_for(user)

    def get_entries(self, context):
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
        """Determines if the review request is approved.

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
    def __init__(self, extension, fieldsets):
        super(ReviewRequestFieldSetsHook, self).__init__(extension)

        self.fieldsets = fieldsets

        for fieldset in fieldsets:
            register_review_request_fieldset(fieldset)

    def shutdown(self):
        super(ReviewRequestFieldSetsHook, self).shutdown()

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

        * ``main``      - The fieldset with Description and Testing Done.
        * ``info``      - The "Information" fieldset on the side.
        * ``reviewers`` - The "Reviewers" fieldset on the side.

    Any registered fieldset ID can be provided, whether from this extension
    or another.

    Field classes can only be added to a single fieldset.
    """
    def __init__(self, extension, fieldset_id, fields):
        super(ReviewRequestFieldsHook, self).__init__(extension)

        self.fieldset_id = fieldset_id
        self.fields = fields

        fieldset = get_review_request_fieldset(fieldset_id)

        for field_cls in fields:
            fieldset.add_field(field_cls)

    def shutdown(self):
        super(ReviewRequestFieldsHook, self).shutdown()

        fieldset = get_review_request_fieldset(self.fieldset_id)

        for field_cls in self.fields:
            fieldset.remove_field(field_cls)


@six.add_metaclass(ExtensionHookPoint)
class CommentDetailDisplayHook(ExtensionHook):
    """This hook allows adding details to the display of comments.

    The hook can provide additional details to display for a comment in a
    review and e-mails.
    """
    def render_review_comment_detail(self, comment):
        raise NotImplementedError

    def render_email_comment_detail(self, comment, is_html):
        raise NotImplementedError


@six.add_metaclass(ExtensionHookPoint)
class ReviewUIHook(ExtensionHook):
    """This hook allows integration of Extension-defined Review UIs.

    This accepts a list of Review UIs specified by the Extension and
    registers them when the hook is created. Likewise, it unregisters
    the same list of Review UIs when the Extension is disabled.
    """
    def __init__(self, extension, review_uis):
        super(ReviewUIHook, self).__init__(extension)
        self.review_uis = review_uis

        for review_ui in self.review_uis:
            register_ui(review_ui)

    def shutdown(self):
        super(ReviewUIHook, self).shutdown()

        for review_ui in self.review_uis:
            unregister_ui(review_ui)


@six.add_metaclass(ExtensionHookPoint)
class FileAttachmentThumbnailHook(ExtensionHook):
    """This hook allows custom thumbnails to be defined for file attachments.

    This accepts a list of Mimetype Handlers specified by the Extension
    that must:

       *
          Subclass
          :py:class:`reviewboard.attachments.mimetypes.MimetypeHandler`
       *
          Define a list of file mimetypes it can handle in a class variable
          called `supported_mimetypes`
       *
          Define how to generate a thumbnail of that mimetype by overriding
          the instance function `def get_thumbnail(self):`

    These MimetypeHandlers are registered when the hook is created. Likewise,
    it unregisters the same list of MimetypeHandlers when the Extension is
    disabled.
    """
    def __init__(self, extension, mimetype_handlers):
        super(FileAttachmentThumbnailHook, self).__init__(extension)
        self.mimetype_handlers = mimetype_handlers

        for mimetype_handler in self.mimetype_handlers:
            register_mimetype_handler(mimetype_handler)

    def shutdown(self):
        super(FileAttachmentThumbnailHook, self).shutdown()

        for mimetype_handler in self.mimetype_handlers:
            unregister_mimetype_handler(mimetype_handler)


class ActionHook(ExtensionHook):
    """A hook for adding actions to a review request.

    Actions are displayed somewhere on the action bar (alongside Reviews,
    Close, etc.) of the review request. The subclasses of ActionHook should
    be used to determine placement.

    The provided actions parameter must be a list of actions. Each
    action must be a dict with the following keys:

       * `id`:           The ID of this action (optional).
       * `image`:        The path to the image used for the icon (optional).
       * `image_width`:  The width of the image (optional).
       * `image_height`: The height of the image (optional).
       * `label`:        The label for the action.
       * `url`:          The URI to invoke when the action is clicked.
                         If you want to invoke a javascript action, this should
                         be '#', and you should use a selector on the `id`
                         field to attach the handler (as opposed to a
                         javascript: URL, which doesn't work on all browsers).

    If your hook needs to access the template context, it can override
    get_actions and return results from there.
    """
    def __init__(self, extension, actions=[], *args, **kwargs):
        super(ActionHook, self).__init__(extension, *args, **kwargs)
        self.actions = actions

    def get_actions(self, context):
        """Returns the list of action information for this action."""
        return self.actions


@six.add_metaclass(ExtensionHookPoint)
class ReviewRequestActionHook(ActionHook):
    """A hook for adding an action to the review request page."""


@six.add_metaclass(ExtensionHookPoint)
class ReviewRequestDropdownActionHook(ActionHook):
    """A hook for adding an drop down action to the review request page.

    The actions for a drop down action should contain:

       * `id`:      The ID of this action (optional).
       * `label`:   The label of the drop-down.
       * `items`:   A list of ActionHook-style dicts (see ActionHook params).

    For example::

        actions = [{
            'id': 'id 0',
            'label': 'Title',
            'items': [
                {
                    'id': 'id 1',
                    'label': 'Item 1',
                    'url': '...',
                },
                {
                    'id': 'id 2',
                    'label': 'Item 2',
                    'url': '...',
                }
            ]
        }]
    """


@six.add_metaclass(ExtensionHookPoint)
class DiffViewerActionHook(ActionHook):
    """A hook for adding an action to the diff viewer page."""


@six.add_metaclass(ExtensionHookPoint)
class HeaderActionHook(ActionHook):
    """A hook for putting an action in the page header."""


@six.add_metaclass(ExtensionHookPoint)
class HeaderDropdownActionHook(ActionHook):
    """A hook for putting multiple actions into a header dropdown."""


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
    def __init__(self, extension, item_classes):
        super(UserPageSidebarItemsHook, self).__init__(
            extension, UserPageDataGrid, item_classes)


@six.add_metaclass(ExtensionHookPoint)
class EmailHook(ExtensionHook):
    """A hook for changing the recipients of e-mails.

    Extensions can use this hook to change the contents of the To and CC fields
    of e-mails. This should be subclassed in an extension to provide the
    desired behaviour. This class is a base class for more specialized
    extension hooks. If modifying only one type of e-mail's fields is desired,
    one of the following classes should be sub-classed instead.

    * :py:class:`ReviewPublishedEmailHook`
    * :py:class:`ReviewReplyPublishedEmailHook`
    * :py:class:`ReviewRequestPublishedEmailHook`
    * :py:class:`ReviewRequestClosedEmailHook`

    However, if more specialized behaviour is desired, this class can be
    sub-classed.
    """

    def __init__(self, extension, signals=None):
        """Initialize the EmailHook.

        Args:
            extension (reviewboard.extensions.base.Extension):
                The extension creating this hook.

            signals (list):
                A list of :py:class:`Signals <django.dispatch.Signal>` that,
                when triggered, will cause e-mails to be sent. Valid signals
                are:

                * :py:data:`~reviewboard.reviews.signals.review_request_published`
                * :py:data:`~reviewboard.reviews.signals.review_request_closed`
                * :py:data:`~reviewboard.reviews.signals.review_published`
                * :py:data:`~reviewboard.reviews.signals.reply_published`
        """
        super(EmailHook, self).__init__(extension)

        self.signals = set(signals or [])

        for signal in self.signals:
            register_email_hook(signal, self)

    def shutdown(self):
        """Unregister the e-mail handlers."""
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
    """A hook for changing the recipients of review publishing e-mails."""

    def __init__(self, extension):
        """Initialize the ReviewPublishedEmailHook.

        Args:
            extension (reviewboard.extensions.base.Extension):
                The extension registering this hook.
        """
        super(ReviewPublishedEmailHook, self).__init__(
            extension,
            signals=[review_published])

    def get_to_field(self, to_field, review, user, review_request):
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

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review, user, review_request):
        """Return the CC field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive a carbon copy of the e-mail.

            review (reviewboard.reviews.models.Review):
                The review that was published.

            user (django.contrib.auth.models.User):
                The user who published the review.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewReplyPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review reply publishing e-mails.
    """

    def __init__(self, extension):
        """Initialize the ReviewReplyPublishedEmailHook.

        Args:
            extension (djblets.extensions.Extension):
                The extension registering this hook.
        """
        super(ReviewReplyPublishedEmailHook, self).__init__(
            extension,
            signals=[reply_published])

    def get_to_field(self, to_field, reply, user, review_request):
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

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, reply, user, review_request):
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

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewRequestClosedEmailHook(EmailHook):
    """A hook for changing the recipients of review request closing e-mails."""

    def __init__(self, extension):
        """Initialize the ReviewRequestClosedEmailHook.

        Args:
            extension (reviewboard.extensions.base.Extension):
                The extension registering this hook.
        """
        super(ReviewRequestClosedEmailHook, self).__init__(
            extension,
            signals=[review_request_closed])

    def get_to_field(self, to_field, review_request, user, close_type):
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

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review_request, user, close_type):
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

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewRequestPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review request publishing e-mails.
    """

    def __init__(self, extension):
        """Initialize the ReviewRequestPublishedEmailHook.

        Args:
            extension (reviewboard.extensions.base.Extension):
                The extension registering this hook.
        """
        super(ReviewRequestPublishedEmailHook, self).__init__(
            extension,
            signals=[review_request_published])

    def get_to_field(self, to_field, review_request, user):
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

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review_request, user):
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

        Returns:
            set: The desired CC field.
        """
        return cc_field


__all__ = [
    'AccountPageFormsHook',
    'AccountPagesHook',
    'ActionHook',
    'AuthBackendHook',
    'CommentDetailDisplayHook',
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
    'UserPageSidebarItemsHook',
]
