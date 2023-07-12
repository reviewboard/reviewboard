"""Extension hooks for managing actions."""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.registries.errors import ItemLookupError

from reviewboard.actions import (AttachmentPoint,
                                 BaseAction,
                                 BaseMenuAction,
                                 actions_registry)
from reviewboard.deprecation import RemovedInReviewBoard70Warning
from reviewboard.urls import (diffviewer_url_names,
                              main_review_request_url_name)


logger = logging.getLogger(__name__)


class ActionHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for injecting clickable actions into the UI.

    Actions are displayed either on the action bar of each review request or in
    the page header.

    The provided ``actions`` parameter must be a list of actions. These are
    subclasses of :py:class:`reviewboard.actions.base.BaseAction`.
    """

    #: The actions registered by this hook.
    actions: List[BaseAction]

    def initialize(
        self,
        actions: Optional[List[BaseAction]] = None,
        *args,
        **kwargs,
    ) -> None:
        """Initialize this action hook.

        Args:
            actions (list of reviewboard.actions.base.BaseAction, optional):
                The list of actions to be added.

            *args (tuple):
                Extra positional arguments.

            **kwargs (dict):
                Extra keyword arguments.
        """
        self.actions = actions or []

        for action in self.actions:
            actions_registry.register(action)

    def shutdown(self) -> None:
        """Shut down the hook."""
        super().shutdown()

        for action in self.actions:
            try:
                actions_registry.unregister(action)
            except ItemLookupError:
                pass

    def get_actions(self, context):
        """Return the list of action information for this action hook.

        Args:
            context (django.template.Context):
                The collection of key-value pairs available in the template.

        Returns:
            list: The list of action information for this action hook.
        """
        return self.actions


class _DictAction(BaseAction):
    """An action for legacy dictionary-based actions.

    For backwards compatibility, review request actions may also be supplied as
    :py:class:`ActionHook`-style dictionaries. This helper class is used by
    :py:meth:`convert_action` to convert these types of dictionaries into
    instances of :py:class:`reviewboard.actions.base.BaseAction`.
    """

    def __init__(self, action_dict, applies_to, attachment):
        """Initialize this action.

        Args:
            action_dict (dict):
                A dictionary representing this action, as specified by the
                :py:class:`ActionHook` class.

            applies_to (callable):
                The list of URLs to apply the action to.

            attachment (reviewboard.actions.base.AttachmentPoint):
                The attachment point for the action.
        """
        super().__init__()

        if not isinstance(action_dict, dict):
            raise ValueError('Action definitions must be dictionaries.')

        self.label = action_dict['label']

        if 'id' in action_dict:
            self.action_id = action_dict['id']
        else:
            self.action_id = re.sub(
                r'[^a-zA-Z0-9]+',
                '-',
                self.label.lower())

        self.url = action_dict['url']
        self.apply_to = applies_to
        self.attachment = attachment

        if 'image' in action_dict:
            self.image = action_dict['image']
            self.image_width = action_dict['image_width']
            self.image_height = action_dict['image_height']

    def get_dom_element_id(self) -> str:
        """Return the ID used for the DOM element for this action.

        Returns:
            str:
            The ID used for the element.
        """
        # We use this instead of the new style (action-*) in order to maintain
        # compatibility with the old implementation.
        return '%s-action' % self.action_id


class _DictMenuAction(BaseMenuAction):
    """A menu action for legacy dictionary-based menu actions.

    For backwards compatibility, review request actions may also be supplied as
    :py:class:`ReviewRequestDropdownActionHook`-style dictionaries. This helper
    class is used by :py:meth:`convert_action` to convert these types of
    dictionaries into instances of
    :py:class:`reviewboard.actions.base.BaseMenuAction`.
    """

    def __init__(self, action_dict, applies_to, attachment):
        """Initialize this action.

        Args:
            action_dict (dict):
                A dictionary representing this menu action, as specified by the
                :py:class:`ReviewRequestDropdownActionHook` class.

            applies_to (list of str):
                The list of URLs to apply the action to.

            attachment (reviewboard.actions.base.AttachmentPoint):
                The attachment point for the action.
        """
        super().__init__()

        if not isinstance(action_dict, dict):
            raise ValueError('Action definitions must be dictionaries.')

        self.label = action_dict['label']

        if 'id' in action_dict:
            self.action_id = action_dict['id']
        else:
            self.action_id = re.sub(
                r'[^a-zA-Z0-9]*',
                '-',
                self.label.lower())

        self.apply_to = applies_to
        self.attachment = attachment


class BaseReviewRequestActionHook(ActionHook, metaclass=ExtensionHookPoint):
    """A base hook for adding review request actions to the action bar.

    Review request actions are displayed on the action bar (alongside default
    actions such as :guilabel:`Download Diff` and :guilabel:`Ship It!`) of each
    review request.
    """

    attachment = AttachmentPoint.REVIEW_REQUEST

    def initialize(self, actions=[], apply_to=None, *args, **kwargs):
        """Initialize this action hook.

        Args:
            actions (list of dict, optional):
                The list of actions to be added.

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
        """
        self.applies_to = apply_to
        super().initialize(
            actions=[
                self.convert_action(action_dict)
                for action_dict in actions
            ], *args, **kwargs)

    def convert_action(self, action_dict):
        """Convert the given dictionary to a review request action instance.

        Args:
            action_dict (dict):
                A dictionary representing a review request action, as specified
                by the :py:class:`ActionHook` class.

        Returns:
            reviewboard.actions.base.BaseAction:
            The corresponding review request action instance.

        Raises:
            KeyError:
                The given dictionary does not have the correct fields.

            ValueError:
                A given action was not a dictionary.
        """
        if not isinstance(action_dict, dict):
            raise ValueError('Action definitions must be dictionaries.')

        for key in ('label', 'url'):
            if key not in action_dict:
                raise KeyError('Action dictionaries require a %s key'
                               % repr(key))

        return _DictAction(action_dict, self.applies_to, self.attachment)


class ReviewRequestActionHook(BaseReviewRequestActionHook,
                              metaclass=ExtensionHookPoint):
    """A hook for adding review request actions to review request pages.

    By default, actions that are passed into this hook will only be displayed
    on review request pages and not on any file attachment pages or diff
    viewer pages.

    This hook is deprecated. New extensions should use
    :py:class:`reviewboard.extensions.hooks.ActionHook`.

    The provided ``actions`` parameter must be a list of actions. Each action
    must be a :py:class:`dict` with the following keys:

    ``id`` (:py:class:`str`, optional):
        The ID to use for the action.

    ``label`` (:py:class:`str`):
        The label to use for the action.

    ``url`` (:py:class:`str`):
        The URL to link the action to.

        If you want to use JavaScript to handle the action, this should be
        ``"#"`` and you should attach a handler to the element specified by
        the "#action-<id>" selector.
    """

    def initialize(self, actions=[], apply_to=None):
        """Initialize this action hook.

        Args:
            actions (list of dict, optional):
                The list of actions to be added.

            apply_to (list of unicode, optional):
                The list of URL names that this action hook will apply to.
                By default, this will apply to the main review request page
                only.

        Raises:
            KeyError:
                Some dictionary is not an :py:class:`ActionHook`-style
                dictionary.
        """
        if apply_to is None:
            apply_to = [main_review_request_url_name]

        super().initialize(actions=actions, apply_to=apply_to)

        RemovedInReviewBoard70Warning.warn(
            'ReviewRequestActionHook is deprecated and will be removed in '
            'Review Board 7.0. Your extension "%s" will need to be updated to '
            'derive actions from reviewboard.actions.BaseAction and use '
            'ActionHook.'
            % self.extension.id)


class ReviewRequestDropdownActionHook(ActionHook,
                                      metaclass=ExtensionHookPoint):
    """A hook for adding dropdown menu actions to review request pages.

    This hook is deprecated. New extensions should use
    :py:class:`reviewboard.extensions.hooks.ActionHook`.

    The provided ``actions`` parameter must be a list of actions. Each action
    must be a :py:class:`dict` with the following keys:

    ``id`` (:py:class:`str`, optional):
        The ID to use for the action.

    ``label`` (:py:class:`str`):
        The label to use for the action.

    ''items`` (:py:class:`list`):
        A list of items, each of which is a :py:class:`dict` which follows the
        conventions for :py:class:`ReviewRequestActionHook`.

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

    attachment = AttachmentPoint.REVIEW_REQUEST

    def initialize(self, actions=[], apply_to=None):
        """Initialize this action hook.

        Args:
            actions (list of dict, optional):
                The list of actions to be added.

            apply_to (list of unicode, optional):
                The list of URL names that this action hook will apply to.
                By default, this will apply to the main review request page
                only.

        Raises:
            KeyError:
                Some dictionary is not an :py:class:`ActionHook`-style
                dictionary.
        """
        converted_actions = []

        if actions is None:
            actions = []

        for action_dict in actions:
            action = _DictMenuAction(action_dict, apply_to, self.attachment)
            converted_actions.append(action)

            for child in action_dict['items']:
                child_action = _DictAction(child, apply_to, self.attachment)
                child_action.parent_id = action.action_id

                converted_actions.append(child_action)

        super().initialize(actions=converted_actions)

        RemovedInReviewBoard70Warning.warn(
            'ReviewRequestDropdownActionHook is deprecated and will be '
            'removed in Review Board 7.0. Your extension "%s" will need to be '
            'updated to derive actions from reviewboard.actions.BaseAction '
            'and use ActionHook.'
            % self.extension.id)


