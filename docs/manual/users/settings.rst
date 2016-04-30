================
Account Settings
================

Overview
========

To get to the account settings page, go to the user menu at the top right of
the page (signified by your username and Gravatar image). From here, select
:menuselection:`My Account`.

The account settings has several sub-pages, listed in a navigation bar on the
left. There are several built-in pages, and more may be added by any extensions
that have been installed.


Groups
======

If your Review Board server has review groups, you can choose which groups
you'd like to join using the checkboxes in this section. Review requests which
are assigned to groups that you are in will then show up on your dashboard.


Settings
========

There are a few settings which allow you to affect how you interact with Review
Board:

* **Time zone**
    This setting will change which time zone is used to show times and dates.
    This should be set to the time zone in your current location.

* **Enable syntax highlighting in the diff viewer**
    By default, code is shown using syntax highlighting. If you'd like to turn
    it off, uncheck this item.

* **Always open an issue when comment box opens**
    By default, when you create a comment, the :guilabel:`Open an issue`
    checkbox will be checked. If you prefer to opt-in to creating issues for
    each comment, uncheck this item.

* **Get e-mail notification for review requests and reviews**
    If e-mail notifications are enabled on the server, unchecking this allows
    you to forego e-mails which are addressed directly to you. Any e-mails that
    are sent to mailing lists via configured review groups may still be
    delivered to you.

* **Get e-mail notifications for my own activity**
    Review Board typically sends you an e-mail when you publish review requests
    or reviews, in order to maintain proper threading in your e-mail client. If
    you'd like to not receive these, uncheck this box.

* **Always use markdown for text fields**
    Review Board encourages the use of :ref:`Markdown <using-markdown>` for
    text fields. When this box is checked, Markdown will be preferred for all
    text boxes, even if you've turned it off when previously editing it.


Authentication
==============

The Authentication page allows you to change your password. This page may not
be available if Review Board is configured to use an external authentication
system like LDAP or Active Directory.


Profile
=======

The Profile page allows you to change the real name and e-mail address
associated with your account. These settings may not be available if Review
Board is configured to use an external authentication system like LDAP or
Active Directory. There is also a setting to control the privacy of your
account:

* **Keep profile information private**
    Normally, the user profile page will show your real name, e-mail address,
    and when you last logged in. If you'd like to hide this information, check
    this item.


API Tokens
==========

.. versionadded:: 2.5

The API Tokens page allows you to create special tokens for use with Review
Board's API. These allow you to embed the tokens in scripts without having to
divulge your login credentials.

Each API Token can be given a nickname in order to keep track of what it is
used for.

The amount of access can be configured for each token. There are two built-in
access levels: :guilabel:`Full access` and :guilabel:`Read-only`. You can also
customize the access per resource and method. See :ref:`api-token-policies` for
details on writing your own policies.


Gravatar Images
===============

Review Board uses the Gravatar system to associate photos or pictures with user
accounts. To set your Gravatar, go to http://gravatar.com/ and enter the email
address used on your Review Board account.
