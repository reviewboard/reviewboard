.. _js-extensions:

=====================
JavaScript Extensions
=====================

Extensions are not purely server-side. Often, they need to interact with some
part of the client-side UI, whether that's to augment a dialog, dynamically
render new UI, or communicate with the API.

To hook into things on the client side, JavaScript-side extensions can be
created. These are defined server-side and then served up to the browser. They
work much like the typical Python extensions, in that you'll create an
extension subclass (of :js:class:`RB.Extension`) and make use of hooks.


Creating an Extension
=====================

You'll first start by defining some information server-side about your
extension. You'll need to create a subclass of
:py:class:`reviewboard.extensions.base.JSExtension` and reference it in your
main extension class, using the :py:attr:`Extension.js_extensions
<djblets.extensions.extension.Extension.js_extensions>` attribute. Your
:py:class:`~reviewboard.extensions.base.JSExtension` subclass will also
specify the name of the JavaScript-side extension model class to instantiate.

Here's an example:

.. code-block:: python

    from reviewboard.extensions.base import Extension, JSExtension


    class SampleJSExtension(JSExtension):
        model_class = 'SampleExtensionProject.Extension'


    class SampleExtension(Extension):
        js_extensions = [SampleJSExtension]

        js_bundles = {
            'default': {
                'source_filenames': (
                    'js/extension.js',
                ),
            }
        }

You'll then need to create your JavaScript-side extension in a file listed in
an appropriate bundle (such as the :file:`js/extension.js` shown above):

.. code-block:: javascript

    window.SampleExtensionProject = {};

    SampleExtensionProject.Extension = RB.Extension.extend({
        initialize: function() {
            RB.Extension.initialize.call(this);

            /* Your setup goes here. */
        }
    });

Now unlike Python-side extensions, you don't need to worry about things like
managing the shutdown logic for extensions. These extensions only run while
the page is loaded, and are re-initialized on every page load. They do not
persist.

.. tip::

   You can create multiple JavaScript-side extensions, which is useful when
   you have different requirements for different pages. You don't need to do
   everything in one extension.

   See :ref:`js-extensions-page-specific` for more information.


Instantiating Hooks
===================

We ship with a few JavaScript-side extension hooks that you can use. These are
documented in the :ref:`js-extensions-hooks` list, and are instantiated like
so:

.. code-block:: javascript

    SampleExtensionProject.Extension = RB.Extension.extend({
        initialize: function() {
            RB.Extension.initialize.call(this);

            new RB.SomeExampleHook({
                extension: this,
                ...
            });
        }
    });

See the documentation for each hook on its usage.

.. note::

   There aren't a lot of JavaScript-side hooks yet, and we're still evaluating
   what makes sense to add here. If you have a particular need for a hook, you
   can suggest one on the reviewboard-dev_ list.

You can also manually listen to events, set up UI, register handlers, etc.
without using hooks. Anything you set up will be undone when the user closes
or leaves the page. However, please note that JavaScript-side classes/events
are subject to change, so please code defensively!


.. _js-extensions-page-specific:

Page-Specific Extensions
========================

You can specify that an extension should only load on one or more specific
pages, or define different extensions for different pages. This is really
useful when you want to augment the behavior of the review request, a review
UI, etc., but don't want to carry all that logic around to every page.

