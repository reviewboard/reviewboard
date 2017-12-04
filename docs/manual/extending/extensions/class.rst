.. _extension-class:

===========================
Creating an Extension Class
===========================

Your extension will live in :file:`extension.py` and inherit from
:py:class:`~reviewboard.extensions.base.Extension`. There's a lot you can do
with this file, but it can start out very simple:

.. code-block:: python

   from reviewboard.extensions.base import Extension


   class SampleExtension(Extension):
       def initialize(self):
           # Your extension initialization code belongs here.


That's a pretty simplistic extension. You probably want to do a lot more with
it. This section will cover some of the attributes and methods you can define.


.. _extension-metadata:

Defining Extension Metadata
===========================

By default, your extension's basic information (name, description, author,
etc.) will be taken from the package's metadata. You may want to override some
or all of this. You can do so using the
:py:attr:`~djblets.extensions.extension.Extension.metadata` attribute:

.. code-block:: python

   class SampleExtension(Extension):
       metadata = {
           'Name': 'My extension name',
           'Version': '1.0',
           'Summary': 'My summary.',
           'Description': 'A longer description.',
           'Author': 'My Name',
           'Author-email': 'me@example.com',
           'Author-home-page': 'https://me.example.com/',
           'License': 'MIT',
           'Home-page': 'https://myextension.example.com/',
       }

These are used primarily for display purposes in the administration UI. The
version, however, is also used for some state tracking, so whether you're
leaving it up to the package or defining it here, you'll want to make sure to
increase the version when you have a new release going into production.

.. note::

   As a best practice, we recommend *not* overriding the version here, and
   instead using the Python package version, unless your package is shipping
   more than one extension and you want to keep their versions separate.


Handling Initialization and Shutdown
====================================

