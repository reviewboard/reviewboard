.. _email:

======
E-Mail
======

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

E-mails appear to be sent from the users, rather than from Review Board
itself. It accomplishes this by putting the user's name and e-mail address
in the :mailheader:`Sender` field in the e-mail, and the configured
:ref:`sender e-mail address <sender-email-address>` in the
:mailheader:`From` field. That address can be customized in the
:ref:`email-settings`.

By using these two fields instead of just faking the :mailheader:`From`
address, we can avoid e-mails appearing to be spam or otherwise malicious.
Many modern e-mail clients warn if the :mailheader:`From` address appears to
be suspicious.


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