To do this, you'll make use of the :py:attr:`JSExtension.apply_to
<djblets.extensions.extension.JSExtension.apply_to>` attribute. This is a list
of URL names that the extension will be loaded on. See the Static Media guide
on :ref:`static-media-apply-to` for a list.

You should also put your extension in a bundle that will be loaded only for
those same pages, using the ``apply_to`` key for the bundle.

Here's an example that loads the extension only for diff viewer page and one
custom URL for your extension:

.. code-block:: python

    from reviewboard.extensions.base import Extension, JSExtension
    from reviewboard.urls import diffviewer_url_names


    class SampleJSExtension(JSExtension):
        model_class = 'SampleExtensionProject.Extension'
        apply_to = diffviewer_url_names + [
            'sample-extension-project-my-diff-url',
        ]


    class SampleExtension(Extension):
        js_extensions = [SampleJSExtension]

        js_bundles = {
            'diffviewer-extension': {
                'source_filenames': (
                    'js/diffviewer-extension.js',
                ),
                'apply_to': SampleJSExtension.apply_to,
            }
        }


Accessing Extension Data
========================

JavaScript-side extensions are automatically instantiated with some
information about the extension. There are a few Backbone.js_ attributes
available for your extension interface:

``id``:
    The ID of your extension (same as ``MyExtensionClass.id``).

``name``:
    The name of your extension (see :ref:`extension-metadata`).

``settings``:
    Settings stored for your extension (see :ref:`js-extension-settings`).

You can also define custom data to pass (see
:ref:`js-extensions-custom-model-data`).


.. _js-extension-settings:

Extension Settings
------------------

By default, your JavaScript-side extension will receive all of your
extension's settings. These are read-only, and will be accessible through your
``settings`` attribute on your extension's instance.

Here's an example of how extension settings can work:

:file:`extension.py`:
    .. code-block:: python

        class SampleExtension(Extension):
            default_settings = {
                'feature_enabled': True,
            }

            ...

:file:`extension.js`:
    .. code-block:: javascript

        SampleExtensionProject.Extension = RB.Extension.extend({
            initialize: function() {
                RB.Extension.initialize.call(this);

                if (this.get('settings').feature_enabled) {
                    ...
                });
            }
        });

.. warning::

   You may not want all your settings to be passed onto the page. There might
   be some secret information (license keys, for instance) that you'd like to
   keep from the page. Remember that anything loaded onto the page is
   available for the user to see.

To provide only certain settings to your extension, or to normalize the
content for the page, you can override :py:meth:`JSExtension.get_settings
<djblets.extensions.extension.JSExtension.get_settings>`. For example:

.. code-block:: python

    class SampleJSExtension(JSExtension):
        ...

        def get_settings(self):
            settings = self.extension.settings

            return {
                'setting1': settings.get('setting1'),
                'setting2': settings.get('setting2'),
                ...
            }


.. _js-extensions-custom-model-data:

Custom Model Data
-----------------

You can also define custom data on the Python side that will be passed to your
extension instance, separately from settings. This is useful when you want to
precompute some form of data to pass down, based on the state of the server or
of your Python-side extension. This can be done by overriding
:py:meth:`JSExtension.get_model_data
<djblets.extensions.extension.JSExtension.get_model_data>`.

.. code-block:: python

    class SampleJSExtension(JSExtension):
        ...

        def get_model_data(self):
            return {
                'some_state': SampleExtension.calculate_some_state(),
            }

Your JavaScript-side extension can then get access to this data using standard
Backbone.js attribute accessors:

.. code-block:: javascript

    SampleExtensionProject.Extension = RB.Extension.extend({
        initialize: function() {
            var someState;

            RB.Extension.initialize.call(this);

            someState = this.get('some_state');

            ...
        }
    });


.. _js-extensions-read-only-mode:

Supporting Read-Only Mode
=========================

Reviewboard can be put into read-only mode by the site administrator, which
disables API requests to the server and associated front-end features. When the
site is in read-only mode, only changes made to models by superusers will be
propagated to the server; changes made by all other users will be discarded.

Whether a user is in read-only mode can be checked by looking up the
``readOnly`` property in the :js:class:`RB.UserSession` instance.

.. code-block:: javascript

   if (RB.UserSession.instance.get('readOnly')) {
       /* Put code to run when in read-only mode here. */
   }


.. _Backbone.js: http://backbonejs.org/
.. _reviewboard-dev: https://groups.google.com/group/reviewboard-dev
