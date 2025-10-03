.. _extensions-making:

===============================
Making a Review Board Extension
===============================


Development Environment
=======================

Writing Review Board extensions requires having a Review Board development
environment (**not** a regular production installation). For instructions on
how to set this up, see the `getting started guide`_.


After following that guide, you should have a Python Virtual Environment which
contains all the Review Board packages, and you should be able to run the
Django development server:

.. code-block:: console

    $ ./contrib/internal/devserver.py

This will run a local instance of Review Board on http://localhost:8080/


.. _getting started guide: https://reviewboard.notion.site/Getting-Started-da208d46de1d47d8b38e8b5ddcb3dd44


Creating an Extension Package
=============================

Review Board extensions are distributed as Python packages.

The :ref:`rbext-create` command is the quickest way to create the boilerplate
package setup for your new extension.

.. code-block:: console

   $ rbext create \
       --name "Sample Review Board Extension" \
       --package-name sample-extension \
       --class-name SampleExtension


This will create a new directory named ``sample-extension`` that contains the
basic framework for your new extension. Inside that directory are several
files, but the two most important are:

:ref:`pyproject.toml <extension-example-files-pyproject.toml>`:
    The python package info. This defines your Python package, its metadata,
    and the :ref:`Entry Point <extension-entry-point>`, which allows Review
    Board to discover your extension.

* :ref:`sample-extension/extension.py <extension-example-files-extension.py>`:
    The main module containing your extension, where the bulk of your work
    will go (at least initially).

See :ref:`extensions-package-layout` for more details on these.

.. note::

   If you're using :command:`rbext` from Review Board 7.1 or newer, the resulting
   Python package will use a `PEP517`_-compatible :file:`pyproject.toml`. On older
   versions, it will create a :file:`setup.py` for the package.


.. _PEP517: https://peps.python.org/pep-0517/


Installing for Development
==========================

When developing your extension, it's most convenient to install the package into
your Python Virtual Environment in "editable" mode. This allows you to iterate on
your package without needing to rebuild and install wheel packages each time.

To do this, inside the ``sample-extension`` directory, run:

.. code-block:: console

   $ pip3 install -e .


Activating the Extension
========================

After installing the extension in development mode, you should be able to open
up the admin site in your devserver, select :guilabel:`Extensions`, and see
your new extension in the list. If there are failures, you may see an error
message in this list, and any exception backtraces will be visible in the
console that you're running the devserver in.

Click :guilabel:`Enable` to enable your new extension.

The Review Board devserver will watch your source files as you make changes to
your extension, so you can usually just reload pages in the browser without
needing to restart the devserver.


Implementing Your Extension
===========================

At this point, you should have a working development environment and extension
package, but it doesn't actually do anything.


Extension Hooks
---------------

Extensions connect to Review Board through "hooks." There are many different
types of hooks to accomplish different tasks.

Hooks are used by instantiating them in your extension's ``initialize`` method:

.. code-block:: python

   from django.urls import include, path
   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import URLHook


   class SampleExtension(Extension):
       def initialize(self) -> None:
           urlpatterns = [
               path('sample_extension/', include('sample_extension.urls')),
           ]

           URLHook(self, urlpatterns)

See :ref:`extension-hooks` for details on the available functionality.


Adding API Resources
--------------------

Extensions can also provide new API resources. This is not done via a hook, but
by specifying a list of resource classes inside of your extension class. See
:ref:`extension-resources` for details.


Next Steps
----------

Now that you have the extension framework ready, check out our
:ref:`extensions-examples` and the :ref:`extensions-reference`.
