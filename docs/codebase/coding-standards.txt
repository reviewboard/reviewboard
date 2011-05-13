.. _coding-standards:

================
Coding Standards
================

In general, Review Board follows the :pep:`8` coding style for Python code.
This is a pretty standard coding style for Python applications, meaning Review
Board's code ends up looking similar to that of many other Python
applications.

While :pep:`8` is a good read, this document will go over the major highlights
of Review Board's coding style.


Code Layout
===========

Indentation
-----------

Indent 4 spaces per indentation level.
It's important to use spaces. Do *not* use tabs.


Line Length
-----------

Lines should be shorter than 80 characters.
Multi-line statements should ideally be broken up into separate lines
if possible. In cases where this isn't possible or clean, break them up
using either parenthesis or by ending the line with a ``\``.

For example:

.. code-block:: python

    if (some_long_check(param1, param2, param3, param4) and
        another_check(param1, param2, param3)):
        ...


Spacing
-------

Use 2 blank lines before/after/between each class or top-level function.

Use 1 blank line before/after each if/for/while block.

Use 2 blank lines after the ``import`` statements at the top of the file.


Directory Layout
================

Pieces of code that serve fundamentally different purposes should live in
their own subdirectories of :file:`reviewboard`. For example, diff viewer
functionality lives within the :file:`reviewboard/diffviewer` directory, while
code to talk to repositories lives within the :file:`reviewboard/scmtools`
directory. These directories are referred to as "app directories."


App Directory Files
-------------------

App directories may contain some of the following filenames or directories:

* **admin.py:**
   Administration UI definitions for database models. There's usually a
   one-to-one mapping between classes in :file:`admin.py` and in
   :file:`models.py`.

* **feeds.py:**
   Code for definining RSS/Atom feeds for certain objects.

* **forms.py:**
   Backend implementations for web forms. These are responsible for
   representing the fields of the form, handling all validation logic,
   and creating or updating any objects based on the provided form data.

* **models.py:**
   Code for database models. These are Python objects that are transformed
   into tables in the database behind the scenes. These can contain functions
   for operating on the objects.

* **managers.py:**
   Managers for the database models. These are generally responsible for
   creating and returning one or more models.

* **tests.py:**
   Unit tests for the module.

* **urls.py:**
   URL mapping definitions. These point URLs to views in views.py.

* **views.py:**
   Views are functions that return HTML responses when invoked. These are
   what's used to render the pages sent to the browser. Views usually
   make use of templates_ when rendering code.


.. _templates:

Templates
---------

Template files contain content and some basic logic for use in rendering web
pages, e-mails, and other files. They live in the :file:`reviewboard/templates`
tree, and are usually separated according to app directory names.


Naming
======

Class names should be in CamelCase. For example, ``ReviewRequest`` or
``SCMTool``.

Function names should be in lowercase, separated by underscores. For
example, ``get_bugs``.

Constants should be in uppercase, separated by underscores. For
example, ``INVALID_REPOSITORY``.
