.. _extension-actions:

===============================
Customizing the UI with Actions
===============================

Review Board represents many pieces of the UI as "actions", which are
navigation links, buttons, or menu items that can be provided or customized
by an extension.

These are used for:

* Buttons, menus, and menu items in the review request action bar (used for
  closing a review request, uploading a file, archiving, and more)

* The menus at the top of the page (account menu, :guilabel:`Support`, and
  :guilabel:`Follow`)

* The administration UI sidebar items

If you want to add to any of those, you'll need to define your own actions.

There are four key things to know about the action framework:

1. **Actions are created** by inheriting from
   :py:class:`~reviewboard.actions.base.BaseAction` (or a subclass), defining
   attributes that describe the action and its placements within the UI. Most
   actions provide a simple label that links to another page, but JavaScript
   can be used to provide more advanced behavior.

2. **Actions are placed** in the UI using one or more
   :py:class:`~reviewboard.actions.base.ActionPlacement` instances, which
   define the "attachment point" (the area of the page -- use
   :py:class:`~reviewboard.actions.base.AttachmentPoint` for a predefined list
   of options) and the ID of any parent action to place it within.

3. **Actions are rendered** by a
   :py:class:`~reviewboard.actions.renderers.BaseActionRenderer`. Each
   placement or parent action may define the renderer used to render any
   actions placed there. This may render as a button, a menu, a menu item, or
   something else.  Actions may also provide their own renderer, if they need
   to.

4. **Actions are registered** by passing them to an
   :py:class:`~reviewboard.extensions.hooks.ActionHook` when instantiating
   the extension.


.. _extension-actions-create:

Creating an Action
==================

A basic action
--------------

To create an action, subclass
:py:class:`~reviewboard.actions.base.BaseAction` and provide the following
attributes:

*
    :py:attr:`~reviewboard.actions.base.BaseAction.action_id`:
    The ID of the action. This must be unique to your action.

*
    :py:attr:`~reviewboard.actions.base.BaseAction.label`:
    A user-visible label for the action.

*
    :py:attr:`~reviewboard.actions.base.BaseAction.verbose_label`:
    A more verbose user-visible label for the action. This is used for
    certain renders where space is available, and as a descriptive label for
    screen readers and other accessibility tools.

*
    :py:attr:`~reviewboard.actions.base.BaseAction.placements`:
    A list of places in the UI where the action should show up. This includes
    the "attachment" (the location within the UI) and an optional ID of the
    parent action to place it within.

    Built-in attachment points can be found in
    :py:class:`reviewboard.actions.base.AttachmentPoint`. You can also define
    your own attachment points by setting this to a unique string and then
    using the :py:func:`~reviewboard.actions.templatetags.actions.actions_html`
    template tag.


A basic example would be:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)


   class MyAction(BaseAction):
       action_id = 'my-action'
       label = 'My Action'
       verbose_label = 'My very special action'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER),
       ]

This will place an action in the header area (where your account menu lives).
But this action won't do anything by itself.


Dynamic labels
--------------

Your action may want to show a different label based on the context of
the page. For example, maybe the label should incorporate someone's
username or data from a database.

Instead of setting the attributes above, you can override these methods:

*
    :py:meth:`~reviewboard.actions.base.BaseAction.get_label`:
    Returns the label to use.

    By default, this just returns
    :py:attr:`~reviewboard.actions.base.BaseAction.label`, but can be
    overridden to return a dynamic result:

    .. code-block:: python

       from django.template import Context

       ...

       class MyAction(BaseAction):
           ...

           def get_label(
               self,
               *,
               context: Context,
           ) -> str:
               user = context['request'].user

               if user.is_anonymous:
                   return 'Public tasks'
               else:
                   return f"{user.username}'s tasks"

*
    :py:meth:`~reviewboard.actions.base.BaseAction.get_verbose_label`:
    Returns the verbose label to use.

    By default, this just returns
    :py:attr:`~reviewboard.actions.base.BaseAction.verbose_label`, but can be
    overridden to return a dynamic result:

    .. code-block:: python

       from django.template import Context

       ...

       class MyAction(BaseAction):
           ...

           def get_verbose_label(
               self,
               *,
               context: Context,
           ) -> str:
               user = context['request'].user

               if user.is_anonymous:
                   return 'All public tasks'
               else:
                   return f"All of {user.username}'s tasks"


Linking to a URL
----------------

Often, you'll want to make your action link somewhere (unless you're using
JavaScript for managing the action -- see below).

To define a URL for your action, use one of:

*
    :py:attr:`~reviewboard.actions.base.BaseAction.url`:
    A URL to link to for the action. The default is ``'#'``, which enables
    handling the action via JavaScript.

*
    :py:attr:`~reviewboard.actions.base.BaseAction.url_name`:
    The name of a URL registered via :ref:`URLHook <url-hook>`. This is
    generally preferred over **url** and takes precedence.

You can also override the URL with a method:

*
    :py:meth:`~reviewboard.actions.base.BaseAction.get_url`:
    Returns the URL to use.

    By default this will just check which URL attribute was set and return
    the appropriate resolved URL.


.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)


   class MyAction(BaseAction):
       action_id = 'my-action'
       label = 'My Action'

       # Either:
       url = 'https://corp.example.com/my-tool/'

       # Or:
       url_name = 'my-registered-url-name'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER),
       ]


Adding only to certain pages
----------------------------

If you want your extension to show up only to certain pages, use:

*
    :py:attr:`~reviewboard.actions.base.BaseAction.apply_to`:
    A list of URL names where the action should appear (assuming the placement
    or parent is available on those pages).

    There are :ref:`many pre-defined URL names <extension-url-names>` that
    might be useful to you.

    If this is not set (the default), this will appear on all pages that
    match any listed placements.

For example, to show up only on the dashboard and reviewable pages (review
request page, diff viewer, and file attachments):

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)
   from reviewboard.reviews.actions import all_review_request_url_names


   class MyAction(BaseAction):
       action_id = 'my-action'
       label = 'My Action'
       url_name = 'my-registered-url-name'

       apply_to = [
           'dashboard',
           *all_review_request_url_names,
       ]

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER),
       ]


Controlling visibility
----------------------

Sometimes you want your action to be shown only under certain circumstances.
It might only apply to certain users or repository types.

The following attributes can control visibility:

*
    :py:attr:`~reviewboard.actions.base.BaseAction.visible`:
    Whether the action should be visible by default

    If set to ``False``, the action will still be rendered on the page,
    but will be hidden by default. JavaScript can then show the action
    on demand.

    .. code-block:: python

       class MyAction(BaseAction):
           visible = False

The following methods can further influence visibility:

*
    :py:meth:`~reviewboard.actions.base.BaseAction.get_visible`:
    Returns whether the action should be visible.

    This returns :py:attr:`~reviewboard.actions.base.BaseAction.visible`
    by default, but you can extend the action to base the result on data
    in the template context.

    For example:

    .. code-block:: python

       from django.template import Context

       ...

       class MyAction(BaseAction):
           ...

           def get_visible(
               self,
               *,
               context: Context,
           ) -> bool:
               # Only show for anonymous users.
               return context['request'].user.is_anonymous

*
    :py:meth:`~reviewboard.actions.base.BaseAction.should_render`:
    Returns whether the action should even be rendered onto the page.

    This can be used to keep an action from being at all included on the
    page. Normally, this checks
    :py:attr:`~reviewboard.actions.base.BaseAction.apply_to` and
    :ref:`HideActionHook <hide-action-hook>` to determine the result.

    If you extend this, you should call the parent method first and return
    its result if ``False``.

    .. code-block:: python

       from django.template import Context

       ...

       class MyAction(BaseAction):
           ...

           def should_render(
               self,
               *,
               context: Context,
           ) -> bool:
               # Only show for Bob.
               return (
                   super().should_render(context=context) and
                   context['request'].user.username == 'bob'
               )


.. _extension-actions-js-model:

Custom JavaScript models and state
----------------------------------

Each action has a central JavaScript model that contains information about
the action. Your action may want to provide more information that your
JavaScript extension code can set or use.

The following attributes may be useful:

*
    :py:attr:`~reviewboard.actions.base.BaseAction.js_model_class`:
    The class of the JavaScript model to instantiate for the action.

    This may be necessary if you want to provide central logic on your
    action model that other code can call.

    .. code-block:: python

       class MyAction(BaseAction):
           js_model_class = 'MyExtension.MyAction'

The following methods may also be useful:

*
    :py:meth:`~reviewboard.actions.base.BaseAction.get_js_model_data`:
    Return JavaScript model data for your action.

    If you override this, make sure to call the parent method and return
    its results along with yours.

    .. code-block:: python

       from django.template import Context
       from typelets.django.json import SerializableDjangoJSONDict

       ...

       class MyAction(BaseAction):
           ...

           def get_js_model_data(
               self,
               *,
               context: Context,
           ) -> SerializableDjangoJSONDict:
               model_data = super().get_js_model_data(context=context)
               model_data['myExtraState'] = 123

               return model_data

