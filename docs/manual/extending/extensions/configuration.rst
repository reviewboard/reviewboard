=======================
Extension Configuration
=======================


.. _extension-settings:

Settings
========

Extensions are able to access, store, and modify settings that define their
behavior.

When an extension is enabled, Review Board will load any stored settings from
the database, making them available through the :py:attr:`settings` attribute
on the Extension.

Extensions can modify the settings by changing the contents of the dictionary
and calling :py:meth:`save`. For example:

.. code-block:: python

   self.settings['mybool'] = True
   self.settings['myint'] = 42
   self.settings['mystring'] = 'New Setting Value'
   self.settings.save()


.. _extension-settings-defaults:

Default Settings
----------------

Any settings not explicitly saved by the extension or loaded from the database
will be looked up in :py:attr:`default_settings`. This can be defined on the
Extension class.

Here is an example extension setting :py:attr:`default_settings`:

.. code-block:: python

   class SampleExtension(Extension):
       default_settings = {
           'mybool': True,
           'myint': 4,
           'mystring': "I'm a string setting",
       }


If neither :py:attr:`settings` nor py:attr:`default_settings` contains the
key, a :py:exc:`KeyError` exception will be thrown.


.. _extension-configuration:

Configuration Pages
===================

Extensions can provide a configuration page, allowing Review Board
administrators to customize the behavior of the extension.

By setting :py:attr:`is_configurable` to ``True`` and providing a
:file:`admin_urls.py` file, a :guilabel:`Configure` link will be shown in the
extension list for the extension. This is only shown when the extension is
enabled.

The extension will then need to create a page to present to the user for any
customizable settings. Review Board provides some helpers for this, which
will be described below.


.. _extension-configuration-urls:

Configuration URLs
------------------

When an extension is configurable, Review Board will load the extension's
:file:`admin_urls.py`, making those URLs available. An extension can provide
whatever it wants in here, but it's expected to provide at least the root
URL, designated by ``url(r'^$', ...)``. This should point to the main
configuration page.

This file follows the `Django URLs`_ format. It must provide a
``urlpatterns`` variable, which will contain all the URL patterns.
For example:

.. code-block:: python

   from django.conf.urls.defaults import patterns, url


   urlpatterns = patterns('sample_extension.views',
       url(r'^$', 'configure')
   )

This will call the ``configure`` function in ``sample_extension.views``
when clicking the :guilabel:`Configure` link.

.. _`Django URLs`: https://docs.djangoproject.com/en/dev/topics/http/urls/


.. _extension-configuration-settings-form:

Settings Form
-------------

Review Board makes it easy to create a basic configuration form for an
extension. It provides views, templates, and a form class that does the hard
work of loading settings, presenting them to the user, and saving them.

To make use of the provided configuration forms, you'll want to:

1. Define a new form class that inherits from
   :py:class:`djblets.extensions.forms.SettingsForm`

2. Create a new ``url()`` entry in :File:`admin_urls.py` that makes use
   of the provided configuration view, passing your extension and form
   classes.

Here is an example form class:

.. code-block:: python

   from django import forms
   from djblets.extensions.forms import SettingsForm


   class SampleExtensionSettingsForm(SettingsForm):
       field1 = forms.IntegerField(min_value=0, initial=1,
                                   help_text="Field 1")


And here is an example URL pattern for the form:

.. code-block:: python

   from django.conf.urls.defaults import patterns, url

   from sample_extension.extension import SampleExtension
   from sample_extension.forms import SampleExtensionSettingsForm


   urlpatterns = patterns('',
       url(r'^$',
           'reviewboard.extensions.views.configure_extension',
           {
               'ext_class': SampleExtension,
               'form_class': SampleExtensionSettingsForm,
           }),
   )


.. _extension-admin-site:

Admin Site (Database Browser)
=============================

By setting :py:attr:`has_admin_site` to ``True``, an extension will be given
its own Django database administration site. A button labeled
:guilabel:`Database` will appear in the list of installed extensions, linking
to that site.

The extension will also have a :py:attr:`admin_site` attribute that points to
the :py:class:`django.contrib.admin.sites.AdminSite` used. This is provided
automatically, and is used primarily for the registration of models.

Only models that are registered will appear in the database browser. You can
see the documentation on the `Django admin site`_ for details on how this
works. For example:

.. code-block:: python

   from reviewboard.extensions.base import get_extension_manager

   from sample_extension.extension import SampleExtension
   from sample_extension.models import SampleModel


   # You must get the loaded instance of the extension to register to the
   # admin site.
   extension_manager = get_extension_manager()
   extension = extension_manager.get_enabled_extension(SampleExtension.id)

   # Register the Model so it will show up in the admin site.
   extension.admin_site.register(SampleModel)


.. _`Django Admin Site`:
   https://docs.djangoproject.com/en/dev/ref/contrib/admin/
