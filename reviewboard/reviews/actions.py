from __future__ import unicode_literals

from collections import deque

from django.template.loader import render_to_string

from reviewboard.reviews.errors import DepthLimitExceededError


#: The maximum depth limit of any action instance.
MAX_DEPTH_LIMIT = 2

#: The mapping of all action IDs to their corresponding action instances.
_all_actions = {}

#: All top-level action IDs (in their left-to-right order of appearance).
_top_level_ids = deque()

#: Determines if the default action instances have been populated yet.
_populated = False


class BaseReviewRequestAction(object):
    """A base class for an action that can be applied to a review request.

    Creating an action requires subclassing :py:class:`BaseReviewRequestAction`
    and overriding any fields/methods as desired. Different instances of the
    same subclass can also override the class fields with their own instance
    fields.

    Example:
        .. code-block:: python

           class UsedOnceAction(BaseReviewRequestAction):
               action_id = 'once'
               label = 'This is used once.'

           class UsedMultipleAction(BaseReviewRequestAction):
               def __init__(self, action_id, label):
                   super(UsedMultipleAction, self).__init__()

                   self.action_id = 'repeat-' + action_id
                   self.label = 'This is used multiple times,'

    Note:
        Since the same action will be rendered for multiple different users in
        a multithreaded environment, the action state should not be modified
        after initialization. If we want different action attributes at
        runtime, then we can override one of the getter methods (such as
        :py:meth:`get_label`), which by default will simply return the original
        attribute from initialization.
    """

    #: The ID of this action. Must be unique across all types of actions and
    #: menu actions, at any depth.
    action_id = None

    #: The label that displays this action to the user.
    label = None

    #: The URL to invoke if this action is clicked.
    url = '#'

    #: Determines if this action should be initially hidden to the user.
    hidden = False

    def __init__(self):
        """Initialize this action.

        By default, actions are top-level and have no children.
        """
        self._parent = None
        self._max_depth = 0

    def copy_to_dict(self, context):
        """Copy this action instance to a dictionary.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            dict: The corresponding dictionary.
        """
        return {
            'action_id': self.action_id,
            'label': self.get_label(context),
            'url': self.get_url(context),
            'hidden': self.get_hidden(context),
        }

    def get_label(self, context):
        """Return this action's label.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            unicode: The label that displays this action to the user.
        """
        return self.label

    def get_url(self, context):
        """Return this action's URL.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            unicode: The URL to invoke if this action is clicked.
        """
        return self.url

    def get_hidden(self, context):
        """Return whether this action should be initially hidden to the user.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            bool: Whether this action should be initially hidden to the user.
        """
        return self.hidden

    def should_render(self, context):
        """Return whether or not this action should render.

        The default implementation is to always render the action everywhere.

        Args:
            context (django.template.Context):
                The collection of key-value pairs available in the template
                just before this action is to be rendered.

        Returns:
            bool: Determines if this action should render.
        """
        return True

    @property
    def max_depth(self):
        """Lazily compute the max depth of any action contained by this action.

        Top-level actions have a depth of zero, and child actions have a depth
        that is one more than their parent action's depth.

        Algorithmically, the notion of max depth is equivalent to the notion of
        height in the context of trees (from graph theory). We decided to use
        this term instead so as not to confuse it with the dimensional height
        of a UI element.

        Returns:
            int: The max depth of any action contained by this action.
        """
        return self._max_depth

    def reset_max_depth(self):
        """Reset the max_depth of this action and all its ancestors to zero."""
        self._max_depth = 0

        if self._parent:
            self._parent.reset_max_depth()

    def render(self, context, action_key='action',
               template_name='reviews/action.html'):
        """Render this action instance and return the content as HTML.

        Args:
            context (django.template.Context):
                The collection of key-value pairs that is passed to the
                template in order to render this action.

            action_key (unicode, optional):
                The key to be used for this action in the context map.

            template_name (unicode, optional):
                The name of the template to be used for rendering this action.

        Returns:
            unicode: The action rendered in HTML.
        """
        content = ''

        if self.should_render(context):
            context.push()

            try:
                context[action_key] = self.copy_to_dict(context)
                content = render_to_string(template_name, context)
            finally:
                context.pop()

        return content

    def register(self, parent=None):
        """Register this review request action instance.

        Note:
           Newly registered top-level actions are appended to the left of the
           other previously registered top-level actions. So if we intend to
           register a collection of top-level actions in a certain order, then
           we likely want to iterate through the actions in reverse.

        Args:
            parent (BaseReviewRequestMenuAction, optional):
                The parent action instance of this action instance.

        Raises:
            KeyError:
                A second registration is attempted (action IDs must be unique
                across all types of actions and menu actions, at any depth).

            DepthLimitExceededError:
                The maximum depth limit is exceeded.
        """
        _populate_defaults()

        if self.action_id in _all_actions:
            raise KeyError('%s already corresponds to a registered review '
                           'request action' % self.action_id)

        if self.max_depth > MAX_DEPTH_LIMIT:
            raise DepthLimitExceededError(self.action_id, MAX_DEPTH_LIMIT)

        if parent:
            parent.child_actions.append(self)
            self._parent = parent
        else:
            _top_level_ids.appendleft(self.action_id)

        _all_actions[self.action_id] = self

    def unregister(self):
        """Unregister this review request action instance.

        Note:
           This method can mutate its parent's child actions. So if we are
           iteratively unregistering a parent's child actions, then we should
           consider first making a clone of the list of children.

        Raises:
            KeyError: An unregistration is attempted before it's registered.
        """
        _populate_defaults()

        try:
            del _all_actions[self.action_id]
        except KeyError:
            raise KeyError('%s does not correspond to a registered review '
                           'request action' % self.action_id)

        if self._parent:
            self._parent.child_actions.remove(self)
        else:
            _top_level_ids.remove(self.action_id)

        self.reset_max_depth()


