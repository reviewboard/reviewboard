.. _extensions-overview:

========
Overview
========

.. versionadded:: 1.7
   Many of the features here are new in Review Board 1.7


Review Board's functionality can be enhanced by installing a Review Board
extension. Writing and installing an extension is an excellent way to tailor
Review Board to your exact needs. Here are a few examples of the many things
you can accomplish by writing an extension:

*  Modify the user interface, providing new links or buttons.
*  Generate statistics for report gathering.
*  Interface Review Board with other systems (e.g. an IRC bot).


Extension Structure
===================

Extensions must follow a certain structure to be recognized and loaded
by Review Board. They are distributed inside Python Eggs following a few
conventions. See :ref:`extension-python-egg` for more information.

.. note::
   The Review Board extension system has been designed to follow many
   of Django's conventions. The structure of an extension package tries
   to mirror that of Django apps.

The main constituent of an extension is a class which inherits from the
Extension base class :py:class:`reviewboard.extensions.base.Extension`.

The Review Board repository contains a script for generating the
initial code an extension requires. See :ref:`extension-generator` for
more information.


Minimum Extension Structure
---------------------------

At minimum, an extension requires the following files:

*  :ref:`setup.py <extension-example-files-setup.py>`
*  *extensiondir*/:ref:`__init__.py <extension-example-files-__init__.py>`
*  *extensiondir*/:ref:`extension.py <extension-example-files-extension.py>`


The following are a description and example of each file. In each example
*extensiondir* has been replaced with the extension's package,
'sample_extension':

.. _extension-example-files-setup.py:

**setup.py**

   This is the file used to create the Python Egg. It defines the
   :ref:`extension-entry-point` along with other meta-data. See
   :ref:`extension-distribution` for a description of features relevant to
   Review Board extensions. Example::

      from reviewboard.extensions.packaging import setup


      PACKAGE = "sample_extension"
      VERSION = "0.1"

      setup(
          name=PACKAGE,
          version=VERSION,
          description="description of extension",
          author="Your Name",
          packages=["sample_extension"],
          entry_points={
              'reviewboard.extensions':
                  '%s = sample_extension.extension:SampleExtension' % PACKAGE,
          },
      )

   See :ref:`extension-distribution` and the :py:mod:`setuptools` documentation
   for more information.

.. _extension-example-files-__init__.py:

