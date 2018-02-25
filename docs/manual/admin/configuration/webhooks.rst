.. _webhooks:

========
WebHooks
========

Review Board can notify third-party services when various events occur. This is
useful for tying your various tools together (for example, posting a message to
a group chat room when a review request is published). WebHooks are managed in
the :ref:`Administration UI <administration-ui>` through the
:ref:`administrator-dashboard`.

WebHooks send an ``HTTP POST`` request to a remote endpoint. The body of the
request contains information that the remote server can use to perform some
action.


Configuring a WebHook
=====================

When creating or updating a WebHook, a form will appear with fields split into
two sections:

* `WebHook Settings`_
* `Payload`_


WebHook Settings
----------------

* **Enabled**
  This check-box will control whether or not the WebHook is active.

* **URL** (required)
  The URL of the remote service to send POST requests to.

* **Events** (required)
  Determines which events will be sent to this WebHook endpoint. Selecting
  :guilabel:`All Events` will override any individual choices.

* **Apply to** (required)
  Allows you to limit this WebHook to operate on only a single repository, or
  on Review Requests which have no repository (file attachments only).


Payload
-------

* **Encoding** (required)
  The method for encoding the payload. This allows you to send the contents as
  either ``JSON``, ``XML``, or ``Form-Data``.

  If :guilabel:`Use custom payload content` is selected, this will not affect
  the payload, but will be used to set the MIME type on the request.

* **Use custom payload content**
  Selecting this will allow you to hand-craft your own payload content using a
  subset of the `Django template language`_. See `Custom payloads`_ for more
  details.

** **HMAC Secret** (optional)
  If present, the payload will be signed using HMAC with the given secret as
  the key. This allows your remote endpoint to confirm that the request isn't
  being spoofed by some nefarious third party.


.. _webhook-custom-payloads:

Custom Payloads
===============

Defining custom payloads allows you to use WebHooks to talk to services which
expect specific content. Custom payloads are configured using a subset of the
`Django template language`_. Most of the built-in tags and filters are allowed,
but some dangerous ones such as ``include`` and ``ssi`` have been disabled.


Custom content data
-------------------

Depending on the event, the webhook content has access to various different
objects:


``review_request_closed`` event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``event``
  ``review_request_closed``
``closed_by``
  The user who closed the review request.
``close_type``
  Either ``submitted`` or ``discarded``.
``review_request``
  The review request being closed.


``review_request_published`` event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``event``
  ``review_request_published``
``is_new``
  Either ``true`` or ``false`` depending on whether this is a new review
  request or an updated review request.
``review_request``
  The review request being published.


``review_request_reopened`` event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``event``
  ``review_request_reopened``
``reopened_by``
  The user who reopened the review request.
``review_request``
  The review request being reopened.


``review_published`` event
~~~~~~~~~~~~~~~~~~~~~~~~~~

``event``
  ``review_published``
``review``
  The review being published.
``diff_comments``
  A list of diff comments in the review.
``file_attachment_comments``
  A list of file attachment comments in the review.
``screenshot_comments``
  A list of screenshot comments in the review.
``review_request``
  The parent review request for the review.


``reply_published`` event
~~~~~~~~~~~~~~~~~~~~~~~~~

``event``
  ``reply_published``
``reply``
  The review reply being published.
``diff_comments``
  A list of diff comment replies.
``file_attachment_comments``
  A list of file attachment comment replies.
``screenshot_comments``
  A list of screenshot comment replies.
``review_request``
  The parent review request for the reply.


Example payload
---------------

This is an example of a custom payload for the ``review_request_published``
event which posts a message to a `Slack`_ channel:

.. code-block:: json

   {
       "attachments": {
           "fallback": "Review Request {{review_request.display_id}} published: {{review_request.summary|escapejs}}",
           "pretext": "Review Request {{review_request.display_id}} published",
           "title": "{{review_request.summary|escapejs}}",
           "title_url": "https://reviewboard.example.com/{{review_request.get_absolute_url}}"
       },
       "channel": "#general"
   }


.. _`Django template language`: https://django.readthedocs.io/en/1.6.x/topics/templates.html
.. _`Slack`: https://slack.com/