If you've set a custom JavaScript model, you'll need to define your
JavaScript class as a subclass of ``RB.Actions.Action``.

The main method to override is ``activate()``, which is called when the user
triggers the action (for example, when a button or menu item representing
the action is clicked).

.. tabs::

   .. code-tab:: javascript JavaScript

      class MyAction extends RB.Actions.Action {
          async activate() {
              // Handle the action here.
              const myExtraState = this.get('myExtraState');
          }
      }

      MyExtension.MyAction = MyAction;

   .. code-tab:: typescript TypeScript

      import { spina } from '@beanbag/spina';
      import { Actions } from 'reviewboard/common';


      @spina
      export class MyAction extends Actions.Action {
          async activate() {
              // Handle the action here.
              const myExtraState = this.get('myExtraState');
          }
      }

Any attributes you pass back from
:py:meth:`~reviewboard.actions.base.BaseAction.get_js_model_data` on the
Python side will be available as model attributes, accessible via
``this.get('attributeName')``.


Controlling rendering
---------------------

For more advanced actions, you may also want to control the rendering of
your action and the JavaScript state behind it.

The following attributes may be useful:

*
    :py:attr:`~reviewboard.actions.base.BaseAction.default_renderer_cls`:
    The default :py:class:`~reviewboard.actions.renderers.BaseActionRenderer`
    subclass to use if no other renderer is available.

    This is rarely required, but may be needed if you're defining your own
    attachment points without their own default renderer.

*
    :py:attr:`~reviewboard.actions.base.BaseAction.js_template_name`:
    The name of the template file to use for rendering the JavaScript side of
    the action's state model.

    You will almost never need to change this.


Creating Menu Actions
=====================

Menus are a common UI pattern, and we've made it easy to create menus that
you can populate with other actions.

To create a menu action, subclass
:py:class:`reviewboard.actions.base.BaseMenuAction` instead:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseMenuAction)


   class MyMenuAction(BaseMenuAction):
       action_id = 'my-menu'
       label = 'My menu'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER),
       ]

This will place a menu in the header area (where your account menu lives).
That's all we have to do. Now we can add menu items to it:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)


   class MyMenuItemAction(BaseAction):
       action_id = 'my-menu-item'
       label = 'My menu item'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER,
                           parent_id='my-menu')
       ]


Registering an Action
=====================

In order for your action to appear in the UI, or for your JavaScript
to interact with it, you will need to register it. This is done by
passing one or more action instances to an :ref:`action-hook`:

.. code-block:: python

   class MyExtension(Extension):
       def initialize(self) -> None:
           ActionHook(self, actions=[
               MyAction1(),
               MyAction2(),
           ])

These will be registered and available for rendering on pages.


Writing an Action Renderer
==========================

For more advanced actions, you may want to control exactly how the action is
rendered on the page. This is done by subclassing
:py:class:`~reviewboard.actions.renderers.BaseActionRenderer` and setting
your action's
:py:attr:`~reviewboard.actions.base.BaseAction.default_renderer_cls` to
reference it.

The following attributes can be set on a renderer:

*
    ``template_name``:
    The path to a Django template for rendering the action's HTML.

*
    ``js_view_class``:
    The JavaScript view class to use for the rendered action. Review Board
    provides several built-in options:

    * ``'RB.Actions.ActionView'``: The default base view.
    * ``'RB.Actions.ButtonActionView'``: A clickable button that calls
      ``activate()`` on the model when clicked.
    * ``'RB.Actions.MenuActionView'``: A dropdown menu.
    * ``'RB.Actions.MenuItemActionView'``: An item inside a dropdown menu
      that calls ``activate()`` on the model when clicked.

You can also override the following method:

*
    :py:meth:`~reviewboard.actions.renderers.BaseActionRenderer.
    get_extra_context`:
    Return additional context variables for the template.

    Make sure to call the parent method and include its results.

For example:

.. code-block:: python

   from django.http import HttpRequest
   from django.template import Context

   from reviewboard.actions.base import BaseAction
   from reviewboard.actions.renderers import BaseActionRenderer


   class MyActionRenderer(BaseActionRenderer):
       template_name = 'myextension/my_action.html'
       js_view_class = 'RB.Actions.ButtonActionView'

       def get_extra_context(
           self,
           *,
           request: HttpRequest,
           context: Context,
       ) -> dict:
           return dict(
               super().get_extra_context(request=request, context=context),
               my_extra_data='...',
           )


   class MyAction(BaseAction):
       ...

       default_renderer_cls = MyActionRenderer


This would render using the template specified in your action, which
should extend ``actions/action_base.html`` and implement the
``action_content`` block. For example:

