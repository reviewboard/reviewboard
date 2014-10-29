.. _webapi2.0-text-fields:

==========================
Rich Text Fields and Types
==========================

.. versionadded:: 2.0

Several resources in the API provide text fields that can store either plain
text or Markdown text. These text fields are accompanied by a text type
field that indicates the type of text being stored (see
:ref:`webapi2.0-storing-text-types`).

Clients can set these text types to influence how the text will be rendered in
Review Board, and can read them to determine how to render the text.

They can also
`force returned text to a requested type <2.0-forcing-text-types>`_
for display purposes. This is useful when clients want to render exclusively
as Markdown or HTML, for instance.


.. _webapi2.0-storing-text-types:

Storing Text Types
==================

Text can be stored along with one of the following text types:

* ``plain``
* ``markdown``

The default text type for a field on a new resource is ``plain``. Text types
can be overridden in a PUT or POST request.

When `forcing text types <2.0-forcing-text-types>`_, there's one additional
text type that clients may use:

* ``html``

This type cannot be stored, and is only there to provide a rendered version of
the text in the resulting payload.


Field names
-----------

There are two rules used for the naming of text type fields.

If the text field's name is ``text``, then the text type field will simply
be named ``text_type``.

If the text field's name is anything else, then the text type field will be
named after it, as in :samp:`{fieldname}_text_type`. For instance, a
``description`` text field will have an accompanying
``description_text_type``.

.. note::

   Review Board 2.0 through 2.0.11 had a field named ``text_type`` on
   :ref:`webapi2.0-review-request-resource` and
   :ref:`webapi2.0-review-request-draft-resource`, which would represent the
   text type for all text fields on that resource, including custom fields.

   In 2.0.12, that has been deprecated in favor of individual fields, and
   is no longer used.


Custom fields in extra_data
---------------------------

:ref:`webapi2.0-review-request-resource` and
:ref:`webapi2.0-review-request-draft-resource` support custom review request
fields provided by extensions, which may themselves support rich text and text
types.

These custom fields store data in an ``extra_data`` dictionary field
in the payload. The text field keys are determined by the custom field (for
example, :samp:`{extensionid}_description`).

The text type information is also stored here, and follows the same
format as any other field, using the same naming convention.

Similar to standard text type field names, if the field name is just simply
:samp:`{extensionid}_text`, then the rich text field will be
:samp:`{extensionid}_text_type`, instead of
:samp:`{extensionid}_text_text_type`.


Updating Text Types
===================

Text types can be set/updated by setting the appropriate field to either
``plain`` or ``markdown`` in a POST/PUT request.

Generally, this will be set along with new text matching that text type.
However, if the text type is changed in a request without changing the text,
the existing stored text will be converted to the new type.

If changing the text type to ``plain``, and the stored text type is
``markdown``, then the existing Markdown text will be unescaped (all ``'\'``
characters before Markdown-unsafe characters will be removed).

If changing the text type to ``markdown``, and the stored text type is
``plain``, then the existing plain text will be escaped (all Markdown-unsafe
characters will be prefixed by a ``'\'``).


.. _webapi2.0-forcing-text-types:

Forcing Text Types for Display
==============================

When retrieving or modifying a resource, the client can force all the text
fields to return text using a given text type. By doing this, a client can,
for instance, ensure all text will be Markdown-safe, or can be rendered as
HTML. This is entirely for the benefit of the client, and does not result in
any modifications to the resource itself.

To force the text type, the client must send either a ``?force-text-type=``
query argument (for GET requests) or a ``force_text_type=`` form field (for
POST/PUT requests) with the given text type.

Text fields can be forced to one of the following text types:

* ``plain``
* ``markdown``
* ``html``

If requesting ``plain``, and the stored text type is ``markdown``, then the
Markdown text will be unescaped (all ``'\'`` characters before Markdown-unsafe
characters will be removed) and returned.

If requesting ``markdown``, and the stored text type is ``plain``, then the
text will be escaped (all Markdown-unsafe characters will be prefixed by a
``'\'``) and returned.

If requesting ``html``, the text will be rendered for HTML. For ``plain``
text, the text will be HTML-escaped, turning special characters into HTML
entities. For ``markdown``, the Markdown text will be rendered to HTML in the
same way that it's rendered in the Review Board UI. It's up to the client to
handle any styling.


Including Raw Text Information
------------------------------

.. versionadded:: 2.0.9

There are cases where a client wants to force text types for rendering, but
also needs access to the original values and text types. This information can
be optionally returned in any GET/POST/PUT request.

To request this inforamtion, the client must send either a
``?include-raw-text-fields=true`` query argument (for GET requests) or a
``include_raw_text_fields=true`` form field (for POST/PUT requests).

The payload will then contain a ``raw_text_fields`` field containing each of
the text and text type fields along with their stored values.

For example, if requesting a resource with
``?force-text-type=html&include-raw-text-fields=true``, you might get:

.. code-block:: javascript

   {
       ...

       "description": "<p>This is a <strong>test</strong>.</p>",
       "description_text_type": "html",
       "raw_text_fields": {
           "description": "This is a **test**.",
           "description_text_type": "markdown"
       },

       ...
   }

Any custom text fields stored in ``extra_data`` will also be returned in an
``extra_data`` dictionary within ``raw_text_fields``:

.. code-block:: javascript

   {
       ...,

       "extra_data": {
           "myextension_text": "<p>This is a <strong>test</strong>.</p>",
           "myextension_text_type": "html"
       },
       "raw_text_fields": {
           "extra_data": {
               "myextension_text": "This is a **test**.",
               "myextension_text_type": "markdown"
           }
       },

       ...
   }
