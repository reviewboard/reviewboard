.. _extensions-overview:
.. _writing-extensions:

======================
Extending Review Board
======================

Because development workflows can vary widely, Review Board is built to be
highly extensible. Extensions are third-party packages that can improve the
product, add new features, enhance existing ones, change the look and
feel, and integrate with other services.

Here are just a few examples of what you can accomplish by writing an
extension:

* Modify the user interface to provide new review request actions or fields.
* Collect statistics and generate reports.
* Connect Review Board with other systems (new chat systems, version control,
  bug trackers, etc.).
* Add new API for collecting or computing custom data.
* Implement review UIs for previously unsupported types of files.

This guide will cover some of the basics of extension writing, and provide a
reference to the Review Board codebase.


Getting Started
===============

For a step-by-step guide to getting started with creating your extension, see
:ref:`extensions-making`.


.. _extensions-examples:

Full Examples
=============

The following are in-depth guides on some of the more common types of
extensions you might be interested in building:

* :ref:`extension-review-request-fields`
* :ref:`extension-review-ui-integration`
* :ref:`extension-resources`
* :ref:`writing-auth-backends`

.. todo:
   * Adding support for a new version control system
   * Integrating with additional services
   * Implementing custom review request approval rules
   * Adding new actions


.. _extensions-reference:

Extension Reference
===================

These pages provide in-depth information about the extension framework and its
APIs:

.. toctree::
   :maxdepth: 2

   extensions/file-layout
   extensions/class
   extensions/configuration
   extensions/models
   extensions/static-files
   extensions/js-extensions
   extensions/testing
   extensions/distribution
   extensions/hooks/index


Code Base Documentation
=======================

When writing extensions, you can use the same Review Board classes and methods
that we use in the product ourselves.

Please note that not all of these are guaranteed to be API-stable or fully
documented.


Review Board
------------

* :ref:`Review Board Code Base Reference <reviewboard-coderef>`


Djblets
-------

* :ref:`Djblets Development Guides <djblets-guides>`
* :ref:`Djblets Code Base Reference <djblets-coderef>`


.. toctree::
   :hidden:

   extensions/index
   extensions/making-an-extension
   extensions/rbext
   extensions/hooks/index
   extensions/js-hooks/index
   extensions/review-request-fields
   extensions/review-ui
   auth-backends
   legacy-auth-backends
   extensions/webapi
   coderef/index