class BaseReviewRequestMenuAction(BaseReviewRequestAction):
    """A base class for an action with a dropdown menu.

    Note:
        A menu action's child actions must always be pre-registered.
    """

    def __init__(self, child_actions=None):
        """Initialize this menu action.

        Args:
            child_actions (list of BaseReviewRequestAction, optional):
                The list of child actions to be contained by this menu action.

        Raises:
            KeyError:
                A second registration is attempted (action IDs must be unique
                across all types of actions and menu actions, at any depth).

            DepthLimitExceededError:
                The maximum depth limit is exceeded.
        """
        super(BaseReviewRequestMenuAction, self).__init__()

        self.child_actions = []
        child_actions = child_actions or []

        for child_action in child_actions:
            child_action.register(self)

    def copy_to_dict(self, context):
        """Copy this menu action instance to a dictionary.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            dict: The corresponding dictionary.
        """
        dict_copy = {
            'child_actions': self.child_actions,
        }
        dict_copy.update(super(BaseReviewRequestMenuAction, self).copy_to_dict(
            context))

        return dict_copy

    @property
    def max_depth(self):
        """Lazily compute the max depth of any action contained by this action.

        Returns:
            int: The max depth of any action contained by this action.
        """
        if self.child_actions and self._max_depth == 0:
            self._max_depth = 1 + max(child_action.max_depth
                                      for child_action in self.child_actions)

        return self._max_depth

    def render(self, context, action_key='menu_action',
               template_name='reviews/menu_action.html'):
        """Render this menu action instance and return the content as HTML.

        Args:
            context (django.template.Context):
                The collection of key-value pairs that is passed to the
                template in order to render this menu action.

            action_key (unicode, optional):
                The key to be used for this menu action in the context map.

            template_name (unicode, optional):
                The name of the template to be used for rendering this menu
                action.

        Returns:
            unicode: The action rendered in HTML.
        """
        return super(BaseReviewRequestMenuAction, self).render(
            context, action_key, template_name)

    def unregister(self):
        """Unregister this review request action instance.

        This menu action recursively unregisters its child action instances.

        Raises:
            KeyError: An unregistration is attempted before it's registered.
        """
        super(BaseReviewRequestMenuAction, self).unregister()

        # Unregistration will mutate self.child_actions, so we make a copy.
        for child_action in list(self.child_actions):
            child_action.unregister()


# TODO: Convert all this to use djblets.registries.
def _populate_defaults():
    """Populate the default action instances."""
    global _populated

    if not _populated:
        _populated = True

        from reviewboard.reviews.default_actions import get_default_actions

        for default_action in reversed(get_default_actions()):
            default_action.register()


def get_top_level_actions():
    """Return a generator of all top-level registered action instances.

    Yields:
        BaseReviewRequestAction:
        All top-level registered review request action instances.
    """
    _populate_defaults()

    return (_all_actions[action_id] for action_id in _top_level_ids)


def register_actions(actions, parent_id=None):
    """Register the given actions as children of the corresponding parent.

    If no parent_id is given, then the actions are assumed to be top-level.

    Args:
        actions (iterable of BaseReviewRequestAction):
            The collection of action instances to be registered.

        parent_id (unicode, optional):
            The action ID of the parent of each action instance to be
            registered.

    Raises:
        KeyError:
            The parent action cannot be found or a second registration is
            attempted (action IDs must be unique across all types of actions
            and menu actions, at any depth).

        DepthLimitExceededError:
            The maximum depth limit is exceeded.
    """
    _populate_defaults()

    if parent_id is None:
        parent = None
    else:
        try:
            parent = _all_actions[parent_id]
        except KeyError:
            raise KeyError('%s does not correspond to a registered review '
                           'request action' % parent_id)

    for action in reversed(actions):
        action.register(parent)

    if parent:
        parent.reset_max_depth()


def unregister_actions(action_ids):
    """Unregister each of the actions corresponding to the given IDs.

    Args:
        action_ids (iterable of unicode):
            The collection of action IDs corresponding to the actions to be
            removed.

    Raises:
        KeyError: An unregistration is attempted before it's registered.
    """
    _populate_defaults()

    for action_id in action_ids:
        try:
            action = _all_actions[action_id]
        except KeyError:
            raise KeyError('%s does not correspond to a registered review '
                           'request action' % action_id)

        action.unregister()


def clear_all_actions():
    """Clear all registered actions.

    This method is really only intended to be used by unit tests. We might be
    able to remove this hack once we convert to djblets.registries.

    Warning:
        This will clear **all** actions, even if they were registered in
        separate extensions.
    """
    global _populated

    _all_actions.clear()
    _top_level_ids.clear()
    _populated = False
