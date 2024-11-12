.. _extension-distribution:

======================
Extension Distribution
======================


.. _extension-packages:

Python Packages
===============

Extensions are packaged and distributed as Python packages (:term:`Python
Wheels`). This allows for automatic detection of installed extensions,
packaging of static files, and dependency checking.


Extension packages are pretty much like any other Python package. It uses
a :ref:`pyproject.toml` file to define your package contents, along with
Review Board's extension build backend.

There are a few additional features that are provided by Review Board, which
will be covered in this guide.


.. _extension-entry-point:

Defining an Entry Point
-----------------------

To facilitate the auto-detection of installed extensions, a
``reviewboard.extensions`` :term:`Python Entry Point` must be defined for each
:ref:`extension class <extension-class>` in your package. These are defined
in your :ref:`pyproject.toml` like so:

.. code-block:: toml

   [project.entry-points."reviewboard.extensions"]
   sample_extension = 'sample_extension.extension:SampleExtension'

This tells the Python packaging system that there's a Review Board extension
named ``sample_extension`` that points to
:py:class:`sample_extension.extension.SampleExtension`. Once the package is
installed, Review Board will be able to use this registered entry point to
locate your extension.

Here is an example of a full :ref:`pyproject.toml` file defining this entry
point:

.. code-block:: toml

   [build-system]
   requires = [
       # Update this for the target version of Review Board.
       'reviewboard~=7.1',

       'reviewboard[extension-packaging]',
   ]
   build-backend = 'reviewboard.extensions.packaging.backend'


   [project]
   name = 'sample_extension'
   version = '1.0'
   description = 'Description of your extension package.'
   authors = [
       {name = 'Your Name', email = 'your-email@example.com'}
   ]

   # Your Python package dependencies go here. Don't include "ReviewBoard" in
   # this list.
   dependencies = [
   ]

   # For a full list of package classifiers, see
   # https://pypi.python.org/pypi?%3Aaction=list_classifiers
   classifiers = [
       'Development Status :: 3 - Alpha',
       'Environment :: Web Framework',
       'Framework :: Review Board',
       'Operating System :: OS Independent',
       'Programming Language :: Python',
   ]


   # This tells Review Board where to find your extension. You'll need to
   # change the "sample_extension = ..." based on your extension ID and
   # module/class path.
   [project.entry-points."reviewboard.extensions"]
   sample_extension = 'sample_extension.extension:SampleExtension'


   # This section tells Python where to find your extension. You shouldn't
   # need to change these.
   [tool.setuptools.packages.find]
   where = ['.']
   namespaces = false


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
------------------------------

If your package needs to ship templates or other data files, you'll need
to include these in your package's :file:`MANIFEST.in` file. Please see
the `MANIFEST.in documentation
<https://docs.python.org/2/distutils/sourcedist.html#manifest-template>`_ for
the format of this file.

This file will live in the same directory as your :ref:`pyproject.toml`.

Your :file:`MANIFEST.in` might look something like this::

    include sample_extension/templates/*.html
    include sample_extension/templates/*.txt
    include README
    include LICENSE


.. _extension-package-dependencies:

Dependencies
------------

Your package can specify a list of dependencies, which are other packages that
will be installed when your package is installed. This is specified as
``dependencies`` in :ref:`pyproject.toml`.

.. warning::

   Don't specify ``reviewboard``, ``djblets``, ``Django``, or any other Review
   Board dependency in your own list. While your package may indeed require
   Review Board or one of its dependencies, this runs the risk (in certain
   cases) of accidentally upgrading all or part of your Review Board install
   when installing your package.

For example, your :ref:`pyproject.toml` may include:

.. code-block:: toml

   [project]
   ...

   dependencies = [
      'PythonPackageIDependOn>=0.1'
   ]

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

You're now ready to build your package! Just follow these steps:

1. Make sure you have Python's :pypi:`build` package installed:

   .. code-block:: console

      $ pip3 install build

   You only have to do this once.

2. Build your source distribution and wheel package from the top of your
   extension's source tree:

   .. code-block:: console

      $ python3 -m build .

   That will produce builds in the :file:`dist/` directory.


.. _extension-package-developing:

Developing Against Your Package
-------------------------------

If you're actively testing your package against Review Board, you don't want
to keep rebuilding the package every time you make a change. Instead, you'll
want to install your package in "editable" mode:

.. code-block:: console

   $ pip3 install -e .

This allows you to make changes to your extension and test it without building
and installing new packages.  It's the recommended way to iterate on your
package while you test.

We recommend only testing editable packages against a Review Board development
server, and not against a production server.
