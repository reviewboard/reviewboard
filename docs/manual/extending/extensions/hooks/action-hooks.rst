.. _action-hooks:
.. _action-hook:

==========
ActionHook
==========

.. versionadded:: 6.0

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

    from typing import Any

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

        def should_render(
            self,
            context: dict[str, Any],
        ) -> bool:
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
