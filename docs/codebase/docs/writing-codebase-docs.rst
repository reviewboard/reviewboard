.. _writing-codebase-docs:

==============================
Writing Codebase Documentation
==============================

Documentation is very important to the project, whether in the form of user
documentation or class/function documentation. In recent years, we've been
making an effort to move to a standard documentation format for our code
across all the languages we work with.

Good codebase documentation offers many advantages:

* Well-written docs make it easier for us to understand your code and to give
  it a proper review.
* New contributors to the project will have an easier time understanding the
  responsibilities for the code they're working with, making it harder to
  break things.
* Third-parties wanting to write code against our public interfaces will have
  a better idea of how.

You'll be expected to write codebase docs for any contributions you have.
This guide will cover our
:ref:`content requirements <docs-content-requirements>`, the expected format
for :ref:`Python docs <docs-python-format>` and
:ref:`JavaScript docs <docs-js-format>`, and will cover the
:ref:`standard format <docs-standard-format>` we use for writing doc content.


.. _docs-content-requirements:

Content Guidelines
==================

Be Explicit and Clear
----------------------

Documentation should always strive to be explicit and thorough, explaining the
purpose of the file, class, function, etc. being documented well enough that
somebody new to the file (or somebody reading this online without access to
the source code) will have a good understanding of what's going on and how
things work.

