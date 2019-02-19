.. _email:
.. _working-with-email:

===================
Working with E-Mail
===================

Sending E-Mail
==============

Review Board requires access to an SMTP server in order to send e-mails.
This should ideally be one that lives on the same network (though for
performance reasons, not the same server). The SMTP server can be
configured on the :ref:`email-settings` page.

It's also very important that the server responds fast enough to requests
to send e-mail. Any delays in server communication will directly affect the
responsiveness of Review Board, particularly when publishing review requests
or reviews.

Review Board cannot be configured to use a local Mail Transfer Agent like
sendmail.


Sender Headers
==============

Review Board can send e-mail on behalf of users. This may happen when
creating a new review request or reviewing some code.

By default, e-mails appear to be sent from the users, rather than from Review
Board itself. The :mailheader:`From` field will contain the full name and
e-mail address of the user, helping the thread appear as a standard discussion
over e-mail.

However, if the e-mail address's domain has a :term:`DMARC` record that
rejects or quarantines suspicious e-mails, this behavior will be turned off,
instead using the :ref:`Default From address
<setting-mail-default-from-address>` configured in :ref:`email-settings`.

All e-mail setups are different, and some are more strict than others. If the
default behavior is not working out for you, you can change it to always use
the user's address, regardless of :term:`DMARC` record, or to only ever use
the default address. This is done through the :ref:`Use user's From address
<setting-mail-use-users-from-address>` setting.


Sender Verification through DKIM
================================

Using the :mailheader:`From` and :mailheader:`Sender` fields may not be
enough. To properly configure Review Board to send e-mail, you may need a
sufficient :term:`DKIM` setup. DKIM allows the receiver to verify that the
e-mail was actually sent from the server it appears to be sent from.

DKIM support may need to be configured on your mail server software.
Configuring DKIM is beyond the scope of this documentation, as it may
vary greatly between different servers.

Along with the mail server configuration, you will need to configure your
DNS records.

There are many guides out there for DKIM. See the following:

* `DKIM on Wikipedia <https://en.wikipedia.org/wiki/DomainKeys_Identified_Mail>`_
* `DKIM DNS wizard <https://www.dnswatch.info/dkim/create-dns-record>`_
* `Postfix DKIM on Ubuntu <https://help.ubuntu.com/community/Postfix/DKIM>`_
* `Setting up DKIM with Sendmail on Ubuntu 14.04 <https://philio.me/setting-up-dkim-with-sendmail-on-ubuntu-14-04/>`_