sample_extension/**__init__.py**

   This file indicates the sample_extension is a Python package.

.. _extension-example-files-extension.py:

sample_extension/**extension.py**

   This is the main module of the extension. The Extension subclass should
   be defined here. Example::

      from reviewboard.extensions.base import Extension


      class SampleExtension(Extension):
          def __init__(self, *args, **kwargs):
              super(SampleExtension, self).__init__(*args, **kwargs)


Other Structure
---------------

Review Board also expects extensions to follow a few other conventions when
naming files. The following files serve a special purpose:

**models.py**
   An extension may define Django models in this file. The
   corresponding tables will be created in the database when the extension is
   loaded. See :ref:`extension-models` for more information.

**models/**
   As an alternative to using models.py, a Python package may
   be created in models/, which may define models in its modules.

**admin_urls.py**
   An extension may define urls for
   configuration in the admin panel. It is only used when
   :py:attr:`is_configurable` is set ``True``. For more information, see
   :ref:`extension-configuration-urls`.

**admin.py**
   This file allows an extension to register models in its own Django admin
   site. It is only used when :py:attr:`has_admin_site` is set ``True``. For
   more information, see :ref:`extension-admin-site`.


.. _extension-class:

Extension Class
===============

The main component of an extension is a class inheriting from
:py:class:`reviewboard.extensions.base.Extension`. It can optionally set
the following attributes:

* :py:attr:`is_configurable`
* :py:attr:`has_admin_site`
* :py:attr:`default_settings`
* :py:attr:`requirements`

The base class also provides the following attributes:

* :py:attr:`settings`


.. py:class:: reviewboard.extensions.base.Extension

   .. py:attribute:: is_configurable

      A Boolean indicating whether the extension supports configuration in
      the Review Board admin panel. The default is ``False``. See
      :ref:`extension-configuration` for more information.

   .. py:attribute:: has_admin_site

      A Boolean that indicates whether a Django admin site should be generated
      for the extension. The default is ``False``. See
      :ref:`extension-admin-site` for more information.

   .. py:attribute:: default_settings

      A Dictionary which acts as a default for :py:attr:`settings`. The default
      is ``{}``, an empty dictionary. See :ref:`extension-settings-defaults`
      for more information.

   .. py:attribute:: requirements

      A list of strings providing the names of other extensions the
      extension requires. An extension may only be enabled if all
      other extensions in its requirements list are also enabled.
      See :ref:`extension-egg-dependencies` for more information.

   .. py:attribute:: settings

      An instance of :py:class:`djblets.extensions.settings.Settings`. This
      attribute gives each extension an easy-to-use and persistent data store
      for settings. See :ref:`extension-settings` for more information.

   .. py:attribute:: metadata

      A dictionary which can contain extra package metadata. Normally, the
      metadata from `setup.py` is used when displaying information about the
      extension inside the administration UI. Defining this dictionary allows
      you to override what gets displayed to the user, which is useful for
      providing human-readable names. In particular, the `Name` and
      `Description` fields in this dictionary are very useful.

   .. py:attribute:: resources

      A list of resource class names. This is used to extend the Web API with
      additional endpoints. See :ref:`extension-resources` for more
      information.


.. _extension-models:

Models
======

Extensions are able to define Django Models to expand the database schema.
When an extension is loaded, it is added to :py:attr:`INSTALLED_APPS`
automatically. New Models are then written to the database by Review Board,
which runs syncdb programmatically.

.. note::
   Review Board is also able to evolve the database programmatically. This
   allows a developer to make changes to an extension's models after release.

Extensions use the same convention as Django applications when defining
Models. In order to define new Models, a :file:`models.py` file, or a
:file:`models/` directory constituting a Python package should be created.

Here is an example :file:`models.py` file::

   from django.db import models


   class MyExtensionsSampleModel(models.Model):
       name = models.CharField(max_length=128)
       enabled = models.BooleanField()

.. note::
   When an extension is disabled, tables for its models are not dropped.
   For a development installation, an evolution to drop these tables may be
   generated using::

      ./reviewboard/manage.py evolve --purge

   Alternativley, when developing against a Review Board install, rb-site
   may be used::

      rb-site manage /path/to/site evolve -- --purge


.. _extension-settings:

Settings
========

Each extension is given a settings dictionary which it can load from the
database using :py:meth:`load` and save to the database using :py:meth:`save`.
This is found in the :py:attr:`settings` attribute and is an instance of the
:py:class:`djblets.extensions.settings.Settings` class.

A set of defaults may be provided in :py:attr:`default_settings` to make
initialization of the dictionary simple. See :ref:`extension-settings-defaults`
for more information.

.. py:class:: djblets.extensions.settings.Settings

   .. py:method:: load()

      Retrieves the dictionary entries from the database.

   .. py:method:: save()

      Stores the dictionary entries to the database.


Here is an example of how to save settings::

   settings['mysetting'] = "New Setting Value"
   settings.save()  # Store the settings in the database.

And an example of how to load settings::

   settings.load()  # Retrieve the settings from the database.
   mysetting = settings['mysetting']  # Read the setting value.


.. _extension-settings-defaults:

Default Settings
----------------

To provide defaults for the :py:attr:`settings` dictionary, an extension
may use the :py:attr:`default_settings` attribute. If a key is not
found in :py:attr:`settings`, :py:attr:`default_settings` will be checked.
If neither dictionary contains the key, a :py:exc:`KeyError` exception
will be thrown.

Here is an example extension setting :py:attr:`default_settings`::

   class SampleExtension(Extension):
      default_settings = {
         'mysetting': 1,
         'anothersetting': 4,
         'stringsetting': "I'm a string setting",
      }

      def __init__(self, *args, **kwargs):
        super(SampleExtension, self).__init__(*args, **kwargs)


.. _extension-configuration:

Configuration
=============

For administrative configuration, extensions are able to hook into the
Review Board admin panel.

By setting :py:attr:`is_configurable` to ``True``, an extension is assigned
a URL namespace under the admin path. New URLs are added to this namespace
using an admin_urls.py file. See :ref:`extension-configuration-urls` for
more information.

Review Board also supplies views, templates, and forms, making management
of :ref:`extension-settings` painless. See
:ref:`extension-configuration-settings-form` for more information.

.. _extension-configuration-urls:

Admin URLs
----------

If an extension has :py:attr:`is_configurable` set to ``True``, it will
be assigned a URL namespace under the admin path. A button labeled
:guilabel:`Configure` will appear in the list of installed extensions,
linking to the base path of this namespace.

To specify URLs in the namespace, an :file:`admin_urls.py` file should be
created, taking the form of a Django URLconf module. This module should
follow Django's conventions, defining a :py:data:`urlpatterns` variable.

.. py:data:: urlpatterns

   Used to specify URLs. This should be a Python list, in the format returned
   by the function :py:func:`django.conf.urls.patterns`.

The following is an example :file:`admin_urls.py` file::

   from django.conf.urls.defaults import patterns, url


   urlpatterns = patterns('sample_extension.views',
       url(r'^$', 'configure')
   )

This would direct the base URL of the namespace to the configure view.

For a more in depth explanation of URLconfs please see the
`Django URLs`_ documentation.

.. _`Django URLs`: https://docs.djangoproject.com/en/1.4/topics/http/urls/

.. _extension-configuration-settings-form:

Settings Form
-------------

Review Board supplies the views, templates, and a base Django form to make
creating a configuration UI for :ref:`extension-settings` painless. To take
advantage of this feature, do the following:

*
   Define a new form class inheriting from
   :py:class:`djblets.extensions.forms.SettingsForm`

*
   Create a new URL pattern to
   `reviewboard.extensions.views.configure_extension`, providing the extension
   class and form class. See :ref:`extension-configuration-urls` for more
   information on creating URL patterns.

Here is an example form class::

   from django import forms
   from djblets.extensions.forms import SettingsForm


   class SampleExtensionSettingsForm(SettingsForm):
       field1 = forms.IntegerField(min_value=0, initial=1, help_text="Field 1")

Here is an example URL pattern for the form::

   from django.conf.urls.defaults import patterns

   from sample_extension.extension import SampleExtension
   from sample_extension.forms import SampleExtensionSettingsForm


   urlpatterns = patterns('',
       (r'^$', 'reviewboard.extensions.views.configure_extension',
        {'ext_class': SampleExtension,
         'form_class': SampleExtensionSettingsForm,
        }),
   )


.. _extension-admin-site:

Admin Site
==========

By setting :py:attr:`has_admin_site` to ``True``, an extension will be given
its own Django admin site. A button labeled :guilabel:`Database` will appear
in the list of installed extensions, linking to the base path of the admin site.

The extension's instance of :py:class:`django.contrib.admin.sites.AdminSite`
will exist in the :py:attr:`admin_site` attribute of the Extension.

Models should be registered to the Admin site in an :file:`admin.py` file.
Here is an example :file:`admin.py` file::

   from reviewboard.extensions.base import get_extension_manager

   from sample_extension.extension import SampleExtension
   from sample_extension.models import SampleModel


   # You must get the loaded instance of the extension to register to the
   # admin site.
   extension_manager = get_extension_manager()
   extension = extension_manager.get_enabled_extension(SampleExtension.id)

   # Register the Model to the sample_extensions admin site.
   extension.admin_site.register(SampleModel)

For more information on Django admin sites, please see the `Django Admin Site`_
documentation.

.. _`Django Admin Site`: https://docs.djangoproject.com/en/1.4/ref/contrib/admin/


.. _extension-resources:

Extending the Web API
=====================

Each extension is given a location in the Web API which is used to get
information about the extension and enable or disable it. Extensions can add
child resources to this location by defining the :py:attr:`resources`
attribute.

Here is an example resource class::

   from django.core.exceptions import ObjectDoesNotExist
   from djblets.webapi.decorators import (webapi_login_required,
                                          webapi_response_errors,
                                          webapi_request_fields)
   from djblets.webapi.errors import DOES_NOT_EXIST
   from reviewboard.webapi.decorators import webapi_check_local_site
   from reviewboard.reviews.models import Review
   from reviewboard.webapi.resources import (WebAPIResource,
                                             review_Request_resource)

   class SampleExtensionResource(WebAPIResource):
       """Resource for creating reviews"""
       name = 'sample_extension_review'
       allowed_methods = ('POST',)

       @webapi_check_local_site
       @webapi_login_required
       @webapi_response_errors(DOES_NOT_EXIST)
       @webapi_request_fields(
           required={
               'review_request_id': {
                   'type': int,
                   'description': 'The ID of the review request',
               },
           },
       )
       def create(self, request, review_request_id, *args, **kwargs):
           try:
               review_request = review_request_resource.get_object(
                   request, review_request_id, *args, **kwargs)
           except ObjectDoesNotExist:
               return DOES_NOT_EXIST

           new_review = Review.objects.create(
               review_request=review_request,
               user=request.user,
               body_top='Sample review body')
           new_review.publish(user=request.user)

           return 201, {
               self.item_result_key: new_review
           }

       def has_access_permissions(self, request, *args, **kwargs):
           return review_request.is_accessible_by(request.user)

   sample_review_resource = SampleExtensionResource()


And the corresponding extension::

   class SampleExtension(Extension):
       resources = [sample_review_resource]

       def __init__(self, *args, **kwargs):
           super(SampleExtension, self).__init__(*args, **kwargs)


With this, one would be able to POST to this resource to create reviews that
contained the text "Sample review body". This API endpoint would be registered
at
``/api/extensions/sample_extension.extension.SampleExtension/sample-extension-reviews/``.


.. _extension-generator:

Extension Boilerplate Generator
===============================

The Review Board repository contains a script for generating the boilerplate
code for a new extension. This script is part of the Review Board tree and is
located here::

   ./contrib/tools/generate_extension.py


.. comment: vim: ft=rst et ts=3
