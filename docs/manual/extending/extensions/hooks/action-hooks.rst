.. _action-hooks:
.. _action-hook:

==========
ActionHook
==========

.. versionadded:: 6.0

Review Board represents many pieces of the UI as :ref:`actions
<extension-actions>`, which are navigation links, buttons, or menu items that
can be provided or customized by an extension.

We have a :ref:`whole guide on actions <extension-actions>`, which you should
follow if you're looking to customize the UI.

Once you've written your action, you'll need to register it with
:py:class:`reviewboard.extensions.hooks.ActionHook`:

.. code-block:: python

   class MyExtension(Extension):
       def initialize(self) -> None:
           ActionHook(self, actions=[
               MyAction1(),
               MyAction2(),
           ])

These will be registered and available for rendering on pages.
