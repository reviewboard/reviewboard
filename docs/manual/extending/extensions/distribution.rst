.. _extension-distribution:

======================
Extension Distribution
======================


.. _extension-packages:

Python Packages
===============

Extensions are packaged and distributed as Python packages (:term:`Python
Eggs` or :term:`Python Wheels`). This allows for automatic detection of
installed extensions, packaging of static files, and dependency checking.


Extension packages are pretty much like any other Python package. It uses
:py:mod:`setuptools` and a :file:`setup.py` file to define the package
contents and to build the package. There are a few additional features that
are provided by Review Board, which will be covered in this guide.


.. _extension-entry-point:

Defining an Entry Point
-----------------------

To facilitate the auto-detection of installed extensions, a
``reviewboard.extensions`` :term:`Python Entry Point` must be defined for each
:ref:`extension class <extension-class>` in your package. These are defined
like so:

.. code-block:: python

      entry_points={
          'reviewboard.extensions': [
              'sample_extension = sample_extension.extension:SampleExtension',
          ],
      },

This tells the Python packaging system that there's a Review Board extension
named ``sample_extension`` that points to
:py:class:`sample_extension.extension.SampleExtension`. Once the package is
installed, Review Board will be able to use this registered entry point to
locate your extension.

Here is an example of a full :file:`setup.py` file defining this entry point:

.. code-block:: python

   from reviewboard.extensions.packaging import setup
   from setuptools import find_packages


   setup(
       name='sample_extension',
       version='0.1',
       description='Description of extension',
       author='Your Name',
       packages=find_packages(),
       entry_points={
           'reviewboard.extensions': [
               'sample_extension = sample_extension.extension:SampleExtension',
           ],
       },
   )


.. _extension-package-static-files:

Packaging Static Media Files
----------------------------

Packages that contain CSS or JavaScript should define those in the extension
class's :py:attr:`~reviewboard.extensions.base.Extension.css_bundles` and
:py:attr:`~reviewboard.extensions.base.Extension.js_bundles` dictionaries.
These bundles will be automatically compiled, minified, and packaged for you.
There's nothing else you need to do.

See :ref:`extension-static-files` for more information on bundles.


.. _extension-package-data-files:

Packaging Templates/Data Files
-----------------------------------

If your package needs to ship templates or other data files, you'll need
to include these in your package's :file:`MANIFEST.in` file. Please see
the `MANIFEST.in documentation
<https://docs.python.org/2/distutils/sourcedist.html#manifest-template>`_ for
the format of this file.

This file will live in the same directory as your :file:`setup.py`.

Your :file:`MANIFEST.in` might look something like this::

    include sample_extension/templates/*.html
    include sample_extension/templates/*.txt
    include README
    include LICENSE


.. _extension-package-dependencies:

Dependencies
------------

Your package can specify a list of dependencies, which are other packages that
will be installed when your package is installed. This is specified as an
``install_requires`` parameter to
:py:func:`~reviewboard.extensions.packaging.setup`. See the `official
documentation <https://packaging.python.org/requirements/#install-requires>`_
for how to specify dependencies.

.. warning::

   Don't specify ``reviewboard``, ``djblets``, ``Django``, or any other Review
   Board dependency in your own list. While your package may indeed require
   Review Board or one of its dependencies, this runs the risk (in certain
   cases) of accidentally upgrading all or part of your Review Board install
   when installing your package.

Your :file:`setup.py` might look like:

.. code-block:: python

   from reviewboard.extensions.packaging import setup
   from setuptools import find_packages


   setup(
       name='sample_extension',
       version='0.1',
       description='Description of extension',
       author='Your Name',
       packages=find_packages(),
       entry_points={
           'reviewboard.extensions': [
               'sample_extension = sample_extension.extension:SampleExtension',
           ],
       },
       install_requires=[
           'PythonPackageIDependOn>=0.1',
       ],
   )

In addition, extensions can have a run-time dependency on another extension,
forcing that extension to be enabled when yours is enabled. This is done by
specifying the required extensions' IDs in the
:py:attr:`~reviewboard.extensions.base.Extension.requirements` list. For
example:

.. code-block:: python

   class SampleExtension(Extension):
       requirements = [
           'other_extension.extension.OtherExtension',
       ]


.. _extension-package-build-options:

Building a Package
------------------

You're now ready to build your package! Before you do, let's talk setup and
deployment options.

.. note::

   If you're running Review Board 2.5.7 or older, and you're working with
   static media files, you'll need to install a couple of modules using
   `npm <https://docs.npmjs.com/getting-started/installing-node>`_::

       $ sudo npm install -g less uglifyjs

If you're looking to distribute your package publicly (such as on the `Python
Package Index`_, you'll want to build this as a Wheel, Egg, and maybe a Source
Distribution ("sdist"). You can build all three with one command::

    $ python setup.py bdist_wheel bdist_egg sdist

That will produce builds in the :file:`dist/` directory.

If this is for internal use, you can get away with just one package format.
We recommend Wheels, as these are the new standard for Python packaging. You
can build just the Wheel by running::

    $ python setup.py bdist_wheel

.. note::

   If you get an error about ``bdist_wheel`` not being a valid command, you
   will need to update your ``pip`` package and install ``wheel``::

       $ pip install -U pip
       $ pip install wheel


.. _Python Package Index: https://pypi.python.org/pypi/


.. _extension-package-developing:

Developing Against Your Package
-------------------------------

If you're actively testing your package against Review Board, you don't want
to keep rebuilding the package every time you make a change. Instead, you'll
want to install your package in development mode::

    $ python setup.py develop

This basically tells the Python packaging system that the installed package
lives in your source tree. The entry points will be registered and you'll be
able to enable the extension in Review Board. It's the recommended way to
iterate on your package while you test.

.. note::

   Due to some differences in how the package is prepared, this will require
   testing against a Review Board development server, instead of a production
   install.
