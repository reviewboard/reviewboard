"""Base classes for actions.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
from typing import Any, List, Mapping, Optional, TYPE_CHECKING, cast

from django.template.loader import render_to_string
from django.utils.safestring import SafeText, mark_safe

from reviewboard.actions.errors import ActionError
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.http import HttpRequest
    from django.template import Context
    from typelets.django.json import SerializableDjangoJSONDict
    from typelets.django.strings import StrOrPromise

    from reviewboard.actions.registry import ActionsRegistry


logger = logging.getLogger(__name__)


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

    #: Attachment for actions in the quick access area.
    #:
    #: Version Added:
    #:     7.1
    QUICK_ACCESS = 'quick-access'


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
    label: (StrOrPromise | None) = None

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

    #: A URL name to resolve.
    #:
    #: If this is not None, it will take precedence over :py:attr:`url`.
    #:
    #: Type:
    #:     str
    url_name: Optional[str] = None

    #: The user-visible verbose label.
    #:
    #: This can be used to provide a longer label for wider UIs that would
    #: benefit from a more descriptive label. It's also intended for ARIA
    #: labels.
    #:
    #: This is always optional.
    #:
    #: Version Added:
    #:     7.1
    verbose_label: (StrOrPromise | None) = None

    #: Whether this action is visible.
    #:
    #: Type:
    #:     bool
    visible: bool = True

    ######################
    # Instance variables #
    ######################

    #: The list of child actions, if this is a grouped action.
    child_actions: list[BaseAction]

    #: The parent of this action, if this is an item in a group.
    parent_action: BaseGroupAction | None

    #: The parent registry managing this action.
    #:
    #: Version Added:
    #:     7.1
    parent_registry: ActionsRegistry | None

    def __init__(self) -> None:
        """Initialize the action."""
        self.parent_action = None
        self.child_actions = []
        self.parent_registry = None

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

    def is_custom_rendered(self) -> bool:
        """Whether this action uses custom rendering.

        By default, this will return ``True`` if a custom template name is
        used. If the JavaScript side needs to override rendering, the subclass
        should explicitly return ``True``.

        Version Added:
            7.0

        Returns:
            bool:
            ``True`` if this action uses custom rendering. ``False`` if it
            does not.
        """
        return self.template_name != BaseAction.template_name

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

        from reviewboard.extensions.hooks.actions import HideActionHook

        for hook in HideActionHook.hooks:
            if self.action_id in hook.hidden_action_ids:
                return False

        return True

    def get_dom_element_id(self) -> str:
        """Return the ID used for the DOM element for this action.

        Returns:
            str:
            The ID used for the element.
        """
        return 'action-%s' % self.action_id

    def get_js_model_data(
        self,
        *,
        context: Context,
    ) -> SerializableDjangoJSONDict:
        """Return data to be passed to the JavaScript model.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of attributes to pass to the model instance.
        """
        dom_id = self.get_dom_element_id()
        icon_class = self.icon_class
        url = self.get_url(context=context)
        visible = self.get_visible(context=context)

        data: SerializableDjangoJSONDict = {
            'actionId': self.action_id,
            'visible': visible,
        }

        if dom_id:
            data['domID'] = dom_id

        if icon_class:
            data['iconClass'] = icon_class

        if self.is_custom_rendered():
            data['isCustomRendered'] = True

        if (label := self.get_label(context=context)):
            data['label'] = str(label)

        if (verbose_label := self.get_verbose_label(context=context)):
            data['verboseLabel'] = str(verbose_label)

        if url:
            data['url'] = url

        return data

    def get_js_view_data(
        self,
        *,
        context: Context,
    ) -> dict:
        """Return data to be passed to the JavaScript view.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of options to pass to the view instance.
        """
        return {}

    def get_label(
        self,
        *,
        context: Context,
    ) -> StrOrPromise | None:
        """Return the label for the action.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The label to use for the action.
        """
        return self.label

    def get_verbose_label(
        self,
        *,
        context: Context,
    ) -> StrOrPromise | None:
        """Return the verbose label for the action.

         This can be used to provide a longer label for wider UIs that would
         benefit from a more descriptive label. It's always optional.

         Version Added:
             7.1

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The verbose label to use for the action.
        """
        return self.verbose_label

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
        assert self.url_name or self.url

        if self.url_name:
            return local_site_reverse(self.url_name,
                                      request=context.get('request'))
        else:
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
    ) -> dict[str, Any]:
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
            'verbose_label': self.get_verbose_label(context=context),
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
            except Exception as e:
                logger.exception('Error rendering action "%r": %s',
                                 self, e)
            finally:
                context.pop()

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


class BaseGroupAction(BaseAction):
    """Base class for a group of actions.

    This can be used to group together actions in some form. Subclasses
    can implement this as menus, lists of actions, or in other
    presentational styles.

    Version Added:
        7.1
    """

    js_model_class = 'RB.Actions.GroupAction'

    #: An ordered list of child action IDs.
    #:
    #: This can be used to specify a specific order for children to appear in.
    #: The special string '--' can be used to add separators. Any children that
    #: are registered with this group as their parent but do not appear in this
    #: list will be added at the end of the group.
    children: Sequence[str] = []

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict:
        """Return extra template context for the action.

        This provides all the children that can be rendered in the group.

        Subclasses can override this to provide additional context.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.

        Raises:
            reviewboard.actions.errors.ActionError:
                There was an error retrieving data for the action.

                Details will be in the error message.
        """
        registry = self.parent_registry

        if not registry:
            raise ActionError(
                f'Attempted to call get_extra_context on {self!r} without '
                f'first being registered.'
            )

        extra_context = super().get_extra_context(request=request,
                                                  context=context)

        action_id = self.action_id
        assert action_id

        extra_context['children'] = [
            child
            for child in registry.get_children(action_id)
            if child.should_render(context=context)
        ]

        return extra_context

    def get_js_model_data(
        self,
        *,
        context: Context,
    ) -> dict:
        """Return data to be passed to the JavaScript model.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of attributes to pass to the model instance.

        Raises:
            reviewboard.actions.errors.ActionError:
                There was an error retrieving data for the action.

                Details will be in the error message.
        """
        registry = self.parent_registry

        if not registry:
            raise ActionError(
                f'Attempted to call get_js_model_data on {self!r} without '
                f'first being registered.'
            )

        action_id = self.action_id
        assert action_id is not None

        rendered_child_ids: dict[str, bool] = {
            child.action_id: True
            for child in registry.get_children(action_id)
            if child.action_id and child.should_render(context=context)
        }

        children: list[str] = []

        # Add in any children with explicit ordering first.
        for child_id in self.children:
            if child_id == '--':
                children.append(child_id)
            elif child_id in rendered_child_ids:
                children.append(child_id)
                del rendered_child_ids[child_id]

        # Now add any other actions that weren't in self.children.
        children += rendered_child_ids.keys()

        data = super().get_js_model_data(context=context)
        data['children'] = children

        return data


class BaseMenuAction(BaseGroupAction):
    """Base class for menu actions.

    Version Added:
        6.0
    """

    template_name = 'actions/menu_action.html'
    js_model_class = 'RB.Actions.MenuAction'
    js_view_class = 'RB.Actions.MenuActionView'

    def is_custom_rendered(self) -> bool:
        """Whether this menu action uses custom rendering.

        By default, this will return ``True`` if a custom template name is
        used. If the JavaScript side needs to override rendering, the subclass
        should explicitly return ``True``.

        Version Added:
            7.0

        Returns:
            bool:
            ``True`` if this action uses custom rendering. ``False`` if it
            does not.
        """
        return self.template_name != BaseMenuAction.template_name


if TYPE_CHECKING:
    BaseQuickAccessActionMixin = BaseAction
else:
    BaseQuickAccessActionMixin = object


class QuickAccessActionMixin(BaseQuickAccessActionMixin):
    """Mixin for creating a Quick Access button.

    Quick Access buttons are user-customizable actions placed in the Unified
    Banner's Quick Access hotbar location. They can be registered and made
    available to users who want them, working just like any standard action.

    This mixin can be used to create brand-new Quick Access actions, and
    can also be mixed in with an existing action to create a new Quick Access
    version of it.

    Quick Access actions are typically displayed as buttons. They must use
    the Quick Access attachment point and may not have a parent ID.
    """

    parent_id: (str | None) = None
    template_name = 'actions/button_action.html'
    attachment = AttachmentPoint.QUICK_ACCESS

    def get_js_model_data(
        self,
        *,
        context: Context,
    ) -> SerializableDjangoJSONDict:
        """Return data to be passed to the JavaScript model.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of attributes to pass to the model instance.
        """
        request = context['request']

        action_ids: set[str]

        # Fetch the list of enabled Quick Access action IDs once and convert
        # to a set for fast lookup across actions.
        try:
            action_ids = request._rb_quick_access_action_ids
        except AttributeError:
            try:
                action_ids = set(
                    request.user.get_profile()
                    .quick_access_actions
                )
            except Exception:
                # If anything goes wrong with fetching the profile or accessing
                # a setting, just ignore the actions entirely.
                action_ids = set()

            request._rb_quick_access_action_ids = action_ids

        data = super().get_js_model_data(context=context)
        data.update({
            'isQuickAccess': True,
            'isQuickAccessEnabled': self.action_id in action_ids,
        })

        return data
