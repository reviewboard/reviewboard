.. _api-token-policies:

==================
API Token Policies
==================

.. versionadded:: 2.5

API tokens are used in Review Board 2.5+ to provide a safe form of
authentication for clients without exposing any user passwords. It also offers
a policy-based form of access control, limiting the capabilities of clients.

Token policies can globally limit HTTP methods, allow or block HTTP methods
per-resource, or even allow or block them for specific resource item IDs.
Policies are written in JSON format.

Despite the flexibility, it's easy to write custom policies.


Policy Sections
===============

All sections of a policy live in a top-level ``resources`` key:

.. code-block:: javascript

   {
       "resources": {
           ...
       }
   }

All policy sections will go under ``resources``.

Each section of a token policy should specify ``allow`` and/or ``block``
lists. These lists contain the list of all HTTP methods that are either
allowed or blocked (``"POST"``, ``"GET"``, ``"PUT"``, etc.). A special value
of ``"*"`` in the list matches all HTTP methods, which is useful for allowing
all methods by default and blocking just a few, or vice-versa.

Any part of the API that is denied by a policy will return a
:ref:`webapi2.0-error-101` error.


Global Policy Section
---------------------

Within ``resources``, you can add a global policy section, ``"*"``, which sets
the default allowed or blocked HTTP methods for all resources:

.. code-block:: javascript

   {
       "resources": {
           "*": {
               "allow": [<list of methods, or "*">],
               "block": [<list of methods, or "*">]
           }
       }
   }

For example, to only allow read-only access to the API:

.. code-block:: javascript

   {
       "resources": {
           "*": {
               "allow": ["GET", "HEAD", "OPTIONS"],
               "block": ["*"]
           }
       }
   }

Global policies apply to any and all resources, unless overridden by a more
specific policy.


Resource Policy Sections
------------------------

To allow or block access to a specific resource, add a section with the
resources API policy identifier (found on any resource page in the
documentation).

This may contain one or more sub-sections: ``"*"``, for rules applying to all
items in that resource, or ``"<id>"``, where the ID matches the ID of the
specific item in the resource that you want to limit access to.

The resource-global policy will apply to both lists and items.

The ID-specific policies are optional. In most cases, the resource-global
policy is all that's needed.

.. code-block:: javascript

   {
       "resources": {
           "*": {
               "allow": [<list of methods, or "*">],
               "block": [<list of methods, or "*">]
           },
           "<id>": {
               "allow": [<list of methods, or "*">],
               "block": [<list of methods, or "*">]
           },
           ...
       }
   }

For example, to block all access to all repositories with the exception
of allowing read access to repository ID 3:

.. code-block:: javascript

   {
       "resources": {
           "repository": {
               "*": {
                   "block": ["*"]
               },
               "3": {
                   "allow": ["GET", "HEAD", "OPTIONS"]
               }
           }
       }
   }


Policy Tips
===========

* To allow read access, you'll generally want to allow ``GET``, ``HEAD``, and
  ``OPTIONS`` in the ``allow`` list. ``GET`` isn't always sufficient.

* Clients are expected to follow links to get to a resource. Because of this,
  if you're specifically allowing access to only certain resources, you will
  also generally need to allow access to their parent resources.

* You probably want to allow :ref:`webapi2.0-root-resource` and
  :ref:`webapi2.0-server-info-resource`, if you're globally blocking ``GET``
  on all resource.
