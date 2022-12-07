"""Base classes for actions.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, TYPE_CHECKING, cast

from django.http import HttpRequest
from django.template import Context
from django.template.loader import render_to_string
from django.utils.safestring import SafeText, mark_safe

if TYPE_CHECKING:
    # This is available only in django-stubs.
    from django.utils.functional import _StrOrPromise


class AttachmentPoint:
    """Attachment points for actions.

    Version Added:
        6.0
    """

    #: Attachment for actions which do not want to render in the UI.
    #:
    #: This can be used for actions which want to be JavaScript-only, and may
    #: be used in the future for things like keyboard shortcuts or a command-K
    #: bar.
    NON_UI = 'non-ui'

    #: Attachment for actions in the page header.
    HEADER = 'header'

    #: Attachment for actions on the left side of the review request header.
    REVIEW_REQUEST_LEFT = 'review-request-left'

    #: Attachment for actions on the right side of the review request header.
    REVIEW_REQUEST = 'review-request'

    #: Attachment for actions in the unified draft banner.
    UNIFIED_BANNER = 'unified-banner'


class BaseAction:
    """Base class for actions.

    Version Added:
        6.0
    """

    #: The internal ID of the action.
    #:
    #: This must be unique.
    #:
    #: Type:
    #:     str
    action_id: Optional[str] = None

    #: A list of URLs to apply to.
    #:
    #: If this is ``None``, the action will be loaded on all pages. Otherwise,
    #: it will be limited to the URLs listed here.
    #:
    #: Type:
    #:     list of str
    apply_to: Optional[List[str]] = None

    #: The attachment point for the action.
    #:
    #: Type:
    #:     str
    attachment: str = AttachmentPoint.REVIEW_REQUEST

    #: A class name to use for an icon.
    #:
    #: If specified, this should be the entire class to apply to a <span>
    #: element to display an icon. For example, 'fa fa-rss'.
    #:
    #: Type:
    #:     str
    icon_class: Optional[str] = None

    #: The class to instantiate for the JavaScript model.
    #:
    #: Type:
    #:     str
    js_model_class: str = 'RB.Actions.Action'

    #: The name of the template to use for rendering action JavaScript.
    #:
    #: Type
    #:     str
    js_template_name: str = 'actions/action.js'

    #: The class to instantiate for the JavaScript view.
    #:
    #: Type:
    #:     str
    js_view_class: str = 'RB.Actions.ActionView'

    #: The user-visible label.
    #:
    #: Type:
    #:     str
    label: Optional[_StrOrPromise] = None

    #: The ID of the parent menu action, if available.
    #:
    #: Type:
    #:     str
    parent_id: Optional[str] = None

    #: The name of the template to use when rendering.
    #:
    #: Type:
    #:     str
    template_name: str = 'actions/action.html'

    #: The URL that this action links to.
    #:
    #: Type:
    #:     str
    url: str = '#'

    #: Whether this action is visible.
    #:
    #: Type:
    #:     bool
    visible: bool = True

    ######################
    # Instance variables #
    ######################

    #: The list of child actions, if this is a menu.
    #:
    #: Type:
    #:     list of BaseAction
    child_actions: List[BaseAction]

    #: The parent of this action, if this is a menu item.
    #:
    #: Type:
    #:     BaseMenuAction
    parent_action: Optional[BaseMenuAction]

    def __init__(self) -> None:
        """Initialize the action."""
        self.parent_action = None
        self.child_actions = []

    @property
    def depth(self) -> int:
        """The depth of the action.

        Type:
            int
        """
        if self.parent_action is None:
            return 0
        else:
            return self.parent_action.depth + 1

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`visible` in that non-visible actions still
        render but are hidden by CSS, whereas if this returns ``False`` the
        action will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']

        if (self.parent_action and not
            self.parent_action.should_render(context=context)):
            return False

        if (self.apply_to and not
            (request.resolver_match and
             request.resolver_match.url_name in self.apply_to)):
            return False

        return True

    def get_dom_element_id(self) -> str:
        """Return the ID used for the DOM element for this action.

        Returns:
            str:
            The ID used for the element.
        """
        return 'action-%s' % self.action_id

    def get_js_model_data(self) -> dict:
        """Return data to be passed to the JavaScript model.

        Returns:
            dict:
            A dictionary of attributes to pass to the model instance.
        """
        return {
            'actionId': self.action_id,
            'visible': self.visible,
        }

    def get_js_view_data(self) -> dict:
        """Return data to be passed to the JavaScript view.

        Returns:
            dict:
            A dictionary of options to pass to the view instance.
        """
        return {}

    def get_label(
        self,
        *,
        context: Context,
    ) -> _StrOrPromise:
        """Return the label for the action.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The label to use for the action.
        """
        assert self.label is not None
        return self.label

    def get_url(
        self,
        *,
        context: Context,
    ) -> str:
        """Return the URL for the action.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The URL to use for the action.
        """
        assert self.url is not None
        return self.url

    def get_visible(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether the action should start visible.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should start visible. ``False``, otherwise.
        """
        return self.visible

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict:
        """Return extra template context for the action.

        Subclasses can override this to provide additional context needed by
        the template for the action. By default, this returns an empty
        dictionary.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        return {
            'has_parent': self.parent_id is not None,
            'id': self.action_id,
            'label': self.get_label(context=context),
            'url': self.get_url(context=context),
            'visible': self.get_visible(context=context),
        }

    def render(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> SafeText:
        """Render the action.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            django.utils.safestring.SafeText:
            The rendered action HTML.
        """
        if self.should_render(context=context):
            context.push()

            try:
                context['action'] = self
                context.update(self.get_extra_context(request=request,
                                                      context=context))
                return render_to_string(
                    template_name=self.template_name,
                    context=cast(Mapping[str, Any], context.flatten()),
                    request=request)
            finally:
                context.pop()
        else:
            return mark_safe('')

    def render_js(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> SafeText:
        """Render the action's JavaScript.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            django.utils.safestring.SafeText:
            The rendered action JavaScript.
        """
        if self.js_template_name and self.should_render(context=context):
            context.push()

            try:
                context['action'] = self
                return render_to_string(
                    template_name=self.js_template_name,
                    context=cast(Mapping[str, Any], context.flatten()),
                    request=request)
            finally:
                context.pop()
        else:
            return mark_safe('')


class BaseMenuAction(BaseAction):
    """Base class for menu actions.

    Version Added:
        6.0
    """

    template_name = 'actions/menu_action.html'
    js_model_class = 'RB.Actions.MenuAction'
    js_view_class = 'RB.Actions.MenuActionView'

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict:
        """Return extra template context for the action.

        Subclasses can override this to provide additional context needed by
        the template for the action. By default, this returns an empty
        dictionary.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        from reviewboard.actions import actions_registry

        extra_context = super().get_extra_context(request=request,
                                                  context=context)
        extra_context['children'] = list(
            actions_registry.get_children(self.action_id))
        return extra_context

    def get_js_model_data(self) -> dict:
        """Return data to be passed to the JavaScript model.

        Returns:
            dict:
            A dictionary of attributes to pass to the model instance.
        """
        from reviewboard.actions import actions_registry

        data = super().get_js_model_data()
        data['children'] = [
            child.action_id
            for child in actions_registry.get_children(self.action_id)
        ]
        return data