When your extension is enabled, its
:py:meth:`~djblets.extensions.extension.Extension.initialize` method will be
called. This is where you'll put code to set up :ref:`extension hooks
<extension-hooks>` or perform any other initialization.

When your extension is disabled (or Review Board is shutting down in a web
server process), the
:py:meth:`~djblets.extensions.extension.Extension.shutdown` method will be
called.  You can use this to perform any cleanup you may need to do.

Note that hooks do not need to be cleaned up by your extension. This will
happen automatically.

.. code-block:: python

   class SampleExtension(Extension):
       def initialize(self):
           logging.info('My extension is enabled!')

       def shutdown(self):
           logging.info('My extension is disabled!')


Requiring Other Extensions
==========================

Extensions can be written to extend or depend on other extensions. This is far
less common, but if you need it, you'll want to know about the
:py:attr:`~djblets.extensions.extension.Extension.requirements` attribute.
This is a list of extension IDs that will be enabled when enabling your
extension.

.. code-block:: python

   class SampleExtension(Extension):
       requirements = [
           'some_other_extension.extension.SomeOtherExtension',
       ]


Adding Django Apps
==================

Your extension may ship with several sub-modules that work as Django_ "app"
modules, with their own :file:`models.py` or similar. It might require
third-party Django apps to be in :django:setting:`INSTALLED_APPS`. In either
case, you can list these apps in the
:py:attr:`~djblets.extensions.extension.Extension.apps` attribute.

.. code-block:: python

   class SampleExtension(Extension):
       apps = [
           'sample_extension.some_app1',
           'sample_extension.some_app2',
           'third_party_app',
       ]

When enabled, these apps will be added (if not already) to
:django:setting:`INSTALLED_APPS` and initialized. When disabled, they'll be
removed (if nothing else is using them).


.. _Django: https://www.djangoproject.com/


Adding Django Context Processors
================================

Context processors are a Django_ feature that provides additional variables to
all templates. If your extension needs to inject variables into most pages, or
you're using a third-party Django app that expectes a context processor to be
loaded in :django:setting:`TEMPLATE_CONTEXT_PROCESSORS`, then you can add them
in the :py:attr:`~djblets.extensions.extension.Extension.context_processors`
attribute.

.. code-block:: python

   class SampleExtension(Extension):
       context_processors = [
           'sample_extension.context_processors.my_processor',
           'third_party_app.context_processors.some_processor',
       ]


Adding Django Middleware
========================

Middleware is another Django_ feature that's used to inject logic into the
HTTP request/response process. They can be used to
:ref:`process HTTP requests <django:request-middleware>`,
:ref:`invoke views <django:view-middleware>`,
:ref:`process responses <django:response-middleware>`,
:ref:`process template responses <django:template-response-middleware>`, or
:ref:`handle exceptions <django:exception-middleware>` raised by views. These
can be added through the
:py:attr:`~djblets.extensions.extension.Extension.middleware` attribute.

.. code-block:: python

   class SampleExtension(Extension):
       middleware = [
           'sample_extension.middleware.MyMiddleware',
           'third_party_app.middleware.SomeMiddleware',
       ]


Defining Static Media Bundles
=============================

Static media bundles for your extension can be defined through the
:py:attr:`~djblets.extensions.extension.Extension.css_bundles` and
:py:attr:`~djblets.extensions.extension.Extension.js_bundles` attributes. These
are used to package up CSS/LessCSS/JavaScript files that can be loaded onto
any new or existing pages in Review Board. For example:

.. code-block:: python

    class SampleExtension(Extension):
        css_bundles = {
            'default': {
                'source_filenames': ['css/common.less'],
            },
        }

        js_bundles = {
            'default': {
                'source_filenames': [
                    'js/extension.js',
                    'js/common.js',
                ]
            },
            'admin': {
                'source_filenames': ['js/admin.js'],
            }
        }

This is covered in more detail in :ref:`extension-static-files`.


Custom Configuration and Settings
=================================

Extensions come with their own settings storage, and you can offer
customization of these settings however you like.

Default settings can be specified by setting a
:py:attr:`~djblets.extensions.extension.Extension.default_settings`
dictionary.  These are the fallbacks for any values not stored in the database
for the extension. Enabled extensions can then access the current settings or
set new ones through
:py:attr:`~djblets.extensions.extension.Extension.settings`.

.. code-block:: python

    class SampleExtension(Extension):
        default_settings = {
            'enable_secret_message': True,
            'days_until_secret_message': 42,
            'secret_message_text': "It's a secret to everyone.",
        }

If you want to enable configuration, you'll need to set
:py:attr:`~djblets.extensions.extension.Extension.is_configurable` to ``True``
and define URLs and views for your configuration page.

.. code-block:: python

    class SampleExtension(Extension):
        is_configurable = True

This is covered in more detail in :ref:`extension-configuration`.


Adding API Resources
====================

Your extension may want to define custom API for use by RBTools_ and other
clients or services. Any top-level API resources you define can be enabled
through :py:attr:`~djblets.extensions.extension.Extension.resources`. You'll
specify them as instances of your resource classes.

.. code-block:: python

    from my_extension.resources import my_resource_1, my_resource_2


    class SampleExtension(Extension):
        resources = [
            my_resource_1,
            my_resource_2,
        ]

This is covered in more detail in :ref:`extension-resources`.


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding JavaScript Extensions
============================

Review Board extensions can contain a JavaScript extension counterpart, which
can interact with the UI dynamically. These are added by subclassing
:py:class:`~reviewboard.extensions.base.JSExtension` and listing the classes
in :py:attr:`~djblets.extensions.extension.Extension.js_extensions`.

.. code-block:: python

    class SampleJSExtension(JSExtension):
        ...


    class SampleExtension(Extension):
        js_extensions = [SampleJSExtension]

This is covered in more detail in :ref:`js-extensions`.


Enabling an Administrator Site
==============================

If you're defining custom database models, you may want to allow users to
create or modify entries for these models. You can do this by enabling a
database administrator site for your extension by setting
:py:attr:`~djblets.extensions.extension.Extension.has_admin_site` to ``True``.

.. code-block:: python

    class SampleExtension(Extension):
        has_admin_site = True

When the extension is enabled, a :guilabel:`Database` will be shown along with
the extension's information. This will be a miniature version of Review
Board's normal database viewer.

This is covered in more detail in :ref:`extension-admin-site`.


.. _extension-read-only-mode:

Supporting Read-Only Mode
=========================

Review Board can be put into read-only mode by the site administrator, which
disables API requests to the server and hides associated front-end features.
If you would like your extension to be compliant or have specific behavior in
read-only mode, :py:meth:`~reviewboard.admin.read_only.is_site_read_only_for`
can be called with a :py:class:`User <django.contrib.auth.models.User>` to
check if the User should be affected by the read-only mode.

.. code-block:: python

   from reviewboard.admin.read_only import is_site_read_only_for
       ...


   if is_site_read_only_for(user):
       # Put code to run when in read-only mode here.