Don't go so far as to describe the inner workings of the actual code itself
(that's what code comments are for), but do give a higher-level overview of
the code.

If you're having trouble writing the docs, or you're not sure your docs are
coming across right, grab another person or even a
`rubber duck <http://en.wikipedia.org/wiki/Rubber_duck_debugging>`_. Read your
docs to them or explain the class/function out loud. That'll help you solidify
your thoughts, making it more likely that other people will understand your
docs better.


Proofread
---------

We expect all documentation to be free of spelling errors, typos, major
grammatical problems, and to have correct punctuation.

Try to make sure your "voice" matches the other docs in our codebase, too.
This isn't always easy, but give it a shot.

We will review and offer suggestions if we find anything we'd like changed.


.. _docs-standard-format:

Standard Documentation Format
=============================

There are many ways out there in the world to structure documentation,
turning it into readable online docs. In order to ensure that things are
consistent, we've settled on one standard across our projects, which this
section will cover.

For formatting, we use ReST_ (reStructuredText), which is similar in many
ways to Markdown. This is used to apply basic formatting (bold, italic, etc.),
define links, lists, tables, and so on.

We generate our ReST-based documentation using Sphinx_, a Python documentation
generation tool with support for multiple languages.

For defining function arguments, return types, exceptions, etc., we use a
variant of the `Google Python Docstring`_ standard, which this will go into
further.


.. _ReST: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://www.sphinx-doc.org/en/stable/index.html
.. _Google Python Docstring:
   https://google.github.io/styleguide/pyguide.html#Comments


reStructuredText
----------------

reStructuredText, or ReST, is a bit like Markdown, in that it lets you apply
formatting and structured content in a standard, text-based way. It differs a
bit in how it does this, and it goes even further and offers a level of
extensibility for defining special formatting options.

We use an enhanced version of ReST, provided by Sphinx_, which offers a bunch
of additions for documenting source code. Most of these additions won't be
needed for most docs, but are there for the special cases.

You'll want to familiarize yourself with the `basics of ReST`_, the
`Sphinx ReST additions`_ and `Sphinx Domains`_ (which is used for codebase
docs).

.. _basics of ReST: http://www.sphinx-doc.org/en/stable/rest.html
.. _Sphinx ReST additions:
   http://www.sphinx-doc.org/en/stable/markup/index.html
.. _Sphinx Domains: http://www.sphinx-doc.org/en/stable/domains.html


Summary/Description Format
--------------------------

Practically everything you document is going to follow a one-line summary,
multi-line description format. The one-line summary (which must *not* wrap)
should briefly describe the purpose of the thing being documented, with the
optional multi-line description providing additional details and zero or more
:ref:`special sections <docs-special-sections>`.

For example::

    One-line summary.

Or::

    One-line summary.

    This is a multi-line description. It can span as many lines as you want,
    and contain contain blank lines, and special sections, like:

    See Also:
        * :py:class:`MyClass`


Examples in this section will be shown in a common format, like this. Please
refer to :ref:`docs-python-format` and :ref:`docs-js-format` for how to format
these docs in those languages.


.. _docs-special-sections:

Special Sections
----------------

Our documentation allows for special section headers that help document things
like function parameters, exceptions, etc. These are parsed when generating
the online docs, turning them into special blocks of HTML.

We use the following:

* :ref:`docs-section-args`
* :ref:`docs-section-attributes`
* :ref:`docs-section-example`
* :ref:`docs-section-model-attributes`
* :ref:`docs-section-note`
* :ref:`docs-section-option-args`
* :ref:`docs-section-raises`
* :ref:`docs-section-returns`
* :ref:`docs-section-see-also`
* :ref:`docs-section-yields`


.. _docs-section-args:

Args
~~~~

``Args`` documents a list of positional and keyword arguments for a
function/method, detailing their names, types, and descriptions.

These are in the form of::

    Args:
        param1 (type):
            Description of param1.

        param2 (type):
            Description of param2.


If a parameter is optional (due to having a default value in Python, or
allowing ``undefined`` in JavaScript), you can include a special indicator in
the type section::

    Args:
        param1 (type, optional):
            Description of param1.


The descriptions should describe what's expected of the parameter, including
any constraints.

If there's a default value, describe that as well. This usually comes in the
form of: ``Defaults to <value>``.

See :ref:`Python Value Types <docs-python-types>` and
:ref:`JavaScript Value Types <docs-js-types>` for the format of
argument types.


.. _docs-section-attributes:

Attributes
~~~~~~~~~~

``Attributes`` documents a list of attributes on a class. These are going to
be attributes not already covered by other documentation on the class (such as
those dynamically set during initialization of a class).

This follows the same format as :ref:`docs-section-args`::

    Attributes:
        attr1 (type):
            Description of attr1.

        attr2 (type):
            Description of attr2.


These should also contain any default values that may be applicable to the
attribute.


.. _docs-section-example:

Example/Examples
~~~~~~~~~~~~~~~~

``Example``/``Examples`` provides examples for function or class usage,
helping to clarify, for example, how to create a subclass of some special
class, or ways you might use a function.

This is in the format of::

    Example:
        .. code-block:: python

           class MyClass(MyBaseClass):
               def handle_foo(self):
                   # Implement this to do things when foo occurs.


If you have multiple examples to show, use the ``Examples`` header and write a
description before each code block::

    Examples:
        Running the operation without notifying on success:

        .. code-block:: javascript

           myOperation(42);


        Running the operation and listening for success/error results:

        .. code-block:: javascript

           myOperation(42, {
               success: function() { ... },
               error: function() { ... }
           });


This should come after most other sections, but before
:ref:`docs-section-see-also`.


.. _docs-section-model-attributes:

Model Attributes
~~~~~~~~~~~~~~~~

``Model Attributes`` documents attributes on JavaScript
:js:class:`Backbone.Model` subclasses. It's not used at all for Python.

This section shares the same exact format as
:ref:`docs-section-model-attributes`. See that and :ref:`docs-js-model-attrs`
for more information.


.. _docs-section-note:

Note/Notes
~~~~~~~~~~

``Note`` and ``Notes`` documents something note-worthy that should be
explicitly noticed in any generated documentation. This takes any kind of
content, and can appear anywhere in your docstring/doc comment (though usually
it'll appear before or after all other sections, wherever it's most
appropriate).

You can use either ``Note`` or ``Notes``, depending on what makes more sense.

For example::

    Note:
        This function signature is not currently API-stable, so use it with
        caution. It may change at any time.


.. _docs-section-option-args:

Option Args
~~~~~~~~~~~

``Option Args`` documents the contents of an ``options`` argument in a
JavaScript function. It's not used at all for Python.

This section shares the same exact format as :ref:`docs-section-args`. See
that and :ref:`docs-js-function-options` for more information.


.. _docs-section-raises:

Raises
~~~~~~

``Raises`` documents any exceptions that may be raised by this function.
It should cover all exceptions raised by the function and all exceptions
that are allowed to be raised by any function called within.

This uses the following format::

    Raises:
        path.to.ExceptionName:
            Description of why the exception would be raised.

        path.to.ExceptionName:
            Description of why the exception would be raised.


For Python, this should be the full class path for the exception (or the raw
exception name if using a standard exception class or one defined within the
same module).

The description should give the reader enough information to know exactly why
that exception would be raised.


.. _docs-section-returns:

Returns
~~~~~~~

``Returns`` documents the return value of a function. It includes the return
type and a description of the value.

This uses the following format::

    Returns:
        type:
        Description of the return value(s).

If the function can return multiple types of values (say, a tuple of
information, or a dictionary of various keys, or may return something like
``None`` or ``undefined``), then those values should be documented, along with
their conditions.

Everything after the return type is free-form, so you are free to provide
paragraphs of content or even tables or examples, if needed.


.. _docs-section-see-also:

See Also
~~~~~~~~

``See Also`` documents other classes, functions, modules, or even external
links that the reader might be interested in.

This is a free-form section, so it can contain any content. Often times,
you'll have a bullet list of related links/references, but this really depends
on the use.

For example::

    See Also:
        The following classes are heavily related to the operation of this
        function:

        * :py:class:`SomeClass`
        * :py:class:`AnotherClass`

        You'll also want to check these related functions, which must be used
        along with this:

        :py:func:`some_func`
        :py:func:`another_func`


.. _docs-section-yields:

Yields
~~~~~~

``Yields`` works like :ref:`docs-section-returns`, but is used for functions
that work as generators, yielding values as it executes instead of returning
all at once. That's useful for Python today, and will be useful down the road
for JavaScript (once generators are more common there).

This uses the following format::

    Yields:
        type:
        Description of the yielded value(s).

If the function can yield multiple types of values (say, a tuple of
information, or a dictionary of various keys, or may yield something like
``None`` or ``undefined``), then those values should be documented, along with
their conditions.

Everything after the yield type is free-form, so you are free to provide
paragraphs of content or even tables or examples, if needed.


Files/Modules
-------------

The top of a source file should define documentation on the purpose of that
file. It must begin with a one-line summary, and can then have multiple lines
of content. The content should provide enough information needed to give a
user an idea of what that module is for and how they'd use it, possibly
linking to other related module docs.

For example, the top of a file might contain::

   Database models for the foo module.

   This module contains database models used to store state related to foo.
   The main model you'll interact with is :py:class:`FooState`. Other models
   are managed through that.

   This consists of:

   * :py:class:`FooState`
   * :py:class:`AnotherHappyModel`


JavaScript files that contain more than a single class should also have
a doc comment. Unlike Python, if they only contain a single class, this
can be left out. This is largely due to the difference in how Python
docstrings and JavaScript doc comments are placed with respect to the code
they're documenting.


Classes
-------

Classes follow the standard single-line/multi-line model, and should be
explicit about the purpose and usage of the class.

Class documentation have a couple special sections they may want to use:

* ``Attributes``
* ``Model Attributes`` (JavaScript models only)

The ``Attributes`` section lists all attributes on the class that aren't
otherwise documented directly on the class. This means instance variables
that the consumer of the class may need to know about that are set during
initialization of the class.

For example::

    One-line summary.

    Multi-line description.

    Attributes:
        enabled (bool):
            The enabled state for the object. Defaults to ``true``.

        text (unicode):
            The current text for the object. Defaults to an empty string.


``Model Attributes`` is only used in JavaScript. See the section on
:ref:`documenting JavaScript models <docs-js-model-attrs>`.


.. _docs-python-format:

Writing Python Docs
===================

Docstrings
----------

We generally follow :pep:`0257` (Docstring Conventions). Docstrings are used
for:

* Module headers
* Classes
* Functions/methods

You'll always write a docstring using this format:

.. code-block:: python

   """One-line summary."""

Or:

.. code-block:: python

   """One-line summary.

   Multi-line description.
   """

The beginning line must always be on the same line as the opening ``"""``,
and must not wrap.

For module headers and classes, you need to have a blank line after the last
``"""`` and the rest of the module/class body. This is not the case for
function/method docs.

See :ref:`docs-standard-format` below for how to structure the content of
these docstrings.


Attributes and Constants
------------------------

You'll also need to document any global variables, constants, or attributes on
a class, but you won't use ``"""`` for this. Instead, you'll use the special
``#:`` notation before the variable. This must follow the same general format
of the above. For example:

.. code-block:: python

   #: The unique ID for the object's registration.
   #:
   #: This ID will be checked when registering the object. If an existing
   #: object with the same ID is already registered, an error will occur.
   #:
   #: If left as ``None`` (the default), this will be automatically computed
   #: from the full class's path.
   obj_id = None


.. _docs-python-types:

Value Types
-----------

When listing attributes or arguments to a function (using
:ref:`docs-section-attributes`, :ref:`docs-section-args`, etc.), you'll need
to specify the types that are expected. For example, they may include a
standard Python type, like:

* ``complex``
* ``dict``
* ``file``
* ``float``
* ``int``
* ``list``
* ``long``
* ``set``
* ``str``
* ``unicode``

There are many more out there.

It may also include a class name (specifying the full class path) or a type
defined within the codebase. This indicates an instance of that class should
be used. Do *not* use this to specify that a class itself is to be passed. For
that, specify ``type`` instead.

To specify a function (or other callable object) as a type, use ``callable``.

To specify a list or set of a given type, use ``list of <type>`` or
``set of <type>``.


Example
-------

Putting it all together:

.. code-block:: python

   """Summary of the module.

   Additional information that may be useful.
   """

   import os


   #: A list of my very important numbers.
   #:
   #: Try not to play these in the lottery.
   NUMBERS = [4, 8, 15, 16, 23, 42]

   #: Whether to use debug mode.
   DEBUG = False


   class MyClass(object):
       """Description of the class.

       Additional details.
       """

       #: The ID this class will use for registration.
       registration_id = 'my-class'

       def __init__(self):
           """Initialize the class."""
           self._state = None


.. _docs-js-format:

Writing JavaScript Docs
=======================

There isn't a winning standard out there for JavaScript documentation the way
there is for Python, so we use standard comments for this in the following
forms:

.. code-block:: javascript

   /**
    * Single-line summary.
    */

Or:

.. code-block:: javascript

   /**
    * Single-line summary.
    *
    * Multi-line description.
    */

Note that these start with ``/**``, and not ``/*``. This is how we will
differentiate standard comments from doc comments.

Unlike with Python docstrings (which are placed within the body of a class
or method), you will not place a blank line between the end of the docs and
any following code.

You should document all the following:

* Classes
* Functions
* Attributes/constants

.. note::

   It is generally not necessary to document a file, as most files have a
   single class, and documentation can be pulled from that. However, if the
   file is more complex, it should also consist of a doc comment at the very
   top.


.. _docs-js-model-attrs:

Documenting Models
------------------

Our JavaScript codebases use Backbone.js_, and as part of this, they define
models. Models are objects that track state (in the form of "model
attributes") and logic. These model attributes are important to document,
and have a special convention.

Model attributes are documented by including a ``Model Attributes:`` section
in the class docs. For example, this looks like:

.. code-block:: javascript

   /**
    * Summary of the model.
    *
    * Some additional details that may be useful.
    *
    * Model Attributes:
    *     enabled (boolean):
    *         Whether the object is enabled. Defaults to ``true``.
    *
    *     text (string):
    *         The text used for display. Defaults to an empty string.
    */
   MyModel = Backbone.Model.extend({
       defaults: {
           enabled: true,
           text: ''
       },

       ...
   });

Each entry under ``Model Attributes`` follows the standard
:ref:`docs-section-attributes` format. It should be in alphabetical order.


.. _Backbone.js: http://backbonejs.org/


.. _docs-js-function-options:

Documenting Function Options
----------------------------

It's common for functions to take an ``options`` parameter that contains
additional options passed to the function. This is a dictionary/object of
key/values passed to the function, which acts as either optional or required
keyword arguments.

We have a special convention for documenting any argument named ``options``.
You will continue to document this in the list of function arguments, but will
document the possible options under a special ``Option Args`` section.

For example:

.. code-block:: javascript

   /**
    * Summary of the function.
    *
    * Some additional details that may be useful.
    *
    * Args:
    *     someValue (boolean):
    *         Some boolean value that this function cares about.
    *
    *     options (object):
    *         Option arguments controlling the behavior of the function.
    *
    *     context (object):
    *         The context passed to any callback functions.
    *
    * Option Args:
    *     error (function):
    *         An error callback called when the operation fails.
    *
    *     identifier (string):
    *         An identifier for this operation.
    *
    *     success (function):
    *         A success callback called when the operation is completed.
    */
   function myFunction(someValue, options, context) {
       ...
   }


.. _docs-js-types:

Value Types
-----------

When listing attributes or arguments to a function (using
:ref:`docs-section-attributes`, :ref:`docs-section-args`, etc.), you'll need
to specify the types that are expected. These may include the following basic
types:

* ``boolean``
* ``function``
* ``number`` (integers, floats)
* ``object``
* ``string``

You can also provide the name of a native class, custom class/prototype, DOM
node type, etc.  For example:

* ``Array``
* ``Element``
* ``Window``
* ``jQuery``
* ``MyApp.MyModel``


Example
-------

Here's how you might document a file:

.. code-block:: javascript

   /**
    * Summary of the class.
    *
    * Some additional details that might be useful.
    *
    * Model Attributes:
    *     text (string):
    *         The text used for display.
    */
   MyModel = Backbone.Model.extend({
       defaults: {
           text: ''
       },

       /** The default value for a thing. */
       DEFAULT_THING: [1, 2, 3],

       /**
        * Initialize the model.
        *
        * Some useful information on anything special this does.
        */
       initialize: function() {
           ...
       }
   });
