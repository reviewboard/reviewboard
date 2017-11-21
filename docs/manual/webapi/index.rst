.. _webapiguide:

=============
Web API Guide
=============

Review Board provides a REST API that allows clients to look up information
and perform operations on behalf of a user. This can be used by in-house
scripts, third-party services, IDE plugins, and other tools to automate Review
Board or to make use of its data in whole new ways.

This guide will cover how to use Review Board's API and provide a full
reference to all the API resources available.


Getting Started
===============

Before you use the API, you'll need to know some of the basic terminology and
how requests/responses are handled.

* :doc:`Overview of the API <2.0/overview>`

  * :ref:`What are resources? <webapi2.0-overview-resources>` -
    How data is represented in the API, and how they connect to each other.

  * :ref:`Making requests <webapi2.0-overview-requests>` -
    How to form an API request.

  * :ref:`Processing responses <webapi2.0-overview-responses>` -
    How responses should be handled and parsed by the client.

* :doc:`Authentication <2.0/authenticating>` -
  Logging in to Review Board's API using passwords or API tokens, and
  clearing existing login sessions.

* :doc:`OAuth2 applications <2.0/oauth2>` -
  Registering your service as an OAuth2 application, giving users a secure
  and convenient way of connecting it to their accounts.

* :doc:`Glossary of terms <2.0/glossary>`


API Bindings
============

When possible, we recommend using supported API bindings instead of talking to
the API directly. This will help keep your code more manageable and leave bug
fixes to someone else.

We provide the following bindings:

* :ref:`Python bindings (via RBTools) <rbtools-api>`


Working with Special Data
=========================

* :ref:`Rich text fields <webapi2.0-text-fields>` -
  Working with textual data (such as from review request fields) and how to
  convert to Markdown and HTML.

* :ref:`Extra data <webapi2.0-extra-data>` -
  Storing and retrieving custom extra data on resources that support it, for
  use in your client or :ref:`extension <writing-extensions>`.


Available Resources
===================

There are a couple ways to look at the available list of resources available
in Review Board.

.. toctree::
   :maxdepth: 2

   Full resource tree <2.0/resources/resource-tree>
   Resources by category <2.0/resources/index>


Available Errors
================

.. toctree::
   :maxdepth: 2

   All errors <2.0/errors/index>


.. comment: Some hidden toctrees for building the structure properly.

.. toctree::
   :hidden:

   2.0/index
