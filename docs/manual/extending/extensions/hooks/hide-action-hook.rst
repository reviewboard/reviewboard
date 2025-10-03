.. _hide-action-hook:

==============
HideActionHook
==============

.. versionadded:: 6.0

In some cases, you may want your extension to hide built-in actions. This
can be used to remove unwanted functionality, or to hide the defaults so you
can replace them with your own custom behavior.

Simply initialize the hook with a list of the
:py:attr:`~reviewboard.actions.base.BaseAction.action_id` of the actions that
you want to hide.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import HideActionHook

    class SampleExtension(Extension):
        def initialize(self) -> None:
            HideActionHook(self, action_ids=['support-menu'])
