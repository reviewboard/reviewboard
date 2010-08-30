========
Overview
========

Review Board's API is based on standard HTTP requests (GET, POST, PUT, and
DELETE).

All requests are made to resources on the server. These resources are just
URLs beginning with ``/api/``.

Review Board makes use of HTTP status codes for responses. Some of these
may contain additional data in JSON_, XML, or other formats.

.. _JSON: http://www.json.org/


Resources
=========

In Review Board's API, every piece of data exists in usually one location
within a "resource." A resource is just a fixed location containing data,
encoded in JSON, XML, or another format, depending on the request.

Resource payloads in JSON or XML format have a main key (or tag) with the name
of the resource, and the content within it.


Resource URLs
-------------

Resources are arranged in consistent, clean URLs underneath ``/api/``. The
top-level "root" resource is at ``/api/`` and is used as a starting point for
finding other resources.

It's highly recommended that clients browse through the resources by following
their links, rather than hard-coding the paths. This will help keep your
client forward-compatible with future versions of Review Board, in case any
of these paths end up changing.


Hyperlinks
----------

Resources are linked together using hyperlinks in the payload. A resource
will often have a ``links`` key with keys for each thing that links off of it.
These will in turn have keys for the URL and for the HTTP method that works
on that URL.

Often, the keys in ``links`` will be the name of the resource, but there
are some special keys:

* ``create`` - A link to the resource list that an HTTP POST can be made on to
  create a new resource.
* ``delete`` - A link to the resource that an HTTP DELETE can be made on to
  delete the resource.
* ``next`` - A link to the next resource (or list of resources) in a list.
* ``prev`` - A link to the previous resource (or list of resources) in a list.
* ``self`` - A link to the official place for the resource. This will be the
  resource the link is in, not necessarily the resource accessed on
  the page (think nested resources in a payload).
* ``update`` - A link to the resource that an HTTP PUT can be made on to
  update the resource.

For example:

.. code-block:: javascript

    {
      links: {
        self: {
          href: '/path/to/whatever',
          method: 'GET'
        },
        create: {
          href: '/path/to/whatever',
          method: 'POST'
        },
        some_sub_resource: {
          href: '/path/to/whatever/some-sub-resource',
          method: 'GET'
        }
      }
    }


Making Requests
===============

HTTP Methods
------------

All requests to a resource are made using standard HTTP methods. The type
of request depends on the method used. Not all resources respond to all
methods, and any invalid method used on a resource will result in a
405 Method Not Allowed.

``GET`` requests are used when retrieving information. These requests will
never cause data to be modified on the server.

``POST`` requests are used for posting brand new content, such as uploading
a diff or creating a review request. The supplied content must be represented
as multi-part form data.

``PUT`` requests are used to update an existing resource. For example,
changing the summary of a review request's draft. Like ``POST`` requests,
the new content must be represented as multi-part form data. However, only
the fields that the client wants to change need to be specified. Any fields
not specified will be left alone.

``DELETE`` requests are used to delete a resource. A deleted resource cannot
be undeleted.


MIME Types
----------

Review Board can return content in different formats. In order to control
which format your client receives the data in, you should make use of
HTTP Accept headers.

An HTTP Accept header lists the mimetypes that the client wishes to receive.
The list is comma-separated and can contain multiple mimetypes, though
typically a client will only need to specify one or two.

The most common mimetypes your client may want to handle are
:mimetype:`application/json` and :mimetype:`application/xml`, though some
resources may be able to return custom data in mimetypes other than these.

An example of this header might be::

    Accept: application/json, */*

The ``*/*`` matches any mimetype. The above header would tell Review Board
to return JSON preferably, but anything is fine.

You can also specify priority levels by appending :samp:`;q={priority}` to the
mimetype, where :samp:`{priority}` is the priority level between 0 and 1. A
value of 0 means that the server should never send that mimetype.

