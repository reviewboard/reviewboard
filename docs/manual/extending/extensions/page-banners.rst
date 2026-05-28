.. _extension-page-banners:

===================
Adding Page Banners
===================

Page banners appear at the top of every page in Review Board, above the
navigation bar. They're useful for drawing attention to important information,
such as scheduled maintenance windows, degraded service notices, prompts to
take action, or any other message that warrants prominent visibility.

We provide an official extension, :pypi:`rbmotd`, for letting administrators
manage a banner that shows important information to users on the server.

If you want to create your own banner in your extension, there are three key
things to know:

1. **Banner templates are created** by using or subclassing
   :ref:`TemplateHook <template-hook>` along with
   :file:`ui/components/page-banner.html`.

2. **Banner content is populated** by populating variables for the template.

3. **Banners are registered** by instantiating the
   :ref:`TemplateHook <template-hook>` in your extension using the
   ``page-banners`` hook point.


.. _extension-page-banners-creating:

Creating a Banner
=================

Creating a banner is as simple as:

1. Instantiating a :ref:`TemplateHook <template-hook>` using the
   :file:`ui/components/page-banner.html` template and ``page-banners`` hook
   point.

2. Providing :ref:`context variables <extension-page-banners-context>` for
   the template.

For example:

.. code-block:: python
   :caption: my_extension.py

   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import TemplateHook


   class MyExtension(Extension):
       def initialize(self) -> None:
           TemplateHook(
               self,
               name='page-banners',
               template_name='ui/components/page-banner.html',
               extra_context={
                   'banner_id': 'myextension-notice-banner',
                   'banner_header': 'Extended maintenance window tonight.',
               },
           )


.. _extension-page-banners-context:

Banner Context Variables
------------------------

The following variables can be provided through ``extra_context`` when
initializing the :ref:`TemplateHook <template-hook>`.

* ``banner_id``

  The ``id`` HTML attribute for the banner's main HTML element.

  If not set, an ID will be generated automatically.

  If you have any :ref:`JavaScript code <js-extensions>` that need to
  interact with this banner, you should set this to a stable, unique ID.
  You will need this if you're setting ``banner_can_close``.

* ``banner_header``

  The main text shown in the banner's header.

* ``banner_classes``

  Additional CSS classes to add to the banner's main element, as a single
  string.

  This is useful if you need to apply custom styling to any part of the
  banner.

* ``banner_can_close``

  Set to ``True`` to show a close button in the top-right corner of
  the banner. Defaults to ``False``.

  Note that Review Board does not handle closing banners for you, or
  remembering that the banner should be closed. It's up to your code to
  listen to click events on an HTML element with a ``rb-c-page-banner__close``
  CSS class under the ID of your banner and handling it yourself.

  See :ref:`extension-page-banners-closing` for more guidance.

* ``banner_aria_label``

  A label used to describe your banner to those using assistive technologies,
  like screen readers.

  If you don't provide this, the ``banner_header`` will be used instead.
  It's usually best to provide an explicit ``banner_aria_label`` if you're
  going to override content (see :ref:`extension-page-banners-templates`).

* ``banner_attrs``

  Extra HTML attributes to add to the banner's main element.

  This is useful for setting ``data-*`` attributes that your JavaScript can
  access, but you can provide anything you need.

  This must be an HTML-safe string, using
  :py:func:`django.utils.html.format_html`. For example:

  .. code-block:: python

     extra_context={
         'banner_attrs': format_html(
             'data-admin-email="{email}" data-important="true"',
             email='admin@example.com',
         ),
         ...
     }

* ``banner_scripts_template_name``

  The name of a template that provides ``<script>...</script>`` HTML for
  managing your banner.

  This would be a good place to handle a banner's close button (if setting
  ``banner_can_close=True``). The template would have access to all
  variables you've set as extra context.


.. _extension-page-banners-dynamic:

Dynamic Banners
===============

So far we've looked at static page banners, where the content never changes.
Sometimes you'll need to provide information that changes over time, like
a banner only shown during certain hours.

