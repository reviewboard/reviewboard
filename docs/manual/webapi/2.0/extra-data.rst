.. _webapi2.0-extra-data:

============================
Storing/Accessing Extra Data
============================

Many API resources have a special field called ``extra_data``, which is a
JSON_ document that can contain arbitrary data for use by extensions or
clients of the API. You are free to store data in this field, and we have
three ways of doing that:

* :ref:`Storing/merging JSON data <webapi2.0-extra-data-merging>`
* :ref:`Patching JSON data <webapi2.0-extra-data-patching>`
* :ref:`Simple key/value assignment <webapi2.0-extra-data-simple-assignment>`

When storing data specific to your tool/script/extension, we recommend
prefixing any top-level keys with some vendor identifier, like
:samp:`{vendorname}-{key}`, or even nesting all data in a top-level vendor
key.

Some keys may not be writable or even readable. See
:ref:`webapi2.0-extra-data-access-restrictions` for more information.


.. _JSON: https://www.json.org


.. _webapi2.0-extra-data-merging:

Storing/Merging JSON Data
=========================

.. versionadded:: 3.0

JSON documents can be stored by using a :rfc:`JSON Merge Patch <7396>`. This
is a simple method of specifying new JSON data to merge in. Any objects in the
data will be merged together, and anything else (arrays, strings, booleans,
etc.) will be replaced by the newly-supplied data. Anything set to ``null``
will be removed.

To supply the data to merge in, supply the new serialized JSON document in the
``extra_data:json`` field, like so:

.. code-block:: javascript

    extra_data:json={
        "myvendor": {
            "mytool": {
                "array_to_replace": [1, 2, 3],
                "key_to_remove": null,
                "maybe_existing_object": {
                    "a": 1,
                    "b": "test",
                    "c": false
                }
            }
        }
    }

In this example, we're merging data into ``beanbag.mytool`` (keeping any
existing data in those objects), replacing the ``array_to_replace`` key with a
new array, removing the ``key_to_remove`` key, and merging in some more data
into ``maybe_existing_object``. The objects will be created if they don't
already exist.

.. note::

   The example above shows the JSON data spread across multiple lines. In
   practice, when sending this via the API, the JSON data should ideally be
   condensed to a single line.

   This is also sent as HTTP Form Data, like any other field being set in the
   API.

When merging in new JSON data, the following rules are followed:

* ``extra_data`` itself cannot be replaced (for instance, supplying
  ``extra_data:json=[]`` will fail).

* If a new key does not match an existing key in ``extra_data``, it will be
  added.

* If a new matches an existing key in ``extra_data``, and the new value is
  ``null``, the key will be removed.

* If a new key matches an existing key in ``extra_data``, and either the old
  or new value is not an object, the old value will be replaced with the new
  one.

* If a new key matches an existing key in ``extra_data``, and both the old and
  new value is an object, the object will be merged using these rules.

While objects are merged together, arrays are not. To update existing arrays,
you will want to :ref:`patch extra_data <webapi2.0-extra-data-patching>`
instead.


.. _webapi2.0-extra-data-patching:

Patching JSON Data
==================

.. versionadded:: 3.0

``extra_data`` fields also support a more advanced form of modification in the
form of a `JSON Patch`_. These patches supply a list of operations to perform,
which may consist of adding new keys, replacing old ones, inserting into
arrays, copying/moving keys, and even testing for the existence of certain
data (aborting the patch if not found).

To patch ``extra_data``, set a serialized JSON Patch in the
``extra_data:json-patch`` field. For example:

.. code-block:: javascript

    extra_data:json-patch=[
        {
            "op": "add",
            "path": "/myvendor/mytool/new_key",
            "value": "new-value"
        },
        {
            "op": "remove",
            "path": "/myvendor/mytool/key_to_remove",
        },
        {
            "op": "replace",
            "path": "/myvendor/mytool/existing_key",
            "value": "new-value"
        }
    ]

This example shows just a few of the operations, the addition of a brand-new
key, the removal of an existing key, and replacing the value for an existing
key. These operations all work on paths (:ref:`documented below
<webapi2.0-extra-data-paths>`), which specify a location within a JSON
document.

If any operation in a patch were to fail (due to a non-existent key, or some
other conflict), no part of the watch will apply, and the API request will
fail with an :ref:`Invalid Form Data <webapi2.0-error-105>` error.


.. _JSON Patch: http://jsonpatch.com/


Operations
----------

Add
~~~

Data can be added to an object or an array through the ``add`` operation.
It takes the form of:

