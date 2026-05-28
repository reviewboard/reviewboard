.. _account-settings:
.. _my-account:

================
Account Settings
================

To get to the account settings page, go to the user menu at the top right of
the page (signified by your username and avatar image), then select
:menuselection:`My Account`.

The account settings has several sub-pages, listed in a navigation bar on the
left. There are several built-in pages, and more may be added by any
:ref:`extensions <writing-extensions>` that have been installed.


.. _my-account-profile:

Profile
=======

The Profile page allows you to change the real name and e-mail address
associated with your account. These settings may not be available if Review
Board is configured to use an external authentication system like LDAP or
Active Directory.

* **First name**

  Your first name, shown in Review Board and e-mails.

* **Last name**

  Your last name.

* **E-mail address**

  Your e-mail address used for all communication.

  This may be set and enforced by your company.

* **Keep profile information private**

  Normally, users will be able to see your real name, e-mail address, and when
  you last logged in. This setting can keep this information hidden and
  private.


.. _account-settings-avatar:
.. _my-account-profile-avatar:

Avatar
------

You can also set your avatar image on this page.

The following options are available by default:

* :guilabel:`Gravatar`: The Gravatar_ service will be used to display your
  avatar. This requires an existing account with Gravatar using your e-mail
  address.

* :guilabel:`File Upload`: Upload your own image to use for your avatar.

.. note::

   Administrators may limit your avatar choices or change the defaults.

   Extensions may provide additional avatar support. See
   :ref:`avatar-service-hook` for more information on writing your own avatar
   service backend for your company.


.. _Gravatar: https://en.gravatar.com/


.. _my-account-settings:

Settings
========

There are a few settings which allow you to affect how you interact with Review
Board:


.. _my-account-settings-general:

General Settings
----------------

* **Time zone**

  This setting will change which time zone is used to show times and dates.
  This should be set to the time zone in your current location.

* **Enable syntax highlighting in the diff viewer**

  By default, code is shown using syntax highlighting. If you'd like to turn
  it off, uncheck this item.

* **Prompt to confirm when publishing Ship It! reviews**

  .. versionadded:: 8.0

  When checked, clicking :ref:`Ship It! <ship-it>` will show a confirmation
  dialog before publishing your review. The dialog also offers an option
  to suppress future confirmations, which will uncheck this setting
  automatically.

* **Always open an issue when comment box opens**

  By default, when you create a comment, the :guilabel:`Open an issue`
  checkbox will be checked. If you prefer to opt-in to creating issues for
  each comment, uncheck this item.


.. _my-account-settings-text-editing:

Text Editing
------------

* **Always use Markdown for text fields**

  Review Board encourages the use of :ref:`Markdown <using-markdown>` for
  text fields. When this box is checked, Markdown will be preferred for all
  text boxes, even if you've turned it off when previously editing it.

* **Enable writing assistance for Markdown text fields**

  .. versionadded:: 8.0

  Review Board can enable your browser's built-in writing assistance
  features such as spell checking, voice dictation, and AI rewriting
  when editing Markdown text fields. This can help catch issues and
  assist you when composing reviews or review requests.

  Three options are available:

  1. :guilabel:`Default (disabled)`: Use Review Board's default settings.
     Writing assistance is off by default, but may be enabled by default in a
     future version.

  2. :guilabel:`Enabled`: Writing assistance is enabled in all Markdown
     text fields.

  3. :guilabel:`Disabled`: Writing assistance is explicitly disabled.

  .. note::

     This feature is still experimental. Different browsers and operating
     systems support different capabilities.

     Some browsers check spelling as you write and some wait until after
     you've finished or move around the text field. This is beyond our
     control.


.. _my-account-settings-notifications:

Notifications
-------------

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


.. _my-account-appearance:

Appearance
==========

.. versionadded:: 7.0

These settings control the overall appearance of Review Board:

* **Default appearance**

  By default, Review Board will match your system's light or dark theme.
  If you prefer light or dark mode all the time, you can change the setting
  here:

  * :guilabel:`Default appearance (System theme)`: Match your system's
    light or dark mode. This is the default.

  * :guilabel:`Light mode`: Always use light mode.

  * :guilabel:`Dark mode`: Always use dark mode.


.. _my-account-group:

Groups
======

You can choose which :term:`Review Groups` you'd like to join. Review
requests assigned to these groups will show up in the :guilabel:`Incoming`
section of your :ref:`Dashboard <dashboard>`.

You'll also be notified of any updates to review requests posted to these
groups, if the group is configured to post to group members instead of a
dedicated mailing list.

To manage your groups:

1. Look for the group you want to join or leave (you can type to filter for
   the group name).

2. Click :guilabel:`Join` to join the group, or :guilabel:`Leave` to leave it.


.. _my-account-authentication:

Authentication
==============

This page give you control over your authentication settings, allowing you
to change your password (if supported by your authentication backend) and
to manage API tokens and OAuth2 tokens used to grant scripts and services
access to your account.


.. _my-account-authentication-change-password:

Change Password
---------------

You can change the password used to log into Review Board. You will need to
provide your current password along with your new one, and then set
:guilabel:`Change Password`.

.. note::

   This depends on your Review Board's authentication settings. If using
   LDAP or Active Directory, you will not be able to change your password.


.. _api-tokens:
.. _my-account-authentication-api-tokens:

API Tokens
----------

.. versionadded:: 2.5

This section allows you to create special tokens for use with Review Board's
API. These allow you to embed the tokens in scripts without having to divulge
your login credentials.

See :ref:`webapi2.0-api-tokens` for details on setting policy and using
tokens.


Creating a Token
~~~~~~~~~~~~~~~~

1. Click :guilabel:`Create a new API token`.

2. Edit the new token, giving it a name, description, optional expiration,
   and access level.

   See below for instructions.

   .. important::

      We recommend setting an expiration and a :ref:`custom token policy
      <api-token-policies>` to restrict access, so that if a token is leaked,
      the damage will be limited.


Editing a Token
~~~~~~~~~~~~~~~

* Click the pencil icon next to the field you want to change (name,
  description, and expiration).

* Click the drop-down to give the token the level of access you need:

  * :guilabel:`Full access`: The token can perform any operation on your
    behalf. This may be dangerous.

  * :guilabel:`Read-only`: The token can read anything you can read, but
    cannot make changes.

  * :guilabel:`Customize`: The token is bound by a custom
    :ref:`token policy <api-token-policies>`.


Removing a Token
~~~~~~~~~~~~~~~~

1. Find the token you want to remove.

2. Click :guilabel:`Remove`.

The token will be immediately revoked and will no longer be able to be used.


.. _my-account-authentication-oauth-tokens:

OAuth Tokens
------------

.. versionadded:: 3.0

If you have any applications which have authenticated using :term:`OAuth2`,
those tokens will be listed in this section and can be revoked.


.. _my-account-oauth2-apps:

OAuth2 Applications
===================

The :guilabel:`OAuth2 Applications` page allows you to create registrations for
your own applications that want to integrate with Review Board. By using
OAuth2, you can allow users of your application to connect it securely to
Review Board without supplying any authentication credentials.

See :ref:`oauth2` for more information about creating applications that use
OAuth2.


.. _my-account-idonethis:

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
