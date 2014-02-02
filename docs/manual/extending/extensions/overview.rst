.. _extensions-overview:

========
Overview
========

Review Board's functionality can be enhanced by installing one or more
extensions. Writing and installing an extension is an excellent way to tailor
Review Board to your exact needs. Here are a few examples of the many things
you can accomplish by writing an extension:

* Modify the user interface, providing new links or buttons.
* Generate statistics for report gathering.
* Interface Review Board with other systems (e.g. an IRC bot).
* Add new API for efficiently gathering custom data from the database.
* Provide review UIs for previously unsupported types of files.

Extensions were introduced as an experimental feature in Review Board 1.7.
However, many of the features discussed here were added or changed in Review
Board 2.0.


Extension Structure
===================

Extensions must follow a certain structure in order to be recognized and
loaded by Review Board. They are distributed inside Python Egg packages,
which must follow a few conventions. See :ref:`extension-python-egg` for more
information.

.. note::
   The Review Board extension system has been designed to follow many
   of Django_'s conventions. The structure of an extension package tries
   to mirror that of Django apps.

The main constituent of an extension is a class which inherits from the
Extension base class :py:class:`reviewboard.extensions.base.Extension`.

The Review Board repository contains a script for generating the
initial code an extension requires. See :ref:`extension-generator` for
more information.


.. _Django: https://www.djangoproject.com/


Required Files
--------------

At minimum, an extension requires the following files:

*  :ref:`setup.py <extension-example-files-setup.py>`
*  *extensiondir*/:ref:`__init__.py <extension-example-files-__init__.py>`
*  *extensiondir*/:ref:`extension.py <extension-example-files-extension.py>`


The following are a description and example of each file. In each example
*extensiondir* has been replaced with the extension's package,
`'sample_extension'`:

.. _extension-example-files-setup.py:

**setup.py**
   This is the file used to create the Python Egg. It defines the
   :ref:`extension-entry-point` along with other meta-data. See
   :ref:`extension-distribution` for a description of features relevant to
   Review Board extensions. For example::

      from reviewboard.extensions.packaging import setup


      PACKAGE = "sample_extension"
      VERSION = "0.1"

      setup(
          name=PACKAGE,
          version=VERSION,
          description='Description of extension package.',
          author='Your Name',
          packages=['sample_extension'],
          entry_points={
              'reviewboard.extensions':
                  '%s = sample_extension.extension:SampleExtension' % PACKAGE,
          },
      )

   See :ref:`extension-distribution` and the :py:mod:`setuptools` documentation
   for more information.

.. _extension-example-files-__init__.py:

