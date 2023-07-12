.. _action-hooks:
.. _action-hook:

============
Action Hooks
============

Starting in Review Board 6.0, all actions throughout the application are based
on :py:class:`~reviewboard.actions.base.BaseAction`. This provides a simple
interface for basic actions that just have a label or link to another page, but
can be extended significantly for custom rendering or client-side behavior
written in JavaScript.

To add new actions to the Review Board UI, you'll add new subclasses of this,
and then use :py:class:`~reviewboard.extensions.hooks.ActionHook` to register
them.

You can also create menu actions by subclassing
:py:class:`~reviewboard.actions.base.BaseMenuAction`.


Subclassing BaseAction
======================

:py:class:`~reviewboard.actions.base.BaseAction` includes a number of
attributes which can be overridden:

*
    **action_id**: The ID of the action. This must be unique to your action.

*
    **parent_id**: For menu items, the ID of the parent menu action.

*
    **label**: A user-visible label for the action.

*
    **url**: A URL to link to for the action. The default is ``'#'``, which
    enables handling the action via JavaScript.

*
    **visible**: Whether the action should be shown by default.

*
    **apply_to**: A list of URL names where the action should appear.

*
    **attachment**: The location in the page where the action should be
    attached. Built-in attachment points can be found in
    :py:class:`reviewboard.actions.base.AttachmentPoint`. You can also define
    your own attachment points by setting this to a unique string and then
    using the :py:func:`~reviewboard.actions.templatetags.actions.actions_html`
    template tag.

*
    **template_name**: The name of the template file to use for rendering the
    action.

*
    **js_template_name**: The name of the template file to use for rendering
    the JavaScript side of the actions.

*
    **js_model_class**: The class of the JavaScript model to instantiate for
    the action. By default this just uses a stub model with no functionality.

*
    **js_view_class**: The class of the JavaScript view to instantiate for
    the action. By default this just uses a stub view with no functionality.


There are also several methods which may be overridden:

*
    **should_render**: Returns whether the action should render at all. This is
    different from **visible** in that non-visible actions will still render
    but will be hidden with CSS, whereas if this returns ``False`` the action
    will not render at all.

*
    **get_js_model_data**: Returns a dict of data to pass in to the JavaScript
    model.

*
    **get_js_view_data**: Returns a dict of data to pass in to the JavaScript
    view.

*
    **get_label**: Returns the label to use. By default this will just return
    the ``label`` attribute, but may be overridden to implement with logic.

*
    **get_url**: Returns the URL to use. By default this will just return
    the ``url`` attribute, but may be overridden to implement with logic.

*
    **get_visible**: Returns whether the action should be visible on the page.

*
    **get_extra_context**: Returns a dict of data to use when rendering the
    template.


Example
-------

.. code-block:: python

    from reviewboard.actions import BaseAction, BaseMenuAction
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ActionHook

    class SampleHeaderMenu(BaseMenuAction):
        action_id = 'header-dropdown'
        label = 'Header Dropdown'
        attachment = AttachmentPoint.HEADER

    class SampleHeaderAction(BaseAction):
        action_id = 'header-item'
        label = 'Header Item'
        attachment = AttachmentPoint.HEADER
        parent_id = 'header-dropdown'
        url = 'https://example.com/'

    class SampleReviewRequestAction(BaseAction):
        action_id = 'review-request-item-1'
        label = 'Item 1'

        # JavaScript view that handles clicks on the action.
        js_view_class = 'MyExtension.ActionView'

        def should_render(self, context) -> bool:
            # We only render this action for logged-in-users.
            request = context['request']
            return request.user.is_authenticated

    class SampleExtension(Extension):
        js_bundles = {
            'default': {
                'source_filenames': (
                    'js/actionView.es6.js',
                ),
            },
        }

        def initialize(self) -> None:
            ActionHook(self, actions=[
                SampleHeaderMenu(),
                SampleHeaderAction(),
                SampleReviewRequestAction(),
            ])


For the JavaScript:

.. code-block:: javascript

    class ActionView extends RB.ActionView {
        events() {
            return {
                'click': '_onClick',
            }
        }

        _onClick() {
            // Perform some action.
        }
    }

    MyExtension = {
        ActionView,
    }


.. _hide-action-hook:

Hiding Standard Actions
=======================

In some cases, you may want your extension to hide built-in actions. This
can be used to remove unwanted functionality, or to hide the defaults so you
can replace them with your own custom behavior.

Simply initialize the hook with a list of the
:py:attr:`~reviewboard.actions.baseBaseAction.action_id` of the actions that
you want to hide.


Example
-------

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import HideActionHook

    class SampleExtension(Extension):
        def initialize(self) -> None:
            HideActionHook(self, action_ids=['support-menu'])


Legacy Action Hooks
===================

Prior to Review Board 6.0, there were separate hooks for injecting
clickable actions into various parts of the UI. These are deprecated and will
be removed in Review Board 7.

:py:mod:`reviewboard.extensions.hooks` contains the following hooks:

.. autosummary::

   ~reviewboard.extensions.hooks.ReviewRequestActionHook
   ~reviewboard.extensions.hooks.DiffViewerActionHook
   ~reviewboard.extensions.hooks.HeaderActionHook


When instantiating any of these, you can pass a list of dictionaries defining
the actions you'd like to insert. These dictionaries have the following fields:

*
    **id**: The ID of the action (optional)

*
    **label**: The label for the action.

*
    **url**: The URI to invoke when the action is clicked. If you want to
    invoke a javascript action, this should be '#', and you should use a
    selector on the **id** field to attach the handler (as opposed to a
    javascript: URL, which doesn't work on all browsers).

*
    **image**: The path to the image used for the icon (optional). This is only
    used for header actions.

*
    **image_width**: The width of the image (optional). This is only used for
    header actions.

*
    **image_height**: The height of the image (optional). This is only used for
    header actions.

There are also two hooks to provide drop-down menus in the action bars:


.. autosummary::

   ~reviewboard.extensions.hooks.ReviewRequestDropdownActionHook
   ~reviewboard.extensions.hooks.HeaderDropdownActionHook

These work like the basic ActionHooks, except instead of a **url** field, they
contain an **items** field which is another list of dictionaries. Only one
level of nesting is possible.


Example
-------

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import (HeaderDropdownActionHook,
                                              ReviewRequestActionHook)


    class SampleExtension(Extension):
        def initialize(self):
            # Single entry on review requests, consumed from JavaScript.
            ReviewRequestActionHook(self, actions=[
                {
                    'id': 'sample-item',
                    'label': 'Review Request Item',
                    'url': '#',
                },
            ])

            # A drop-down in the header that links to other pages.
            HeaderDropdownActionHook(self, actions=[
                {
                    'label': 'Header Dropdown',
                    'items': [
                        {
                            'label': 'Item 1',
                            'url': '...',
                        },
                        {
                            'label': 'Item 2',
                            'url': '...',
                        },
                    ],
                },
            ])
