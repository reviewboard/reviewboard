.. _email-settings:

===============
E-Mail Settings
===============

.. _send-e-mails:

* **Send e-mails for review requests and reviews:**
    If enabled, e-mails will be sent out whenever a review request is
    posted or updated, or when reviews and replies are posted.

    See :ref:`e-mail-and-review-groups` for more information.

* **Send e-mails when new users register an account:**
    If enabled, e-mails will be sent to the administrator every time a new
    user signs up to the site. This is useful for open source projects that
    are interested in new user signups.

.. _sender-email-address:

* **Sender e-mail address:**
    The e-mail address all e-mails are sent from. The :mailheader:`Sender`
    e-mail header will be used to make e-mails appear to come from the user
    causing the e-mail to be sent. By using the :mailheader:`Sender` header
    for this instead of :mailheader:`From`, there's less risk that e-mail
    clients will consider the e-mails to be malicious or spam. This may
    require a proper :term:`DKIM` setup.

    This defaults to ``noreply@<servername>``.

* **Mail Server:**
    The SMTP mail server used for outgoing e-mails.
    This defaults to ``localhost``.

* **Port:**
    The SMTP mail server port. This defaults to ``25``.

* **Username:**
    The username needed to connect to the outgoing SMTP mail server, if any.
    This is optional and depends on the mail server configuration.

* **Password:**
    The password needed to connect to the outgoing SMTP mail server, if any.
    This is optional and depends on the mail server configuration.

* **Use TLS for authentication:**
    If enabled, TLS is used for mail server authentication. This is more
    secure, but requires TLS support on the mail server.