class DiffViewerActionHook(BaseReviewRequestActionHook,
                           metaclass=ExtensionHookPoint):
    """A hook for adding review request actions to diff viewer pages.

    By default, actions that are passed into this hook will only be displayed
    on diff viewer pages and not on any review request pages or file attachment
    pages.

    This hook is deprecated. New extensions should use
    :py:class:`reviewboard.extensions.hooks.ActionHook`.
    """

    def initialize(self, actions=[], apply_to=diffviewer_url_names):
        """Initialize this action hook.

        Args:
            actions (list of dict, optional):
                The list of actions to be added.

            apply_to (list of unicode, optional):
                The list of URL names that this action hook will apply to.

        Raises:
            KeyError:
                Some dictionary is not an :py:class:`ActionHook`-style
                dictionary.
        """
        super().initialize(
            actions,
            apply_to=apply_to or diffviewer_url_names)

        RemovedInReviewBoard70Warning.warn(
            'DiffViewerActionHook is deprecated and will be removed in '
            'Review Board 7.0. Your extension "%s" will need to be updated to '
            'derive actions from reviewboard.actions.BaseAction and use '
            'ActionHook.'
            % self.extension.id)


class HeaderActionHook(BaseReviewRequestActionHook,
                       metaclass=ExtensionHookPoint):
    """A hook for adding actions to the page header.

    This hook is deprecated. New extensions should use
    :py:class:`reviewboard.extensions.hooks.ActionHook`.

    The provided ``actions`` parameter must be a list of actions. Each action
    must be a :py:class:`dict` with the following keys:

    ``id`` (:py:class:`str`, optional):
        The ID to use for the action.

    ``label`` (:py:class:`str`):
        The label to use for the action.

    ``url`` (:py:class:`str`):
        The URL to link the action to.

        If you want to use JavaScript to handle the action, this should be
        ``"#"`` and you should attach a handler to the element specified by
        the "#action-<id>" selector.

    ``image`` (:py:class:`str`):
        The URL to an image to display next to the label.

    ``image_width`` (:py:class:`int`):
        The width of the image, if present.

    ``image_height`` (:py:class:`int`):
        The height of the image, if present.
    """

    attachment = AttachmentPoint.HEADER

    def __init__(self, *args, **kwargs):
        """Initialize the hook.

        Args:
            *args (tuple):
                Positional arguments to pass through to the superclass.

            **kwargs (dict):
                Keyword arguments to pass through to the superclass.
        """
        super().__init__(*args, **kwargs)
        RemovedInReviewBoard70Warning.warn(
            'HeaderActionHook is deprecated and will be removed in Review '
            'Board 7.0. Your extension "%s" will need to be updated to derive '
            'actions from reviewboard.actions.BaseAction and use ActionHook.'
            % self.extension.id)

    def convert_action(self, action_dict):
        """Convert the given dictionary to na action instance.

        Args:
            action_dict (dict):
                A dictionary representing a header action.

        Returns:
            BaseReviewRequestMenuAction:
            The corresponding review request menu action instance.
        """
        action = super().convert_action(action_dict)

        if 'image' in action_dict:
            action.template_name = 'extensions/header_action_with_image.html'

        return action


