.. _action-hook:
.. _action-hooks:

==========
ActionHook
==========

Extensions can make use of a variety of action hooks in order to inject
clickable actions into various parts of the UI.

The :py:mod:`reviewboard.extensions.hooks` module contains the following hooks:

.. autosummary::

   ~reviewboard.extensions.hooks.ActionHook
   ~reviewboard.extensions.hooks.BaseReviewRequestActionHook
   ~reviewboard.extensions.hooks.ReviewRequestActionHook
   ~reviewboard.extensions.hooks.DiffViewerActionHook
   ~reviewboard.extensions.hooks.HeaderActionHook

When instantiating any of these hooks, we can pass in a list of dictionaries
that define the actions that we'd like to insert. These dictionaries must have
the following keys:

``id`` (optional):
    The ID of the action.

``label``:
    The label for the action.

``url``:
    The URL to invoke when the action is clicked.

    If we want to invoke a JavaScript action, then this should be ``#``, and
    there should be a selector on the ``id`` field to attach the handler (as
    opposed to a ``javascript:`` URL, which doesn't work on all browsers).

``image`` (optional):
    The path to the image used for the icon.

``image_width`` (optional):
    The width of the image.

``image_height`` (optional):
    The height of the image.

.. versionadded:: 3.0

   The :py:class:`~.hooks.BaseReviewRequestActionHook` class was added. Also,
   instead of passing in a list of dictionaries, we instead recommend passing
   in a list of :py:class:`~.actions.BaseReviewRequestAction` instances.

.. seealso:: The :py:mod:`reviewboard.reviews.actions` module.

There are also two hooks that can provide dropdown menus:

.. autosummary::

   ~reviewboard.extensions.hooks.ReviewRequestDropdownActionHook
   ~reviewboard.extensions.hooks.HeaderDropdownActionHook

These work like the basic action hooks, except instead of a ``url`` field, they
contain an ``items`` field which is another list of
:py:class:`~.ActionHook`-style dictionaries.

.. versionadded:: 3.0

   Up to two levels of action nesting are now possible. Also, instead of
   passing in a list of dictionaries, we instead recommend passing in a list of
   :py:class:`~.actions.BaseReviewRequestMenuAction` instances.

.. seealso:: The :py:mod:`reviewboard.reviews.actions` module.


Modifying the Default Actions
=============================

.. versionadded:: 3.0

The :py:mod:`reviewboard.reviews.actions` module provides two useful methods
for working with default review request actions:

.. autosummary::

   ~reviewboard.reviews.actions.register_actions
   ~reviewboard.reviews.actions.unregister_actions

.. seealso:: The :py:mod:`reviewboard.reviews.default_actions` module.


Example
=======

.. code-block:: python

   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import (BaseReviewRequestActionHook,
                                             HeaderDropdownActionHook,
                                             ReviewRequestActionHook)
   from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                            BaseReviewRequestMenuAction,
                                            register_actions,
                                            unregister_actions)


   class NewCloseAction(BaseReviewRequestAction):
       action_id = 'new-close-action'
       label = 'New Close Action!'


   class SampleMenuAction(BaseReviewRequestMenuAction):
       action_id = 'sample-menu-action'
       label = 'Sample Menu'


   class FirstItemAction(BaseReviewRequestAction):
       action_id = 'first-item-action'
       label = 'First Item'


   class SampleSubmenuAction(BaseReviewRequestMenuAction):
       action_id = 'sample-submenu-action'
       label = 'Sample Submenu'


   class SubItemAction(BaseReviewRequestAction):
       action_id = 'sub-item-action'
       label = 'Sub Item'


   class LastItemAction(BaseReviewRequestAction):
       action_id = 'last-item-action'
       label = 'Last Item'


   class SampleExtension(Extension):
       def initialize(self):
           # Register a new action in the Close menu.
           register_actions([NewCloseAction()], 'close-review-request-action')

           # Register a new review request action that only appears if the user
           # is on a review request page.
           ReviewRequestActionHook(self, actions=[
               {
                   'id': 'foo-item-action',
                   'label': 'Foo Item',
                   'url': '#',
               },
           ])

           # Register a new dropdown menu action (with two levels of nesting)
           # that appears if the user is on a review request page, a file
           # attachment page, or a diff viewer page.
           BaseReviewRequestActionHook(self, actions=[
               SampleMenuAction([
                   FirstItemAction(),
                   SampleSubmenuAction([
                       SubItemAction(),
                   ]),
                   LastItemAction(),
               ]),
           ])

           # Add a dropdown in the header that links to other pages.
           HeaderDropdownActionHook(self, actions=[
               {
                   'label': 'Sample Header Dropdown',
                   'items': [
                       {
                           'label': 'Item 1',
                           'url': '#',
                       },
                       {
                           'label': 'Item 2',
                           'url': '#',
                       },
                   ],
               },
           ])

       def shutdown(self):
           super(SampleExtension, self).shutdown()

           # Restore everything back to the original state by unregistering all
           # of the custom review request actions that were registered.
           unregister_actions([
               NewCloseAction.action_id,
               'foo-item-action',
               SampleMenuAction.action_id,
           ])
