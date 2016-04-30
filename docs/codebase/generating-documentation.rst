.. _generatingdocumentation:

========================
Generating Documentation
========================

This guide will show how to build the local documentation. These steps have
been tested on Linux.

The documentation resides in the ``/reviewboard/docs/manual`` directory

Building and organizing documentation is done through Sphinx. You can
install Sphinx via::

    $ pip install sphinx

You are now ready to generate the documentation. To do so, run the following::

    $ make html

To access the newly generated documentation, browse to
``/reviewboard/docs/manual/_build/html`` and open the index.html file in a
browser.