.. code-block:: javascript

    {
        "op": "add",
        "path": "/path/to/key/or/index",
        "value": "new value"
    }

If the key at the path already exists, it will be replaced. Otherwise, it will
be created.

The new value can be simple data like a string or number, or it can be a
complete JSON document by itself.


Remove
~~~~~~

Data can be removed from an object or array through the ``remove`` operation.
It takes the form of:

.. code-block:: javascript

    {
        "op": "remove",
        "path": "/path/to/key/or/index",
    }

If the path does not exist, the patch will fail.


Replace
~~~~~~~

Existing data in an array or key can be replaced with a new value through the
``replace`` operation. It takes the form of:

.. code-block:: javascript

    {
        "op": "replace",
        "path": "/path/to/key/or/index",
        "value": "new value"
    }

If the path does not exist, the patch will fail.

The new value can be simple data like a string or number, or it can be a
complete JSON document by itself.


Copy
~~~~

Data can be copied from one location (such as an object or array) to another
location anywhere in ``extra_data`` through the ``copy`` operation. It takes
the form of:

.. code-block:: javascript

    {
        "op": "copy",
        "from": "/path/to/source/key/or/index",
        "path": "/path/to/new/key/or/index"
    }

If the "from" path does not exist, or the destination path cannot be written
to, the patch will fail.


Move
~~~~

Data can be moved from one location (such as an object or array) to another
location anywhere in ``extra_data`` through the ``move`` operation. It takes
the form of:

.. code-block:: javascript

    {
        "op": "move",
        "from": "/path/to/source/key/or/index",
        "path": "/path/to/new/key/or/index"
    }

If the "from" path does not exist, or the destination path cannot be written
to, the patch will fail.


Test
~~~~

A patch can sanity-check that there's some expected data already stored in
``extra_data``. If that data is not present as expected, the patch will fail.

.. code-block:: javascript

    {
        "op": "test",
        "from": "/path/to/source/key/or/index",
        "value": "expected value"
    }


.. _webapi2.0-extra-data-paths:

Specifying Paths
----------------

All patch operations take at least one path, using the :rfc:`JSON Pointer
<6901>` specification. These paths specify a location within a JSON document,
using ``/`` to separate object keys and array indices.

Paths always begin with a ``/``.

To specify an object key, just list the key name.

To specify an index in an array, specify the 0-based index of the array. If
you want to specify the tail end of an array (for the purposes of appending to
an array), use the special ``-`` character instead of a numeric index.


Special Escape Characters
~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to reference a key with a ``/`` or ``~`` in the name, you'll need
to use a special escape character.

To specify a key containing ``/``, use ``~1`` instead.

To specify a key containing ``~``, use ``~0`` instead.


Examples
~~~~~~~~

Here are some examples of paths:

* ``/myvendor/mytool/mykey``
* ``/myvendor/mytool/myarray/2``
* ``/myvendor/mytool/myarray/2/nested-key``
* ``/myvendor/mytool/myarray/-``
* ``/myvendor/mytool/-1``
* ``/myvendor/mytool/-0/nested-key``


.. _webapi2.0-extra-data-simple-assignment:

Simple Key/Value Assignment
===========================

If you need to store top-level data directly in ``extra_data``, you can use
simple assignments in the form of::

    extra_data.mykey=myvalue

The value can be a string, a numeric value (integer or floating-point), or a
boolean (``true`` or ``false``, case-insensitive). Anything that doesn't look
like a number or boolean is considered a string.

If an empty value is provided for a key, and the key already exists in
``extra_data``, it will be removed.

.. note::

   This is a legacy way of working with ``extra_data``, available for versions
   prior to Review Board 3.0. It has limitations, like being unable to work
   with nested keys, unable to store complex JSON documents, and unable to
   store strings that look like numbers or booleans.

   If targetting Review Board 3.0 or higher, we recommend using the more
   modern :ref:`merging <webapi2.0-extra-data-merging>` or
   :ref:`patching <webapi2.0-extra-data-patching>` methods instead.


.. _webapi2.0-extra-data-access-restrictions:

Access Restrictions
===================

There are certain keys that, if present in ``extra_data``, will not be shown
to clients and cannot be modified.

First, any key starting with double underscores (``__``) is considered private
for internal use by Review Board or :ref:`extensions <writing-extensions>`
only. API clients cannot see these keys or anything underneath them.

Extensions may also mark some keys as read-only or private by making use of
:ref:`api-extra-data-access-hook`. This allows extensions (while enabled) to
limit what API clients are able to do.

Finally, some API resources may impose their own limitations on certain keys.
