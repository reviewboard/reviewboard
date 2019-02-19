.. _email-settings:

===============
E-Mail Settings
===============

Review Board provides a lot of options for customizing how and when e-mails
are sent. You can control the types of e-mails that get sent out to your
users, how those e-mails are generated, and what server is used to send them.

See :ref:`working-with-email` for details on how Review Board sends e-mail,
and how you can customize these settings to avoid mail delivery problems.


.. _send-e-mails:

E-Mail Notification Settings
============================

* **Send e-mails for review requests and reviews:**
    If enabled, e-mails will be sent out whenever a review request is
    posted or updated, or when reviews and replies are posted.

    See :ref:`e-mail-and-review-groups` for more information.

* **Send e-mails when review requests are closed:**
    If enabled, e-mails will be sent out whenever a review request has been
    closed/discarded.

* **Send e-mails to administrators when new users register accounts:**
    If enabled, e-mails will be sent to the system administrator whenever a
    new user account has been registered, helping administrators on-board
    new users or catch suspicious activity.

* **Send e-mails to users when they change their password:**
    If enabled, e-mails will be sent to users any time they change their
    password. For password-based authentication setups, this can help users
    confirm that their password change went through successfully, and can
    also catch any account hijacking.

* **Send e-mails when new users register an account:**
    If enabled, e-mails will be sent to the administrator every time a new
    user signs up to the site. This is useful for open source projects that
    are interested in new user signups.


E-Mail Delivery Settings
========================

.. _sender-email-address:
.. _setting-mail-default-from-address:

* **Default From address:**
    The default e-mail address that e-mails are sent from. The
    :mailheader:`Sender` e-mail header will be used to make e-mails appear to
    come from the user causing the e-mail to be sent. By using the
    :mailheader:`Sender` header for this instead of :mailheader:`From`,
    there's less risk that e-mail clients will consider the e-mails to be
    malicious or spam. This may require a proper :term:`DKIM` setup.

    This defaults to ``noreply@<servername>``.

.. _setting-mail-use-users-from-address:

* **Use the user's From address:**
    Controls which :mailheader:`From` address is use for outgoing e-mails.

    If set to :guilabel:`Auto`, then any new e-mails sent out will use the
    sending user's own e-mail address only if there's no risk of a
    :term:`DMARC` record quarantining the e-mail. If there is a risk, then
    the :ref:`default From address <setting-mail-default-from-address>` will
    be used instead.

    If set to :guilabel:`Always`, then the user's own e-mail address will
    always be used, without needing to perform a record lookup first. This
    can speed up sending, but at the risk of a mail server or client flagging
    the e-mail as suspicious.

    If set to :guilabel:`Never`, then the :ref:`default From address
    <setting-mail-default-from-address>` will always be used.

* **Enable "Auto-Submitted: auto-generated" header:**
    Configures whether this header will be attached to any outgoing e-mails.
    This can be turned off if using a mailing list that reject e-mails
    containing this header.


E-Mail Server Settings
======================

* **Mail server:**
    The SMTP mail server used for outgoing e-mails. This defaults to
    ``localhost``.

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

* **Send a test e-mail after saving:**
    Enable this to send a test e-mail address to yourself after saving the
    form. This can help verify that your e-mail setup is correct.
