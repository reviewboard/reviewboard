"""Base classes for actions.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, TYPE_CHECKING, cast

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from housekeeping import func_deprecated

from reviewboard.actions.errors import (ActionError,
                                        MissingActionRendererError)
from reviewboard.actions.renderers import (BaseActionGroupRenderer,
                                           BaseActionRenderer,
                                           ButtonActionRenderer,
                                           DefaultActionGroupRenderer,
                                           DefaultActionRenderer,
                                           MenuActionGroupRenderer)
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from django.http import HttpRequest
    from django.template import Context
    from django.utils.safestring import SafeString
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


class ActionAttachmentPoint:
    """An attachment point for a list of actions.

    Attachment points manage the display and registration of the UI side of
    actions. They may contain any number of pre-defined actions, and will
    automatically contain any actions dynamically registered to the attachment
    point.

    Actions rendered in an attachment point will use their own default
    renderer if specified, and fall back to the attachment point's default
    renderer. This order ensures that an attachment point may, for instance,
    default to buttons but that a menu button can still be added and rendered
    correctly.

    An attachment point can be registered in a central registry so that it
    can be referred to by name. It may also be unregisterd and passed directly
    to any templates that want to render the actions.

    To include an attachment point on a page, use the
    :py:func:`{% actions_html %}
    <reviewboard.actions.templatetags.actions.actions_html>` template tag.
    """

    ########################################
    # Instance-overridable class variables #
    ########################################

    #: The default action renderer used for child actions.
    #:
    #: This may be set on the class or passed when initializing an instance.
    #:
    #: This will be used for any actions that don't already have a default
    #: action renderer set. The action's default takes precedence in order
    #: to allow actions such as menus to manage their own display.
    default_action_renderer_cls: (type[BaseActionRenderer] | None) = \
        DefaultActionRenderer

    #: The unique ID for this attachment point.
    #:
    #: This may be set on the class or passed when initializing an instance.
    attachment_point_id: str

    #: A pre-defined list of action IDs to include on the attachment point.
    #:
    #: This may be set on the class or passed when initializing an instance.
    #:
    #: Any actions listed here will be listed first in the specified order.
    #: Any additional actions registered to this attachment point will be
    #: added after these actions.
    actions: (Sequence[str] | None) = None

    ######################
    # Instance variables #
    ######################

    #: The registry managing actions for this attachment point.
    #:
    #: This is primarily for unit test purposes.
    actions_registry: ActionsRegistry

    def __init__(
        self,
        attachment_point_id: (str | None) = None,
        *,
        actions: (Sequence[str] | None) = None,
        default_action_renderer_cls: (type[BaseActionRenderer] | None) = None,
        actions_registry: (ActionsRegistry | None) = None,
    ) -> None:
        """Initialize the attachment point.

        Args:
            attachment_point_id (str, optional):
                The unique ID for this attachment point.

                This must be provided if :py:attr:`attachment_point_id` is
                not already set.

            actions (list of str, optional):
                An explicit list of action IDs to include in this attachment
                point.

                Any actions listed here will be listed first in the
                specified order. Any additional actions registered to this
                attachment point will be added after these actions.

            default_action_renderer_cls (type, optional):
                The default action renderer used for child actions.

                This will be used for any actions that don't already have a
                default action renderer set. The action's default takes
                precedence in order to allow actions such as menus to manage
                their own display.

            actions_registry (reviewboard.actions.registry.ActionsRegistry,
                              optional):
                The registry managing actions for this attachment point.

                This is primarily for unit test purposes.
        """
        if attachment_point_id:
            self.attachment_point_id = attachment_point_id
        elif not getattr(self, 'attachment_point_id', None):
            raise AttributeError(
                'attachment_point_id must be provided as an argument or a '
                'class attribute.'
            )

        if actions is not None:
            self.actions = actions

        if default_action_renderer_cls is not None:
            self.default_action_renderer_cls = default_action_renderer_cls

        if not actions_registry:
            from reviewboard.actions import actions_registry

        assert actions_registry is not None
        self.actions_registry = actions_registry

    def iter_actions(
        self,
        *,
        include_children: bool = False,
    ) -> Iterator[BaseAction]:
        """Yield actions for this attachment point.

        Args:
            include_children (bool, optional):
                Whether to also include children of menus.

                If ``False`` (default), this will only yield the top-level
                items.

        Yields:
            reviewboard.actions.base.BaseAction:
            The actions for the given attachment point.
        """
        registered_actions = self.actions_registry.get_for_attachment(
            self.attachment_point_id,
            include_children=include_children,
        )

        # If there are any predefined order of actions, list those first.
        # Then list any registered actions after.
        if (actions := self.actions):
            actions_registry = self.actions_registry
            seen_actions: set[str] = set()

            for action_id in actions:
                action = actions_registry.get_action(action_id)

                if action is not None:
                    yield action
                else:
                    logger.warning(
                        'Attachment point "%s" referenced action "%s", but '
                        'that action was not registered.',
                        self.attachment_point_id, action_id)

                seen_actions.add(action_id)

            for action in registered_actions:
                if action.action_id not in seen_actions:
                    yield action
        else:
            # There are no predefined actions, so just return everything
            # registered at this attachment point.
            yield from registered_actions

    def get_js_view_data(
        self,
        *,
        context: Context,
    ) -> SerializableDjangoJSONDict:
        """Return additional data to be passed to the JavaScript view.

        This will be merged along with the data provided by the renderer.
        Any data in the renderer will take precedence over data returned
        by this method.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of attributes to pass to the model instance.
        """
        return {}

    def render(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> SafeString:
        """Render all actions in the attachment point.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            django.utils.safestring.SafeString:
            The rendered action HTML.
        """
        return mark_safe(''.join(self._iter_render(
            request=request,
            context=context,
        )))

    def render_js(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> SafeString:
        """Render the JavaScript for loading each action view in this point.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            django.utils.safestring.SafeString:
            The rendered action JavaScript.
        """
        return mark_safe(''.join(self._iter_render_js(
            request=request,
            context=context,
            actions=self.iter_actions(),
            default_renderer_cls=self.default_action_renderer_cls,
        )))

    def _iter_render(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> Iterator[SafeString]:
        """Generate HTML for each top-level action in the attachment point.

        This will iterate through all the top-level actions and render each
        to HTML, yielding each one-by-one.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Yields:
            django.utils.safestring.SafeString:
            Each rendered action HTML.
        """
        attachment_point_id = self.attachment_point_id
        default_renderer_cls = self.default_action_renderer_cls

        for action in self.iter_actions(include_children=False):
            placement = action.get_placement(attachment_point_id)
            renderer = action.get_renderer_cls(
                placement=placement,
                fallback_renderer_cls=default_renderer_cls,
            )

            try:
                yield action.render(
                    request=request,
                    context=context,
                    placement=placement,
                    renderer=renderer,
                )
            except Exception as e:
                logger.exception('Error rendering action %r: %s',
                                 action, e,
                                 extra={'request': request})

    def _iter_render_js(
        self,
        *,
        request: HttpRequest,
        context: Context,
        actions: Iterable[BaseAction],
        default_renderer_cls: type[BaseActionRenderer] | None,
    ) -> Iterator[SafeString]:
        """Generate JavaScript for each action in the attachment point.

        This will iterate through all the actions (top-level and children)
        and render each action's JavaScript view registration, yielding each
        one-by-one.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

            actions (list of BaseAction):
                The actions to iterate through.

            default_renderer_cls (type):
                The default renderer to use as a fallback.

        Yields:
            django.utils.safestring.SafeString:
            Each rendered action JavaScript.
        """
        attachment_point_id = self.attachment_point_id
        js_view_data = self.get_js_view_data(context=context)

        for action in actions:
            placement = action.get_placement(attachment_point_id)

            if not placement:
                continue

            renderer = action.get_renderer_cls(
                placement=placement,
                fallback_renderer_cls=default_renderer_cls,
            )

            try:
                yield action.render_js(
                    request=request,
                    context=context,
                    placement=placement,
                    renderer=renderer,
                    extra_js_view_data=js_view_data,
                )
            except Exception as e:
                logger.exception('Error rendering JavaScript for '
                                 'action %r: %s',
                                 action, e,
                                 extra={'request': request})

                continue

            # Render any children using the item renderer as the default.
            if (child_actions := placement.child_actions):
                if (renderer is not None and
                    issubclass(renderer, BaseActionGroupRenderer)):
                    child_default_renderer_cls = \
                        renderer.default_item_renderer_cls
                else:
                    child_default_renderer_cls = None

                yield from self._iter_render_js(
                    request=request,
                    context=context,
                    actions=child_actions,
                    default_renderer_cls=child_default_renderer_cls,
                )


class ActionPlacement:
    """Placement information for an action.

    This is used to specify where and how an action may be placed. This is
    mapped to a key specifying an attachment point ID, and can specify the
    parent action within the attachment point and a default renderer to use.

    Version Added:
        7.1
    """

    #: The attachment point for the action.
    attachment: str

    #: The list of child actions, if this is a grouped action.
    child_actions: list[BaseAction]

    #: The default renderer used for this action.
    #:
    #: By default, actions inherit their default renderer from a previous
    #: group or attachment point.
    #:
    #: Default renderes can always be overridden when rendering the action.
    default_renderer_cls: type[BaseActionRenderer] | None

    #: The DOM element ID for this element on the page.
    #:
    #: If not provided, an ID in the form of
    #: :samp:`action-{attachment}-{action_id}` will be used.
    dom_element_id: (str | None) = None

    #: The parent of this action, if this is an item in a group.
    parent_action: BaseGroupAction | None

    #: The ID of the parent action within the attachment point, if needed.
    #:
    #: This is used to build menus or groups of actions in part of the UI.
    parent_id: str | None

    def __init__(
        self,
        attachment: str,
        *,
        default_renderer_cls: (type[BaseActionRenderer] | None) = None,
        dom_element_id: (str | None) = None,
        parent_id: (str | None) = None,
    ) -> None:
        """Initialize the placement.

        Args:
            attachment (str):
                The attachment point ID to place the action in.

            default_renderer_cls (type, optional):
                The default renderer to use when rendering in this attachment
                point.

            dom_element_id (str, optional):
                A custom DOM element ID for the action in this attachment
                point.

            parent_id (str, optional):
                The parent ID of an action in this attachment point in which
                to place this action.
        """
        self.attachment = attachment
        self.default_renderer_cls = default_renderer_cls
        self.dom_element_id = dom_element_id
        self.parent_id = parent_id

        self.child_actions = []
        self.parent_action = None

    @property
    def depth(self) -> int:
        """The depth of the action in this placement.

        Type:
            int
        """
        if (parent_action := self.parent_action) is None:
            return 0
        else:
            return parent_action.depth + 1


class BaseAction:
    """Base class for actions.

    Version Changed:
        7.1:
        * A single action now can be placed in multiple attachment points
          via :py:attr:`placements`.

        * Actions now make use of renderer classes for rendering, instead
          of including rendering logic built-in.

        * Deprecated the attributes :py:attr:`attachment`,
          :py:attr:`js_view_class`, :py:attr:`parent_action`,
          :py:attr:`parent_id`, and :py:attr:`template_name`.

        * Deprecated the methods :py:meth:`get_js_view_data` and
          :py:meth:`is_custom_rendered`.

    Version Added:
        6.0
    """

    #: The internal ID of the action.
    #:
    #: This must be unique.
    #:
    #: Type:
    #:     str
    action_id: str

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
    #: Deprecated:
    #:     7.1:
    #:     This has been replaced by :py:attr:`placements`. This option
    #:     will be removed in Review Board 9.
    attachment: (str | None) = None

    #: The default renderer used for this action.
    #:
    #: By default, actions inherit their default renderer from a previous
    #: group or attachment point.
    #:
    #: Default renderers can always be overridden when rendering the action.
    #:
    #: Version Added:
    #:     7.1
    default_renderer_cls: (type[BaseActionRenderer] | None) = None

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

    #: The name of the template to use for registering action model JavaScript.
    js_template_name: str = 'actions/action.js'

    #: The class to instantiate for the JavaScript view.
    #:
    #: Deprecated:
    #:     7.1:
    #:     This should be set on the action's renderer instead.
    js_view_class: (str | None) = None

    #: The user-visible label.
    #:
    #: Type:
    #:     str
    label: (StrOrPromise | None) = None

    #: The IDs of any parent actions, if needed.
    #:
    #: Deprecated:
    #:     7.1:
    #:     This should be set in :py:attr:`placements` instead. This option
    #:     will be removed in Review Board 9.
    parent_id: (str | None) = None

    #: The placements of this action within the page.
    #:
    #: Each entry defines a placement within an attachment point and an
    #: action parent/child hierarchy where action should be rendered, along
    #: with options controlling the rendering.
    #:
    #: Version Added:
    #:     7.1
    placements: (Sequence[ActionPlacement] | None) = None

    #: The name of the template to use when rendering.
    #:
    #: Deprecated:
    #:     7.1:
    #:     This should be set on the action's renderer instead. This option
    #:     will be removed in Review Board 9.
    template_name: (str | None) = None

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

    #: The parent registry managing this action.
    #:
    #: Version Added:
    #:     7.1
    parent_registry: ActionsRegistry | None

    #: A cache of attachment point IDs to placement information.
    #:
    #: Version Added:
    #:     7.1
    _placement_cache: dict[str, ActionPlacement] | None

    def __init__(self) -> None:
        """Initialize the action."""
        cls = type(self)

        self.parent_registry = None
        self._placement_cache = None

        if not getattr(self, 'action_id', None):
            raise AttributeError(
                f'{cls.__name__}.action_id must be set.'
            )

        attachment = self.attachment
        parent_id = self.parent_id

        if hasattr(self, '_ignore_action_deprecations'):
            # This is a compatibility subclass. We don't want to check
            # the deprecations below.
            if not self.placements:
                self.placements = [
                    ActionPlacement(
                        attachment=(attachment or
                                    AttachmentPoint.REVIEW_REQUEST),
                        parent_id=parent_id),
                ]

            return

        # Check for deprecations.
        if attachment:
            RemovedInReviewBoard90Warning.warn(
                f'{type(self).__name__}.attachment is deprecated and '
                f'support will be removed in Review Board 9. Please set the '
                f'"placements" attribute instead.'
            )

            self.placements = [
                ActionPlacement(attachment=attachment,
                                parent_id=parent_id),
            ]
        elif not self.placements:
            self.placements = [
                ActionPlacement(attachment=AttachmentPoint.REVIEW_REQUEST,
                                parent_id=parent_id),
            ]

        if parent_id:
            RemovedInReviewBoard90Warning.warn(
                f'{type(self).__name__}.parent_id is deprecated and '
                f'support will be removed in Review Board 9. Please set this '
                f'attribute in "placements" instead.'
            )

        if self.template_name:
            RemovedInReviewBoard90Warning.warn(
                f'{cls.__name__}.template_name is deprecated and '
                f'support will be removed in Review Board 9. Please move any '
                f'custom rendering to a reviewboard.actions.renderers.'
                f'BaseActionRenderer subclass instead.'
            )

        if self.js_view_class:
            RemovedInReviewBoard90Warning.warn(
                f'{cls.__name__}.js_view_class is deprecated and '
                f'support will be removed in Review Board 9. Please move any '
                f'custom rendering to a reviewboard.actions.renderers.'
                f'BaseActionRenderer subclass instead.'
            )

        if cls.get_js_view_data is not BaseAction.get_js_view_data:
            RemovedInReviewBoard90Warning.warn(
                f'{cls.__name__}.get_js_view_data is deprecated and '
                f'support will be removed in Review Board 9. Please move any '
                f'custom rendering to a reviewboard.actions.renderers.'
                f'BaseActionRenderer subclass instead.'
            )

        if cls.get_dom_element_id is not BaseAction.get_dom_element_id:
            RemovedInReviewBoard90Warning.warn(
                f'{cls.__name__}.get_dom_element_id is deprecated and '
                f'support will be removed in Review Board 9.'
            )

    @property
    @func_deprecated(RemovedInReviewBoard90Warning, message=(
        '%(func_name)s is deprecated and support will be removed in '
        '%(product)s %(version)s. Please use ActionPlacement.parent_action '
        'instead.'
    ))
    def parent_action(self) -> BaseAction | None:
        """The parent of this action, if this is an item in a group.

        Deprecated:
            7.1:
            This has been replaced by
            :py:attr:`ActionPlacement.parent_action`. It will be removed in
            Review Board 9.
        """
        if (placements := self.placements):
            return placements[0].parent_action

        return None

    @property
    @func_deprecated(RemovedInReviewBoard90Warning, message=(
        '%(func_name)s is deprecated and support will be removed in '
        '%(product)s %(version)s. Please use ActionPlacement.child_actions '
        'instead.'
    ))
    def child_actions(self) -> Sequence[BaseAction]:
        """The children of this action, if this is a group.

        Deprecated:
            7.1:
            This has been replaced by
            :py:attr:`ActionPlacement.child_actions`. It will be removed in
            Review Board 9.
        """
        if (placements := self.placements):
            return placements[0].child_actions

        return []

    @property
    @func_deprecated(RemovedInReviewBoard90Warning, message=(
        '%(func_name)s is deprecated and support will be removed in '
        '%(product)s %(version)s. Please use ActionPlacement.depth '
        'instead.'
    ))
    def depth(self) -> int:
        """The depth of the action.

        Deprecated:
            7.1:
            This is scheduled for removal in Review Board 9. This has been
            replaced by :py:attr:`ActionPlacement.depth`.

        Type:
            int
        """
        if (placements := self.placements):
            return placements[0].depth

        return 0

    def get_placement(
        self,
        attachment_point_id: str,
    ) -> ActionPlacement:
        """Return the Placement for the action matching the attachment point.

        Version Added:
            7.1

        Args:
            attachment_point_id (str):
                The ID of the attachment point matching the placement.

        Returns:
            ActionPlacement:
            The Placement, or ``None`` if not found.

        Raises:
            KeyError:
                The attachment point ID is not a valid placement for this
                action.
        """
        placement_cache = self._placement_cache

        if placement_cache is None:
            placement_cache = {
                placement.attachment: placement
                for placement in self.placements or []
            }
            self._placement_cache = placement_cache

        try:
            return placement_cache[attachment_point_id]
        except KeyError:
            raise KeyError(
                f'"{attachment_point_id}" is not a valid placement for '
                f'action "{self.action_id}".'
            )

    def get_renderer_cls(
        self,
        *,
        placement: ActionPlacement | None,
        preferred_renderer_cls: (type[BaseActionRenderer] | None) = None,
        fallback_renderer_cls: (type[BaseActionRenderer] | None) = None,
    ) -> type[BaseActionRenderer] | None:
        """Return the renderer class used to render this action.

        This takes into account the attachment point, the preferred
        renderer from the caller, and the fallback if no suitable renderer
        is found.

        Version Added:
            7.1

        Args:
            placement (ActionPlacement):
                The placement where the action will be rendered.

            preferred_renderer_cls (type, optional):
                The preferred renderer for items.

                This will be used if provided, unless item isn't
                custom-rendered (a deprecated feature).

            fallback_renderer_cls (type, optional):
                The fallback renderer if the placement or action does not
                provide one.

        Returns:
            type:
            The renderer class, or ``None`` if one could not be determined.
        """
        if preferred_renderer_cls and not self.is_custom_rendered():
            return preferred_renderer_cls

        if placement is not None and placement.default_renderer_cls:
            return placement.default_renderer_cls

        return self.default_renderer_cls or fallback_renderer_cls

    def is_custom_rendered(self) -> bool:
        """Whether this action uses custom rendering.

        By default, this will return ``True`` if a custom template name is
        used. If the JavaScript side needs to override rendering, the subclass
        should explicitly return ``True``.

        Deprecated:
            7.1:
            This is scheduled for removal in Review Board 9. This was only
            ever used for menu items. Custom menu items should instead set
            the ``data-custom-rendered="true"`` attribute on the custom
            element.

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

        if ((apply_to := self.apply_to) and not
            (request.resolver_match and
             request.resolver_match.url_name in apply_to)):
            return False

        from reviewboard.extensions.hooks.actions import HideActionHook

        action_id = self.action_id

        for hook in HideActionHook.hooks:
            if action_id in hook.hidden_action_ids:
                return False

        return True

    def get_dom_element_id(self) -> str:
        """Return the ID used for the DOM element for this action.

        Deprecated:
            7.1:
            This is scheduled for removal in Review Board 9. This has been
            replaced by :py:attr:`ActionPlacement.dom_element_id`.

        Returns:
            str:
            The ID used for the element.
        """
        return ''

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
        icon_class = self.icon_class
        url = self.get_url(context=context)
        visible = self.get_visible(context=context)

        data: SerializableDjangoJSONDict = {
            'id': self.action_id,
            'visible': visible,
        }

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

        Deprecated:
            7.1:
            Actions implementing this should instead move to custom
            renderers.

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
        placement: (ActionPlacement | None) = None,
        renderer: (type[BaseActionRenderer] | None) = None,
        fallback_renderer: (type[BaseActionRenderer] | None) = None,
    ) -> SafeString:
        """Render the action.

        Version Changed:
            7.1:
            Added the ``extra_js_view_data``, ``fallback_renderer``,
            ``placement``, and ``renderer`` arguments.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

            placement (ActionPlacement, optional):
                The placement the action is being rendered into.

                If not added, the first will be used, with a warning.

                This argument will be required in Review Boad 9.

                Version Added:
                    7.1

            renderer (type, optional):
                The renderer used to render this action.

                If not specified, :py:attr:`default_renderer_cls` will be
                used.

                Version Added:
                    7.1

            fallback_renderer (type, optional):
                The renderer used to render this action if no other is found.

                Version Added:
                    7.1

        Returns:
            django.utils.safestring.SafeString:
            The rendered action HTML.

        Raises:
            TypeError:
                An invalid renderer class was provided.

            reviewboard.actions.errors.MissingActionRendererError:
                A renderer was not found or provided.
        """
        if not self.should_render(context=context):
            return mark_safe('')

        if placement is None:
            RemovedInReviewBoard90Warning.warn(
                f'{type(self).__name__}.render() must be passed a placement= '
                f'argument. This will be required in Review Board 9.'
            )

            if not (placements := self.placements):
                return mark_safe('')

            placement = placements[0]

        renderer_cls = self.get_renderer_cls(
            placement=placement,
            preferred_renderer_cls=renderer,
        )

        if renderer_cls is None:
            raise MissingActionRendererError(
                f'A renderer must be explicitly provided when rendering '
                f'action {type(self)!r}.'
            )

        if not issubclass(renderer_cls, BaseActionRenderer):
            raise TypeError(
                f'An invalid renderer class was provided ({renderer_cls!r}).'
            )

        if not self.should_render(context=context):
            return mark_safe('')

        return (
            renderer_cls(action=self,
                         placement=placement)
            .render(request=request,
                    context=context)
        )

    def render_model_js(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> SafeString:
        """Render the action's JavaScript model.

        This will set up the JavaScript model, registering it for use in
        views.

        Version Added:
            7.1

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            django.utils.safestring.SafeString:
            The rendered action JavaScript.
        """
        with context.push():
            try:
                context.update({
                    'action': self,
                    'js_model_class': self.js_model_class,
                })

                return render_to_string(
                    template_name=self.js_template_name,
                    context=cast(dict, context.flatten()),
                    request=request)
            except Exception as e:
                logger.exception('Error rendering JavaScript for action model '
                                 '%r: %s',
                                 self, e)

                return mark_safe('')

    def render_js(
        self,
        *,
        request: HttpRequest,
        context: Context,
        extra_js_view_data: (SerializableDjangoJSONDict | None) = None,
        placement: (ActionPlacement | None) = None,
        renderer: (type[BaseActionRenderer] | None) = None,
        fallback_renderer: (type[BaseActionRenderer] | None) = None,
    ) -> SafeString:
        """Render the action's JavaScript view.

        This will set up an instance of an action's view using either the
        provided renderer or the action's default renderer.

        Version Changed:
            7.1:
            Added the ``extra_js_view_data``, ``fallback_renderer``,
            ``placement``, and ``renderer`` arguments.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

            extra_js_view_data (dict, optional):
                Optional extra data to pass to the JavaScript action view's
                constructor.

                Version Added:
                    7.1

            placement (ActionPlacement, optional):
                The placement the action is being rendered into.

                If not added, the first will be used, with a warning.

                This argument will be required in Review Boad 9.

                Version Added:
                    7.1

            renderer (type, optional):
                The renderer used to render this action.

                If not specified, :py:attr:`default_renderer_cls` will be
                used.

                Version Added:
                    7.1

            fallback_renderer (type, optional):
                The renderer used to render this action if no other is found.

                Version Added:
                    7.1

        Returns:
            django.utils.safestring.SafeString:
            The rendered action JavaScript.

        Raises:
            TypeError:
                An invalid renderer class was provided.

            reviewboard.actions.errors.MissingActionRendererError:
                A renderer was not found or provided.
        """
        if not self.should_render(context=context):
            return mark_safe('')

        if placement is None:
            RemovedInReviewBoard90Warning.warn(
                f'{type(self).__name__}.render_js() must be passed a '
                f'placement= argument. This will be required in '
                f'Review Board 9.'
            )

            if not (placements := self.placements):
                return mark_safe('')

            placement = placements[0]

        renderer_cls = self.get_renderer_cls(
            placement=placement,
            preferred_renderer_cls=renderer,
        )

        if renderer_cls is None:
            raise MissingActionRendererError(
                f'A renderer must be explicitly provided when rendering '
                f'JavaScript for action {type(self)!r}.'
            )

        if not issubclass(renderer_cls, BaseActionRenderer):
            raise TypeError(
                f'An invalid renderer class was provided ({renderer_cls!r}).'
            )

        if not self.should_render(context=context):
            return mark_safe('')

        return (
            renderer_cls(action=self,
                         placement=placement)
            .render_js(request=request,
                       context=context,
                       extra_js_view_data=extra_js_view_data)
        )


class BaseGroupAction(BaseAction):
    """Base class for a group of actions.

    This can be used to group together actions in some form. Subclasses
    can implement this as menus, lists of actions, or in other
    presentational styles.

    Version Added:
        7.1
    """

    default_renderer_cls: (type[BaseActionRenderer] | None) = \
        DefaultActionGroupRenderer
    js_model_class = 'RB.Actions.GroupAction'

    #: An ordered list of child action IDs.
    #:
    #: This can be used to specify a specific order for children to appear in.
    #: The special string '--' can be used to add separators. Any children that
    #: are registered with this group as their parent but do not appear in this
    #: list will be added at the end of the group.
    children: Sequence[str] = []

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

        action_children = self.children
        placement_children: dict[str, list[str]] = {}

        for placement in (self.placements or []):
            # Note that we're using a dict here instead of a set in order to
            # maintain order.
            placement_child_ids: dict[str, bool] = {
                child.action_id: True
                for child in placement.child_actions
                if child.action_id and child.should_render(context=context)
            }

            children: list[str] = []

            # Add in any children with explicit ordering first.
            for child_id in action_children:
                if child_id == '--':
                    children.append(child_id)
                elif child_id in placement_child_ids:
                    children.append(child_id)
                    del placement_child_ids[child_id]

            # Now add any other actions that weren't in self.children.
            children += placement_child_ids.keys()

            placement_children[placement.attachment] = children

        data = super().get_js_model_data(context=context)
        data['children'] = placement_children

        return data


class BaseMenuAction(BaseGroupAction):
    """Base class for menu actions.

    Version Added:
        6.0
    """

    default_renderer_cls: (type[BaseActionRenderer] | None) = \
        MenuActionGroupRenderer
    js_model_class = 'RB.Actions.MenuAction'

    def is_custom_rendered(self) -> bool:
        """Whether this menu action uses custom rendering.

        By default, this will return ``True`` if a custom template name is
        used. If the JavaScript side needs to override rendering, the subclass
        should explicitly return ``True``.

        Deprecated:
            7.1:
            This is scheduled for removal in Review Board 9. This was only
            ever used for menu items. Custom menu items should instead set
            the ``data-custom-rendered="true"`` attribute on the custom
            element.

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
    template_name: (str | None) = None
    default_renderer_cls = ButtonActionRenderer
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
