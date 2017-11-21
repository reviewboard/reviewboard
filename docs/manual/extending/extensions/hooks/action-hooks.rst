.. _action-hooks:
.. _action-hook:

============
Action Hooks
============

There are a variety of action hooks, which allow injecting clickable actions
into various parts of the UI.

:py:mod:`reviewboard.extensions.hooks` contains the following hooks:

+-------------------------------------+-----------------------------------+
| Class                               | Location                          |
+=====================================+===================================+
| :py:class:`ReviewRequestActionHook` | The bar at the top of a review    |
|                                     | request (containing "Close",      |
|                                     | "Update", etc.)                   |
+-------------------------------------+-----------------------------------+
| :py:class:`DiffViewerActionHook`    | Like the ReviewRequestActionHook, |
|                                     | but limited to the diff viewer    |
|                                     | page.                             |
+-------------------------------------+-----------------------------------+
| :py:class:`HeaderActionHook`        | An action in the page header.     |
+-------------------------------------+-----------------------------------+

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
    **image**: The path to the image used for the icon (optional).

*
    **image_width**: The width of the image (optional).

*
    **image_height**: The height of the image (optional).

There are also two hooks to provide drop-down menus in the action bars:

+---------------------------------------------+-------------------------+
| Class                                       | Location                |
+=============================================+=========================+
| :py:class:`ReviewRequestDropdownActionHook` | The bar at the top of a |
|                                             | review request.         |
+---------------------------------------------+-------------------------+
| :py:class:`HeaderDropdownActionHook`        | The page header.        |
+---------------------------------------------+-------------------------+

These work like the basic ActionHooks, except instead of a **url** field, they
contain an **items** field which is another list of dictionaries. Only one
level of nesting is possible.


Example
=======

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
