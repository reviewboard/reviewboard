.. _account-settings:

================
Account Settings
================

Overview
========

To get to the account settings page, go to the user menu at the top right of
the page (signified by your username and avatar image), then select
:menuselection:`My Account`.

The account settings has several sub-pages, listed in a navigation bar on the
left. There are several built-in pages, and more may be added by any extensions
that have been installed.


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


.. _account-settings-avatar:

Avatar
------

.. versionadded:: 3.0

You can also set your avatar image on this page. By default, Review Board uses
the Gravatar_ system for user avatars, which allows you to associate an avatar
image with your e-mail address and have it appear on any supporting
application. You can change this to upload an image file for use as your
avatar.

Extensions may provide additional avatar mechanisms. See
:ref:`avatar-service-hook` for more information on writing avatar service
backends.

.. _Gravatar: https://en.gravatar.com/


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

* **Always use Markdown for text fields**
    Review Board encourages the use of :ref:`Markdown <using-markdown>` for
    text fields. When this box is checked, Markdown will be preferred for all
    text boxes, even if you've turned it off when previously editing it.

* **Get e-mail notification for review requests and reviews**
    If e-mail notifications are enabled on the server, unchecking this allows
    you to forego e-mails which are addressed directly to you. Any e-mails that
    are sent to mailing lists via configured review groups may still be
    delivered to you.

* **Get e-mail notifications for my own activity**
    Review Board typically sends you an e-mail when you publish review requests
    or reviews, in order to maintain proper threading in your e-mail client. If
    you'd like to not receive these, uncheck this box.

* **Show desktop notifications**
    Review Board can use your browser's notifications system to pop up system
    notifications when there's new activity on an open review request. If you'd
    like to not see these, uncheck this box.


Groups
======

If your Review Board server has review groups, you can choose which groups
you'd like to join. Review requests which are assigned to groups that you are
in will then show up in the :guilabel:`Incoming` section of your dashboard.

For any groups that are not set up with a specific e-mail list, you will also
recieve e-mail notifications for anything which is assigned to those groups.
For groups that do have mailing lists configured, Review Board will not send
e-mail to individual group members, and you'll need to join those lists.


Authentication
==============

The Authentication page allows you to change your password. This page may not
be available if Review Board is configured to use an external authentication
system like LDAP or Active Directory.


.. _api-tokens:

API Tokens
----------

.. versionadded:: 2.5

This section allows you to create special tokens for use with Review Board's
API. These allow you to embed the tokens in scripts without having to divulge
your login credentials.

Each API Token can be given a nickname in order to keep track of what it is
used for.

The amount of access can be configured for each token. There are two built-in
access levels: :guilabel:`Full access` and :guilabel:`Read-only`. You can also
customize the access per resource and method. See :ref:`api-token-policies` for
details on writing your own policies.


OAuth Tokens
------------

.. versionadded:: 3.0

If you have any applications which have authenticated using :term:`OAuth2`,
those tokens will be listed in this section and can be revoked.


OAuth2 Applications
===================

The :guilabel:`OAuth2 Applications` page allows you to create registrations for
your own applications that want to integrate with Review Board. By using
OAuth2, you can allow users of your application to connect it securely to
Review Board without supplying any authentication credentials.

See :ref:`oauth2` for more information about creating applications that use
OAuth2.


I Done This
===========

.. versionadded:: 3.0.4

If the :ref:`I Done This integration <integrations-idonethis>` is enabled,
the :guilabel:`I Done This` section will be available, allowing you to
configure your API Token for automatically posting status updates to `I Done
This`_.

If you don't see this section, but are using I Done This, ask your
administrator to :ref:`enable I Done This support <integrations-idonethis>`.


.. _I Done This: https://idonethis.com/
