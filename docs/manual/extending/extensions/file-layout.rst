==============================
Extension Files/Package Layout
==============================

When building a Review Board extension, you'll want to adopt a certain file
layout. If you're a seasoned Python developer, you're probably already
familiar with most of this, but if not, we're going to walk you through the
basics of building a Python module for your extension.

This directory structure for your module will allow it to be packaged as a
Python package. This will be covered in more detail in
:ref:`extension-distribution`.

Extensions follow a lot of the conventions used in Django_ "apps," which
are loadable modules that may contain special files for defining database
models, administration UI forms, and more. We'll cover the important ones in
more detail later.


.. _Django: https://www.djangoproject.com/


Required Files
==============

At minimum, an extension requires the following files:

*  :ref:`setup.py <extension-example-files-setup.py>`
*  *extensiondir*/:ref:`__init__.py <extension-example-files-__init__.py>`
*  *extensiondir*/:ref:`extension.py <extension-example-files-extension.py>`

Let's go into each of these files and show some examples.


.. _extension-example-files-setup.py:

**setup.py**
   This is the file used to create the Python package. It defines the
   :ref:`Entry Point <extension-entry-point>` used to allow Review Board to
   find the extension, and contains other metadata. This is covered in detail
   in :ref:`extension-distribution`.

   Here's an example :file:`setup.py`:

   .. code-block:: python

      from reviewboard.extensions.packaging import setup
      from setuptools import find_packages


      setup(
          name='sample_extension',
          version='0.1',
          description='Description of extension package.',
          author='Your Name',
          packages=find_packages(),
          entry_points={
              'reviewboard.extensions': [
                  'sample_extension = sample_extension.extension:SampleExtension',
              ]
          },
      )


.. _extension-example-files-__init__.py:

sample_extension/**__init__.py**
   This file is needed in order for ``sample_extension`` to be a proper
   Python module. You will generally leave this blank.


.. _extension-example-files-extension.py:

sample_extension/**extension.py**
   This is the main module containing your extension, where the bulk of your
   work will go (at least initially). In here, you'll define a subclass of
   :py:class:`~reviewboard.extensions.base.Extension`, add any metadata, and
   handle any initialization of :ref:`extension hooks <extension-hooks>`.

   This will look something like:

   .. code-block:: python

      from reviewboard.extensions.base import Extension


      class SampleExtension(Extension):
          def initialize(self):
              # Your extension initialization code belongs here.

   Throughout the Extending Review Board guide, we'll cover the various things
   you may place in this file.


Optional Files
==============

You can put anything you want in your extension's top-level module directory
(and even create nested subdirectories of modules). There's a few filenames
that are special, though.

**models.py**
   An extension can provide custom Django models (which become tables in the
   database) in this file. The corresponding tables will be created in the
   database when the extension is loaded. See :ref:`extension-models` for more
   information.

**admin_urls.py**
   This file is used to define custom URLs in the administration UI. These
   are often used to create configuration pages for your extension, but they
   can really be used for any purpose.

   This file is only used when
   :py:attr:`~reviewboard.extensions.base.Extension.is_configurable` is set
   to ``True``.

   For more information, see :ref:`extension-configuration-urls`.

**admin.py**
   This file allows an extension to register its models (from
   :file:`models.py`) in its own section of the administration UI. This allows
   administrators to browse through the content of the models owned by your
   extension.

   This file is only used when
   :py:attr:`~reviewboard.extensions.base.Extension.has_admin_site` is set to
   ``True``.

   For more information, see :ref:`extension-admin-site`.