class HeaderDropdownActionHook(ActionHook,
                               metaclass=ExtensionHookPoint):
    """A hook for adding dropdown menu actions to the page header.

    This hook is deprecated. New extensions should use
    :py:class:`reviewboard.extensions.hooks.ActionHook`.

    The provided ``actions`` parameter must be a list of actions. Each action
    must be a :py:class:`dict` with the following keys:

    ``id`` (:py:class:`str`, optional):
        The ID to use for the action.

    ``label`` (:py:class:`str`):
        The label to use for the action.

    ``items`` (:py:class:`list`):
        A list of items, each of which is a :py:class:`dict` which follows the
        conventions for :py:class:`HeaderActionHook`.
    """

    attachment = AttachmentPoint.HEADER

    def initialize(self, actions=[], *args, **kwargs):
        """Initialize the hook.

        Args:
            actions (list of dict, optional):
                The list of actions to be added.

            *args (tuple):
                Positional arguments to pass through to the superclass.

            **kwargs (dict):
                Keyword arguments to pass through to the superclass.
        """
        converted_actions = []

        if actions is None:
            actions = []

        for action_dict in actions:
            action = _DictMenuAction(action_dict, None, self.attachment)
            converted_actions.append(action)

            for child in action_dict['items']:
                child_action = _DictAction(child, None, self.attachment)
                child_action.parent_id = action.action_id

                converted_actions.append(child_action)

        super().initialize(actions=converted_actions)

        RemovedInReviewBoard70Warning.warn(
            'HeaderDropdownActionHook is deprecated and will be removed in '
            'Review Board 7.0. Your extension "%s" will need to be updated to '
            'derive actions from reviewboard.actions.BaseAction and use '
            'ActionHook.'
            % self.extension.id)


class HideActionHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for hiding built-in actions.

    Extensions may want to replace bulit-in functionality with their own custom
    versions, or disable some things entirely (such as the quick ship-it
    button).
    """

    #: The list of action IDs hidden by this hook.
    hidden_action_ids: List[str]

    def initialize(
        self,
        action_ids: List[str],
        *args,
        **kwargs,
    ) -> None:
        """Initialize the hook.

        Args:
            action_ids (list of str):
                The list of action IDs to hide.

            *args (tuple):
                Extra positional arguments.

            **kwargs (dict):
                Extra keyword arguments.
        """
        self.hidden_action_ids = action_ids
