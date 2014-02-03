===========
File Layout
===========

Extensions must follow a certain file structure in order to be recognized and
loaded by Review Board. They are distributed inside Python Egg packages, which
must follow a few conventions. See :ref:`extension-python-egg` for more
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
   Review Board extensions. For example:

   .. code-block:: python

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
   be defined here. For example:

   .. code-block:: python

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