For example::

    Accept: application/json;q=1, text/plain;q=0.2, application/xml;q=0, */*

In this example, JSON is preferred. Plain text is okay, but the client isn't
very excited about it. Anything else is okay, as long as it's not XML.


Responses
=========

HTTP Status Codes
-----------------

Every response has an HTTP status code. The following are used:

+------------------+--------------+-----------------------------------------+
| HTTP Status Code | Name         | Description                             |
+==================+==============+=========================================+
| 200              | OK           | The operation completed successfully.   |
+------------------+--------------+-----------------------------------------+
| 400              | Bad Request  | There was an error in the data sent in  |
|                  |              | the request.                            |
+------------------+--------------+-----------------------------------------+
| 401              | Unauthorized | The user wasn't authorized to perform   |
|                  |              | this request.                           |
+------------------+--------------+-----------------------------------------+
| 403              | Forbidden    | The request was to a resource that the  |
|                  |              | user didn't have permission to access.  |
+------------------+--------------+-----------------------------------------+
| 404              | Not Found    | The resource was not found.             |
+------------------+--------------+-----------------------------------------+
| 405              | Method Not   | The HTTP method used was not allowed.   |
|                  | Allowed      |                                         |
+------------------+--------------+-----------------------------------------+
| 409              | Conflict     | There was a conflict in the data when   |
|                  |              | creating a new resource. A previous     |
|                  |              | resource with that data already exists. |
+------------------+--------------+-----------------------------------------+
| 500              | Internal     | There was a server-side error when      |
|                  | Server Error | processing the request. This is usually |
|                  |              | a bug in Review Board.                  |
+------------------+--------------+-----------------------------------------+
| 501              | Not          | The call is not supported on that       |
|                  | Implemented  | particular instance of the resource     |
|                  |              | type.                                   |
+------------------+--------------+-----------------------------------------+


Payloads
--------

Responses will be returned based on the HTTP Accept header. All resources
can return JSON or XML, with JSON being the default.

.. note:: When viewing the API in your web browser, you may see XML
          data instead of JSON and assume we just lied about JSON being the
          default. What's happening is that your browser is sending
          its own Accept header indicating that either HTML or XML data is
          preferred. It doesn't particularly care about JSON. That doesn't
          mean that's what your app will get by default, though!

Every payload has, at the least, a ``stat`` key. The value will be either
``ok`` (for success) or ``fail`` (for a failed request).

Payloads for failed requests will also contain a ``err`` key mapping to a
dictionary containing ``code`` and ``msg`` keys. ``code`` will contain
a numeric error code that can be used for determining the particular type of
error. ``msg`` will contain a human-readable error string from the server.


JSON
~~~~

JSON, or JavaScript Object Notation, is a standard, minimal format for
expressing information in a way that is both human-readable and easy to parse.
Most languages contain libraries for parsing JSON. We recommend JSON when
interacting with the Review Board API.

JSON responses are returned when using the :mimetype:`application/json`
mimetype.

An example of a successful response payload would be:

.. code-block:: javascript

    {
      stat: "ok",
      calculated_result: 42
    }

An example of an error response payload would be:

.. code-block:: javascript

    {
      stat: "fail",
      err: {
        code: 205,
        msg: "A repository path must be specified"
      }
    }


XML
~~~

XML is another popular format, though it's more verbose than JSON. Our
XML format is for the moment very simplistic, and does not contain a schema
or any namespaces. This will likely change in a future version.

XML responses are returned when using the :mimetype:`application/xml`
mimetype.

An example of a successful response payload would be:

.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>

    <rsp>
     <stat>ok</stat>
     <calculated_result>42</calculated_result>
    </rsp>

An example of an error response payload would be:

.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>

    <rsp>
     <stat>fail</stat>
     <err>
      <code>205</code>
      <msg>A repository path must be specified</msg>
     </err>
    </rsp>


.. comment: vim: ft=rst et ts=3
