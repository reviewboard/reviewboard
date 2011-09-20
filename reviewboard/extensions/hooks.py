from djblets.extensions.base import ExtensionHook, ExtensionHookPoint
import djblets.extensions.hooks as djblets_hooks


class DashboardHook(ExtensionHook):
    __metaclass__ = ExtensionHookPoint

    def get_entries(self):
        raise NotImplemented


class NavigationBarHook(ExtensionHook):
    """A hook for adding entries to the main navigation bar."""
    __metaclass__ = ExtensionHookPoint

    def get_entry(self):
        """Returns the entry to add to the navigation bar.

        This should be a dict with the following keys:

            * `label`: The label to display
            * `url`:   The URL to point to.
        """
        raise NotImplemented


class ReviewRequestDetailHook(ExtensionHook):
    __metaclass__ = ExtensionHookPoint

    def get_field_id(self):
        raise NotImplemented

    def get_label(self):
        raise NotImplemented

    def get_detail(self):
        raise NotImplemented

    def get_wide(self):
        """Returns whether or not this detail spans multiple columns."""
        return False


class ActionHook(ExtensionHook):
    def get_action_info(self, context):
        """Returns the action information for this action.

        This should be a dict with the following keys:

           * `id`:           The ID of this action (optional).
           * `image`:        The path to the image used for the icon (optional).
           * `image_width`:  The width of the image (optional).
           * `image_height`: The height of the image (optional).
           * `label`:        The label for the action.
           * `uri`:          The URI to invoke when the action is clicked.
                             This could be a javascript: URI.
        """
        raise NotImplemented


class ReviewRequestActionHook(ActionHook):
    """A hook for adding an action to the review request page."""
    __metaclass__ = ExtensionHookPoint


class ReviewRequestDropdownActionHook(ActionHook):
    """A hook for adding an drop down action to the review request page.

    The 'get_action_info' method for a drop down action should contain:

       * `id`:      The ID of this action (optional).
       * `title`:   The title of the dashboard select field.
       * `options`: A list of ActionHook-style dicts (see ActionHook params).

    For example::

        def get_action_info(self, context):
            'id': 'id 0',
            'title': 'Title',
            'options': [
                {
                    'id': 'id 1',
                    'label': 'Item 1',
                    'uri': 'javascript: ...',
                },
                {
                    'id': 'id 2',
                    'label': 'Item 2',
                    'uri': 'javascript: ...',
                }
            ]
    """
    __metaclass__ = ExtensionHookPoint


class DiffViewerActionHook(ActionHook):
    """A hook for adding an action to the diff viewer page."""
    __metaclass__ = ExtensionHookPoint


URLHook = djblets_hooks.URLHook
TemplateHook = djblets_hooks.TemplateHook
