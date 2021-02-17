.. _rbext:
.. program:: rbext

==============
The rbext Tool
==============

Review Board ships with a command line tool called :program:`rbext` that can
help you create and test your extension, helping you focus on writing new
features for Review Board.


.. _rbext-create:

rbext create
============

.. program:: rbext create

.. versionadded:: 3.0.4

:command:`rbext create` is used to create an initial extension, complete with
packaging. It can optionally set things up to distribute static files and to
enable configuration.

At its simplest, you can create an extension with:

.. code-block:: text

    $ rbext create --name "My Extension"

A ``my_extension`` package will be created with a basic, functioning extension
and packaging, ready to be modified.

There are several options available to customize the generation of your
initial extension:

.. option:: --name

   The name you want to give your extension. This should be a human-readable
   name, not a package name or a class name. Those can be provided separately,
   or will be generated from this name.

.. option:: --class-name

   Sets a specific class name for your extension's :ref:`main class
   <extension-class>`. This must be a valid Python class name, and must end
   with ``Extension``.

   If not set, a name will be generated based on the value passed in
   :option:`--name`.

.. option:: --package-name

   Sets a specific name to use for the package, instead of generating one
   from :option:`--name`.

.. option:: --package-version

   Sets a specific version to use for the package and extension. This will
   be stored in the :file:`setup.py` in your package. It defaults to "1.0".

.. option:: --summary

   Sets a summary for the package's :file:`setup.py`, :file:`README.rst` and
   for the extension information.

.. option:: --description

   Sets a longer description for the package's :file:`README.rst`.

.. option:: --author-name

   Sets the name of the author for the package's :file:`setup.py`. This can
   be an individual or the name of an organization/company.

.. option:: --author-email

   Sets the e-mail address of the author for the package's :file:`setup.py`.
   This can be any e-mail address suitable for contacting the developers of
   the package.

.. option:: --enable-configuration

   Whether to generate some files and options for providing a default form for
   configuring an extension. This will produce :file:`admin_urls.py` and
   :file:`forms.py` files, and set ``is_configurable = True`` on the
   extension.

   :ref:`Learn more <extension-configuration>` about how to customize the
   configuration of your extension.

.. option:: --enable-static-media

   Whether to generate some default static media directories and to enable
   default rules for CSS/JavaScript static media bundles for your extension.

   :ref:`Learn more <extension-static-files>` about how to work with static
   media bundles for your extension.


.. _rbext-test:

rbext test
==========

.. program:: rbext test

:command:`rbext test` is a handy tool for testing your extension, handling all
the hard work of setting up an in-memory Review Board environment and database
in which to run your test suite.

This is usually invoked like:

.. code-block:: text

    $ rbext test -e my_extension.extension.MyExtensionClass

See :ref:`our guide to testing extensions <testing-extensions>` for more
information on how to incorporate a test suite into your extension.

There's a few special arguments you may want to use:

.. option:: --app

   A Django app label to enable in your test environemnt. This can be
   specified multiple times.

   This can be combined with :option:`--extension` and :option:`--module`.

   .. versionadded:: 4.0

.. option:: -e, --extension

   The full Python class path of the extension class to test. This will set
   up the extension in your environment, loading all relevant Django apps,
   and locate your tests.

   This can be combined with :option:`--app` and :option:`--module`.

   .. versionadded:: 4.0

.. option:: -m, --module

   The name of the top-level module for your extension. This will look for
   any :file:`tests.py` anywhere within the module.

   This can be combined with :option:`--app` and :option:`--extension`.

.. option:: --pdb

   Opens a Python debugger on any failure or error.

   .. versionadded:: 4.0

.. option:: --tree-root

   The path to the root of your extension's source tree (where
   :file:`setup.py` lives). This defaults to the current directory.

.. option:: --with-coverage

   Whether to include coverage information. This is used to show what lines
   of your code have been invoked through the test suite, and which lines
   have not been included in tests. See :ref:`extensions-test-coverage`
   for examples.

   This requires the coverage_ module to be installed.

   .. versionadded:: 4.0

.. option:: -x, --stop

   Stops running tests after the first failure.

   .. versionadded:: 4.0


A list of modules/classes/functions to test can be included after any options.
See :ref:`extensions-running-unit-tests` on how to do this.

.. _coverage: https://pypi.python.org/pypi/coverage