.. code-block:: html+django

   {% extends "actions/action_base.html" %}

   {% block action_content %}
   <a {{action_attrs}} href="{{url}}" role="button"
      aria-label="{{verbose_label}}">
    {{label}}
    {% if my_extra_data %}
     <strong>({{my_extra_data}})</strong>
    {% endif %}
   </a>
   {% endblock action_content %}



The following context variables are automatically available:

*
    ``action``:
    The action object. Useful for accessing custom attributes, or attributes
    like :py:attr:`action.icon_class
    <reviewboard.actions.base.BaseAction.icon_class>`.

*
    ``action_attrs``:
    Pre-built HTML attributes for the inner element, including the ID
    and visibility state. Insert these directly into your element's
    opening tag.

*
    ``dom_element_id``:
    The unique DOM element ID for the action.

*
    ``label``:
    The label to show on the action.

*
    ``url``:
    The URL to navigate to, if suitable for the action.

*
    ``verbose_label``:
    A verbose label, suitable for wider elements and for ARIA labels for
    screen readers and other assistive technologies.

*
    ``visible``:
    Whether the action should appear visible.

*
    Any variables returned by
    :py:meth:`~reviewboard.actions.renderers.BaseActionRenderer.
    get_extra_context`.


Writing Actions For...
======================

.. _extension-actions-page-header:

Page Headers
------------

The header area at the top of every page contains a set of menus:

* Your account menu (when logged in)
* :guilabel:`Support`
* :guilabel:`Follow`

You can add your own standalone menus or links alongside these, or add items
to any of these built-in menus.

To place an action in the header, use a placement attaching to
:py:attr:`~reviewboard.actions.base.AttachmentPoint.HEADER`.


Adding a standalone menu or link
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add a standalone menu or link to the header, use either
:py:class:`~reviewboard.actions.base.BaseMenuAction` (for a dropdown menu) or
:py:class:`~reviewboard.actions.base.BaseAction` (for a top-level item).

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction,
                                         BaseMenuAction)
   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import ActionHook


   class MyHeaderMenu(BaseMenuAction):
       action_id = 'my-header-menu'
       label = 'My Menu'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER),
       ]


   class MyHeaderMenuItem(BaseAction):
       action_id = 'my-header-menu-item'
       label = 'My Menu Item'
       url = 'https://example.com/'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER,
                           parent_id=MyHeaderMenu.action_id),
       ]


   class SampleExtension(Extension):
       def initialize(self) -> None:
           ActionHook(self, actions=[
               MyHeaderMenu(),
               MyHeaderMenuItem(),
           ])


Adding to built-in header menus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can add items to the built-in header menus by including the menu's
action ID as the placement's ``parent_id``.

The following action IDs are available:

* ``"account-menu"``: The logged-in user's account menu.
* ``"follow-menu"``: The :guilabel:`Follow` menu.
* ``"support-menu"``: The :guilabel:`Support` menu.

For example, to add an item to the account menu:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)
   from reviewboard.accounts.actions import AccountMenuAction


   class MyAccountMenuItem(BaseAction):
       action_id = 'my-account-menu-item'
       label = 'My Feature'
       url = 'https://corp.example.com/user'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.HEADER,
                           parent_id=AccountMenuAction.action_id),
       ]


.. _extension-actions-review-request:

Review Request Action Bar
-------------------------

The review request action bar contains the buttons and menus shown on the
review request page, such as :guilabel:`Update`, :guilabel:`Close`, and
:guilabel:`Download Diff`.

To place an action in the action bar:

1. Use a placement attaching to
   :py:attr:`~reviewboard.actions.base.AttachmentPoint.REVIEW_REQUEST`
   (for the actions on the right) or
   :py:attr:`~reviewboard.actions.base.AttachmentPoint.REVIEW_REQUEST_ELFT`
   (for the actions on the left).

2. Set :py:attr:`~reviewboard.actions.base.BaseAction.apply_to` to
   :py:data:`reviewboard.reviews.actions.all_review_request_url_names`.

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)
   from reviewboard.reviews.actions import all_review_request_url_names


   class MyReviewRequestAction(BaseAction):
       action_id = 'my-review-request-action'
       label = 'My Action'
       apply_to = all_review_request_url_names

       placements = [
           ActionPlacement(attachment=AttachmentPoint.REVIEW_REQUEST),
       ]