For dynamic content, you'll need to subclass :ref:`TemplateHook
<template-hook>` and instantiate your subclass. Your subclass can run
Python code every time your banner's being shown to decide what information
should be provided, and even show or hide the banner conditionally.

Here's an example that shows a banner only during maintenance hours:

.. code-block:: python
   :caption: my_extension.py

   from datetime import datetime, timezone
   from typing import Any

   from django.http import HttpRequest
   from django.template import Context
   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import TemplateHook


   class MaintenanceBannerHook(TemplateHook):
       name = 'page-banners'
       template_name = 'ui/components/page-banner.html'

       def get_extra_context(
           self,
           request: HttpRequest,
           context: Context,
       ) -> dict[str, Any]:
           maintenance_start, maintenance_end = \
               MyExtension.instance.get_maintenance_window()

           return {
               'banner_header': (
                   f'Maintenance will begin at {maintenance_start} and '
                   f'end at {maintenance_end}. Please be patient. It will '
                   f'be done soon.'
               ),
               'maintenance_start': maintenance_start,
               'maintenance_end': maintenance_end,
           }

       def should_render(
           self,
           *,
           request: HttpRequest,
           context: Context,
       ) -> bool:
           # This has access to any context we provided above.
           now = datetime.now(timezone.utc)
           maintenance_start = context['maintenance_start']
           maintenance_end = context['maintenance_end']

           # Show while the maintenance window is active.
           return maintenance_start <= now <= maintenance_end


   class MyExtension(Extension):
       def initialize(self) -> None:
           MaintenanceBannerHook(self)

       def get_maintenance_window(self) -> tuple[datetime, datetime]:
           return (
               datetime(1999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
               datetime(3999, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
           )


.. tip::

   If you want to set extra context, but you don't need it to be dynamic,
   you can just set ``extra_context`` as an attribute directly on the
   subclass.


.. _extension-page-banners-apply-to:

Limiting to Specific Pages
===========================

By default, a banner appears on all pages. To limit it to specific pages,
pass the URL names to ``apply_to``. There are :ref:`many pre-defined URL names
<extension-url-names>` to choose from.

Here's a banner that only renders on the :ref:`dashboard`:

.. code-block:: python

   TemplateHook(
       self,
       name='page-banners',
       template_name='ui/components/page-banner.html',
       extra_context={
           'banner_id': 'myextension-notice-banner',
           'banner_header': 'Extended maintenance window tonight.',
       },
       apply_to=['dashboard'],
   )


This works the same way if you subclass the banner:

.. code-block:: python

   MaintenanceBannerHook(
       self,
       apply_to=['dashboard'],
   )


Or you can set it right on the banner subclass itself:

.. code-block:: python

   class MaintenanceBannerHook(TemplateHook):
       name = 'page-banners'
       template_name = 'ui/components/page-banner.html'
       apply_to = ['dashboard']

       ...


.. _extension-page-banners-templates:

Customizing Banner Templates
============================

For truly advanced banners, you can extend the default
:file:`ui/components/page-banner.html` template and override the following
blocks instead of the context variables above (if you choose -- you can
continue to just supply attributes).

Here's a basic example of overriding a template:

.. code-block:: html+django
   :caption: templates/myextension/my_banner.html

   {% extends "ui/components/page-banner.html" %}

   {% block banner_classes %}myextension-mybanner -is-important{% endblock %}

   {% block banner_header %}Pay attention to me{% endblock %}

   {% block banner_content %}
    <span>
     Click this button:
     <button class="ink-c-button">Click me</button>
    </span>
   {% endblock banner_content %}

We'll look at how you extend a template in a minute, but first, let's go
over the template blocks that you can override.

The following work the same way as the :ref:`context variables
<extension-page-banners-context>` above (and default to any provided context
variables values if the block isn't overridden in your template).

* ``banner_attrs``
* ``banner_can_close``
* ``banner_classes``
* ``banner_header``
* ``banner_id``

The following additional blocks are also available:

* ``banner_content``

  Extra content you want to show in the banner, after the header (which you
  can omit if overriding this block).

  The content can be any HTML you want, but you may need to handle styling
  it yourself. ``banner_classes`` will come in handy there.

* ``banner_scripts``

  Explicit JavaScript you want to execute for this banner. These have access
  to all of the same variables passed down into the context or overridden
  in blocks.

  This is a good place to handle the Close Button.

  You can put content here instead of setting
  ``banner_scripts_template_name`` in your banner context.

  For example:

  .. code-block:: html+django
     :caption: templates/myextension/my_banner.html

     {% block banner_scripts %}
     <script>
       const bannerEl = document.getElementById('{{banner_id}}');
       const closeBtnEl = bannerEl.querySelector('.rb-c-page-banner__close');

       ...
     </script>
     {% endblock banner_scripts %}


.. _extension-page-banners-closing:

Closing Banners
===============

When setting ``banner_can_close=True``, the banner will show a close button
on the right-hand side.

By default, nothing happens when you click this. It's up to the extension
to handle closing the banner, and remembering that it was closed. A common
way to do this is to:

1. Provide JavaScript that listens for when the close button is clicked.

   This would live in the template specified by the
   ``banner_scripts_template_name`` context variable, or directly in the
   ``banner_scripts`` template block.

2. Closing the banner and setting a cookie when clicked.

3. Looking for the cookie when deciding whether to show the banner.


Here's a complete example of that in action.

.. code-block:: python
   :caption: my_extension.py

   class MyBannerHook(TemplateHook):
       name = 'page-banners'
       template_name = 'ui/components/page-banner.html'
       extra_context = {
           'banner_can_close': True,
           'banner_header': 'Do not close this banner or else.',
           'banner_id': 'myextension-banner',
           'banner_scripts_template_name': 'myextension/banner-scripts.html',
           'my_banner_close_cookie_name': 'mybanner-close-id',
           'my_banner_close_cookie_value': 'closed123',
       }

       def should_render(
           self,
           *,
           request: HttpRequest,
           context: Context,
       ) -> bool:
           cookie_name = context['my_banner_close_cookie_name']
           closed_value = context['my_banner_close_cookie_value']

           # Render this if the cookie is not set.
           return request.COOKIES.get(cookie_name) != closed_value


.. code-block:: html+django
   :caption: templates/myextension/banner-scripts.html

   <script>
     const bannerEl = document.getElementById('{{banner_id}}');
     const closeBtnEl = bannerEl.querySelector('.rb-c-page-banner__close');

     closeBtnEl.addEventListener('click', evt => {
         evt.preventDefault();
         bannerEl.remove();

         document.cookie = "{{my_banner_close_cookie_name}}=" +
                           "{{my_banner_close_cookie_value}}; " +
                           "path=/; max-age=34560000; SameSite=Strict";
     });
   </script>


You can customize this based on your needs, but this will give you basic
closing functionality that's remembered across page loads.
