.. _extension-configuration:

=======================
Extension Configuration
=======================


.. _extension-settings:

Settings
========

Extensions are able to access, store, and modify settings that define their
behavior.

When an extension is enabled, Review Board will load any stored settings from
the database, making them available through the :py:attr:`Extension.settings
<djblets.extensions.extension.Extension.settings>` attribute on the Extension.

Extensions can modify the settings by changing the contents of the dictionary
and calling :py:meth:`settings.save()
<djblets.extensions.settings.Settings.save>`. For example:

.. code-block:: python

   self.settings['mybool'] = True
   self.settings['myint'] = 42
   self.settings['mystring'] = 'New Setting Value'
   self.settings.save()


.. _extension-settings-defaults:

Default Settings
----------------

Any settings not explicitly saved by the extension or loaded from the database
will be looked up in :py:attr:`Extension.default_settings
<djblets.extensions.extension.Extension.default_settings>`.

Here is an example extension setting default settings:

.. code-block:: python

   class SampleExtension(Extension):
       default_settings = {
           'mybool': True,
           'myint': 4,
           'mystring': "I'm a string setting",
       }


If neither :py:attr:`Extension.settings
<djblets.extensions.extension.Extension.settings>` nor
:py:attr:`Extension.default_settings
<djblets.extensions.extension.Extension.default_settings>` contains the key, a
:py:exc:`KeyError` exception will be raised.


.. _extension-configuration-pages:

Configuration Pages
===================

Extensions can provide a configuration page, allowing Review Board
administrators to customize the behavior of the extension.

By setting :py:attr:`Extension.is_configurable
<djblets.extensions.extension.Extension.is_configurable>` to ``True`` and
providing a :file:`admin_urls.py` file, a :guilabel:`Configure` link will be
shown in the extension list for the extension. This is only shown when the
extension is enabled.

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

This file follows the :djangodoc:`Django URLs <topics/http/urls>` format. It
must provide a ``urlpatterns`` variable, which will contain all the URL
patterns. For example:

.. code-block:: python

   from django.conf.urls import url

   from sample_extension.views import my_configure


   urlpatterns = [
       url(r'^$', my_configure),
   ]

This will call the ``my_configure`` function in ``sample_extension.views``
when clicking the :guilabel:`Configure` link.


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
       field1 = forms.IntegerField(min_value=0,
                                   initial=1,
                                   help_text='Put a number in this field.')


And here is an example URL pattern for the form:

.. code-block:: python

   from django.conf.urls import url
   from reviewboard.extensions.views import configure_extension

   from sample_extension.extension import SampleExtension
   from sample_extension.forms import SampleExtensionSettingsForm


   urlpatterns = [
       url(r'^$',
           configure_extension,
           {
               'ext_class': SampleExtension,
               'form_class': SampleExtensionSettingsForm,
           }),
   ]