sample_extension/**__init__.py**
   This file indicates the sample_extension is a Python package. It is
   generally left blank.

.. _extension-example-files-extension.py:

sample_extension/**extension.py**
   This is the main module of the extension. The Extension subclass should
   be defined here. For example::

      from reviewboard.extensions.base import Extension


      class SampleExtension(Extension):
          def initialize(self):
              # Your extension initialization code belongs here.

   This file will often be where you'll define any hooks, utility functions,
   and extension metadata you may need. Throughout this guide, we'll cover
   the various things you may place in this file.


Optional Files
--------------

Review Board also expects extensions to follow a few other conventions when
naming files. The following files serve a special purpose:

**models.py**
   An extension may define Django models in this file. The corresponding
   tables will be created in the database when the extension is loaded. See
   :ref:`extension-models` for more information.

**models/**
   As an alternative to using :file:`models.py`, a Python package may be
   created in a :file:`models/` directory, which may contain files with other
   models. Like any Python module directory, it must also contain an
   :file:`__init__.py`.

**admin_urls.py**
   An extension may define URLs for configuration in the administration UI.

   This file is only used when :py:attr:`is_configurable` is set ``True``.
   For more information, see :ref:`extension-configuration-urls`.

**admin.py**
   This file allows an extension to register its models in its own section
   of the administration UI, allowing administrators to browse the content
   in the database.

   This file is only used when :py:attr:`has_admin_site` is set ``True``.
   For more information, see :ref:`extension-admin-site`.


.. _extension-class:

Extension Class
===============

The main component of an extension is a class inheriting from
:py:class:`reviewboard.extensions.base.Extension`. It can optionally set
the following attributes on the class:

* :py:attr:`apps`
* :py:attr:`context_processors`
* :py:attr:`css_bundles`
* :py:attr:`default_settings`
* :py:attr:`has_admin_site`
* :py:attr:`is_configurable`
* :py:attr:`js_bundles`
* :py:attr:`js_extensions`
* :py:attr:`metadata`
* :py:attr:`middleware`
* :py:attr:`requirements`
* :py:attr:`resources`

The following are also available on an extension instance:

* :py:attr:`settings`


.. py:class:: reviewboard.extensions.base.Extension

   .. py:attribute:: apps

      A list of `Django apps`_ that the extension either provides or depends
      upon.

      Each "app" is a Python module path that Django will use when looking for
      models, template tags, and more.

      This does not need to include the app for the extension itself, but
      if the extension is grouped into separate Django apps, it can list
      those.

      This setting is equivalent to modifying ``settings.INSTALLED_APPS``
      in Django.

   .. py:attribute:: context_processors

      A list of `Django context processors`_, which inject variables into
      every rendered template. Certain third-party apps depend on context
      processors.

      This setting is equivalent to modifying
      ``settings.TEMPLATE_CONTEXT_PROCESSORS`` in Django.

   .. py:attribute:: css_bundles

      A list of custom CSS media bundles that can be used when rendering
      pages.

      See :ref:`extension-static-files` for more information.

   .. py:attribute:: default_settings

      A dictionary of default settings for the extension. These defaults
      are used when accessing :py:attr:`settings`, if the user hasn't
      provided a custom value. By default, this is empt.

      See :ref:`extension-settings-defaults` for more information.

   .. py:attribute:: has_admin_site

      A boolean that indicates whether a Django admin site should be generated
      for the extension.

      If ``True``, a :guilabel:`Database` link will be shown for the
      extension, allowing the user to inspect and modify the extension's
      database entries. The default is ``False``.

      See :ref:`extension-admin-site` for more information.

   .. py:attribute:: is_configurable

      A boolean indicating whether the extension supports global
      configuration by a system administrator.

      If ``True``, a :guilabel:`Configure` link will be shown for the
      extension when enabled, taking them to the configuration page provided
      by the extension. The default is ``False``.

      See :ref:`extension-configuration` for more information.

   .. py:attribute:: js_bundles

      A list of custom JavaScript media bundles that can be used when
      rendering pages.

      See :ref:`extension-static-files` for more information.

   .. py:attribute:: js_extensions

      A list of :py:class:`reviewboard.extensions.base.JSExtension`
      subclasses used for providing JavaScript-side extensions.

      See :ref:`js-extensions` for more information.

   .. py:attribute:: metadata

      A dictionary providing additional information on the extension,
      such as the name or a description.

      By default, the metadata from :file:`setup.py` is used when displaying
      information about the extension inside the administration UI. Extensions
      can override what the user sees by setting the values in this
      dictionary.

      The following metadata keys are supported:

      ``Name``
         The human-readable name of the extension, shown in the extension
         list.

      ``Version``
         The version of the extension. Usually, the version specified in
         :file:`setup.py` suffices.

      ``Summary``
         A brief summary of the extension, shown in the extension list.

      ``Description``
         A longer description of the extension. As of Review Board 2.0, this
         is not shown to the user, but it may be used in a future release.

      ``Author``
         The individual or company that authored the extension.

      ``Author-email``
         The contact e-mail address for the author of the extension.

      ``Author-home-page``
         The URL to the author's public site.

      ``Home-page``
         The URL to the extension's public site.

      We generally recommend setting ``Name``, ``Summary``, and the
      author information. ``Version`` is usually best left to the package,
      unless there's a special way it should be presented.

   .. py:attribute:: middleware

      A list of `Django middleware`_ classes, which hook into various levels
      of the HTTP request/response and page render process.

      This is an advanced feature, and is generally not needed by most
      extensions. Certain third-party apps may depend on middleware,
      though.

      This setting is equivalent to modifying
      ``settings.MIDDLEWARE_CLASSES`` in Django.

   .. py:attribute:: requirements

      A list of strings providing the names of other extensions the
      extension requires. Enabling the extension will in turn enable
      all required extensions, and can only be enabled if the required
      extensions can also be enabled.

      See :ref:`extension-egg-dependencies` for more information.

   .. py:attribute:: settings

      An instance of :py:class:`djblets.extensions.settings.Settings`. This
      attribute gives each extension an easy-to-use and persistent data store
      for settings.

      See :ref:`extension-settings` for more information.

   .. py:attribute:: resources

      A list of :py:class:`reviewboard.webapi.resources.WebAPIResource`
      subclasses. This is used to extend the Web API.

      See :ref:`extension-resources` for more information.


.. _`Django apps`: https://docs.djangoproject.com/en/dev/intro/reusable-apps/
.. _`Django context processors`:
   https://docs.djangoproject.com/en/dev/ref/templates/api/#subclassing-context-requestcontext
.. _`Django middleware`:
   https://docs.djangoproject.com/en/dev/topics/http/middleware/


.. _extension-models:

Models
======

Extensions are able to provide `Django Models`_, which are database tables
under the control of the extension. Review Board handles registering these
models, creating the database tables, and performing any database schema
migrations the extension defines.

Extensions use the same convention as `Django apps`_ when defining
Models. In order to define new Models, a :file:`models.py` file, or a
:file:`models/` directory constituting a Python package needs to be created.

Here is an example :file:`models.py` file::

   from django.db import models


   class MyExtensionsSampleModel(models.Model):
       name = models.CharField(max_length=128)
       enabled = models.BooleanField(default=False)

See the `Django Models`_ documentation for more information on how to
write a model, and `Django Evolution`_ for information on how to write
database schema migrations.

.. note::
   When an extension is disabled, tables for its models remain in the
   database. These should generally not interfere with anything.


.. _`Django Models`: https://docs.djangoproject.com/en/dev/topics/db/models/
.. _`Django Evolution`: http://django-evolution.googlecode.com/


.. _extension-settings:

Settings
========

Extensions are able to access, store, and modify settings that define their
behavior.

When an extension is enabled, Review Board will load any stored settings from
the database, making them available through the :py:attr:`settings` attribute
on the Extension.

Extensions can modify the settings by changing the contents of the dictionary
and calling :py:meth:`save`. For example::

   self.settings['mybool'] = True
   self.settings['myint'] = 42
   self.settings['mystring'] = 'New Setting Value'
   self.settings.save()


.. _extension-settings-defaults:

Default Settings
----------------

Any settings not explicitly saved by the extension or loaded from the database
will be looked up in :py:attr:`default_settings`. This can be defined on the
Extension class. For example::

Here is an example extension setting :py:attr:`default_settings`::

   class SampleExtension(Extension):
       default_settings = {
           'mybool': True,
           'myint': 4,
           'mystring': 'I'm a string setting',
       }


If neither :py:attr:`settings` nor py:attr:`default_settings` contains the
key, a :py:exc:`KeyError` exception will be thrown.


.. _extension-configuration:

Configuration
=============

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
whatever it wants in here, but it's expected to proivide at least the root
URL, designated by ``url(r'^$', ...)``. This should point to the main
configuration page.

This file follows the `Django URLs`_ format. It must provide a
``urlpatterns`` variable, which will contain all the URL patterns.
For example::

   from django.conf.urls.defaults import patterns, url


   urlpatterns = patterns('sample_extension.views',
       url(r'^$', 'configure')
   )

This will call the ``configure`` function in ``sample_extension.views``
when clickin the :guilabel:`Configure` link.

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

Here is an example form class::

   from django import forms
   from djblets.extensions.forms import SettingsForm


   class SampleExtensionSettingsForm(SettingsForm):
       field1 = forms.IntegerField(min_value=0, initial=1,
                                  help_text="Field 1")


And here is an example URL pattern for the form::

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
works. For example::

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


.. _extension-resources:

Extending the Web API
=====================

Each extension has a very basic API resource that clients can use to fetch
details on the extension, such as the name, URLs, and whether it's enabled.

Extensions can extend this to provide even more resources, which can be used
to retrieve or modify any information the extension chooses. They do this by
creating :py:class:`reviewboard.webapi.resources.WebAPIResource` subclasses
and listing an instance of each that you want as a child of the extension's
resource in :py:attr:`resources` attribute.

Resources are complex, but are explained in detail in the Djblets
`WebAPIResource code`_.

.. _`WebAPIResource code`:
   https://github.com/djblets/djblets/blob/master/djblets/webapi/resources.py


For example, a resource for creating and publishing a simplified review may
look like::

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
       uri_name = 'review'
       allowed_methods = ('POST',)

       def has_access_permissions(self, request, *args, **kwargs):
           return review_request.is_accessible_by(request.user)

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

   sample_review_resource = SampleExtensionResource()


The extension would then make use of this with::

   class SampleExtension(Extension):
       resources = [sample_review_resource]


With this, one would be able to POST to this resource to create reviews that
contained the text "Sample review body". This API endpoint would be registered
at
``/api/extensions/sample_extension.extension.SampleExtension/reviews/``.


.. _extension-generator:

Extension Boilerplate Generator
===============================

The Review Board repository contains a script for generating the boilerplate
code for a new extension. This script is part of the Review Board tree and can
be run by typing::

   ./contrib/tools/generate_extension.py