You'll probably want to define a :ref:`custom JavaScript model
<extension-actions-js-model>` to control what happens when this is clicked.


Adding to built-in review request menus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also add items to the built-in review request menus in the review
request action bar by including the menu's action ID as the placement's
``parent_id``.

The following action IDs are available:

* ``"close-menu"``: The :guilabel:`Close` menu.
* ``"update-menu"``: The :guilabel:`Update` menu.

For example, to add an item to the :guilabel:`Update` menu:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)
   from reviewboard.reviews.actions import (UpdateMenuAction,
                                            all_review_request_url_names)


   class MyUpdateMenuItem(BaseAction):
       action_id = 'my-update-menu-item'
       label = 'My Update Option'
       apply_to = all_review_request_url_names

       placements = [
           ActionPlacement(attachment=AttachmentPoint.REVIEW_REQUEST,
                           parent_id=UpdateMenuAction.action_id),
       ]


.. _extension-actions-admin-sidebar:

Admin UI Sidebar
----------------

The administration UI sidebar lists the various pages for administering your
server, changing settings, and working with the database. Extensions can add
their own links anywhere in the sidebar for their own features or settings
pages.

To place an action in the admin sidebar, use a placement attaching to
:py:attr:`~reviewboard.actions.base.AttachmentPoint.ADMIN_NAV`.


Adding to the Main or Settings groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For links to your own administration or settings pages, use a plain
:py:class:`~reviewboard.actions.base.BaseAction` placed under the
appropriate group:

* ``"admin-main-nav-group"``: Main administration items (dashboard,
  extensions, licensing, security center, etc.).
* ``"admin-settings-nav-group"``: Review Board settings pages.

For example, to add a settings link:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)
   from reviewboard.admin.actions import AdminSettingsNavGroupAction


   class MySettingsItem(BaseAction):
       action_id = 'my-settings-item'
       label = 'My Settings'
       url_name = 'my-settings-url'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                           parent_id=AdminSettingsNavGroupAction.action_id),
       ]


Adding managed items
~~~~~~~~~~~~~~~~~~~~

If you have a Django model that you want to expose in the
:guilabel:`Manage` section of the sidebar (alongside Users, Repositories,
etc.), subclass
:py:class:`~reviewboard.admin.actions.BaseAdminSidebarManageItemAction`
instead of a plain :py:class:`~reviewboard.actions.base.BaseAction`.

This automatically provides:

* A link to the model's admin changelist page.
* An :guilabel:`Add` icon that links to the model's admin add page.
* A live count badge showing how many items are in the database.

The minimum required attribute is ``model``:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint)
   from reviewboard.admin.actions import (AdminManageNavGroupAction,
                                          BaseAdminSidebarManageItemAction)

   from myextension.models import MyModel


   class MyManagedItem(BaseAdminSidebarManageItemAction):
       action_id = 'my-managed-item'
       label = 'My Items'
       model = MyModel

       placements = [
           ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                           parent_id=AdminManageNavGroupAction.action_id),
       ]

The following optional attributes let you customize the behavior:

*
    :py:attr:`~reviewboard.admin.actions.BaseAdminSidebarManageItemAction.
    add_item_url_name`:
    The Django URL name to use for the :guilabel:`Add` button. Defaults to
    the URL name derived from ``model``.

*
    :py:attr:`~reviewboard.admin.actions.BaseAdminSidebarManageItemAction.
    add_item_title`:
    The tooltip text for the :guilabel:`Add` button. Defaults to
    :samp:`"Add a new {model}"`.

*
    :py:attr:`~reviewboard.admin.actions.BaseAdminSidebarManageItemAction.
    item_queryset`:
    A custom queryset for the count badge. Defaults to
    ``model.objects.all()``.

*
    :py:attr:`~reviewboard.admin.actions.BaseAdminSidebarManageItemAction.
    admin_site_name`:
    The admin site name used for URL resolution. Defaults to ``'admin'``.


Creating a new sidebar group
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add an entirely new sidebar group, use
:py:class:`~reviewboard.admin.actions.BaseAdminSidebarGroupAction`:

.. code-block:: python

   from reviewboard.actions.base import (ActionPlacement,
                                         AttachmentPoint,
                                         BaseAction)
   from reviewboard.admin.actions import BaseAdminSidebarGroupAction


   class MyAdminGroup(BaseAdminSidebarGroupAction):
       action_id = 'my-admin-group'
       label = 'My Section'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV),
       ]


   class MyAdminItem(BaseAction):
       action_id = 'my-admin-item'
       label = 'My Feature'
       url_name = 'my-admin-feature-url'

       placements = [
           ActionPlacement(attachment=AttachmentPoint.ADMIN_NAV,
                           parent_id=MyAdminGroup.action_id),
       ]
