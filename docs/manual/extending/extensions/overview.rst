.. _extensions-overview:

========
Overview
========

Review Board's functionality can be enhanced by installing one or more
extensions. Writing and installing an extension is an excellent way to tailor
Review Board to your exact needs. Here are a few examples of the many things
you can accomplish by writing an extension:

* Modify the user interface, providing new links or buttons.
* Generate statistics for report gathering.
* Interface Review Board with other systems (e.g. an IRC bot).
* Add new API for efficiently gathering custom data from the database.
* Provide review UIs for previously unsupported types of files.

Extensions were introduced as an experimental feature in Review Board 1.7.
However, many of the features discussed here were added or changed in Review
Board 2.0.


.. _extension-generator:

Extension Boilerplate Generator
===============================

To help you get started writing an extension, the Review Board repository
provides a script to provide extension boilerplate. To run the generator,
check out the `Review Board tree`_ and run::

   ./contrib/tools/generate_extension.py


.. _`Review Board tree`: https://github.com/reviewboard/reviewboard/
