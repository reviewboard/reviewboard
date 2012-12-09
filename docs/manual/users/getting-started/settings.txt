================
Account Settings
================

Overview
========

To get to the account settings page, go to the user menu at the top right of the
page (signified by your gravatar image). From here, select :menuselection:`My
Account`.


User Preferences
================

Depending on how the Review Board server is configured, you may have the option
to change the real name, e-mail address, and password on your account. These
options are typically not available if Review Board is set up to use some kind
of centralized authentication system such as LDAP or Active Directory.

There are three other user preferences which are always available:

* **Enable syntax highlighting in the diff viewer**
    By default, code is shown using syntax highlighting. If you'd like to turn
    it off, de-select this item.

* **Keep your user profile page private**
    Normally, the user profile page will show your real name, e-mail address,
    and when you last logged in. If you'd like to hide this information, select
    this item.

* **Time zone**
    This setting will change which time zone is used to show times and dates.
    This should be set to the time zone in your current location.


Groups
======

If Review Board has review groups, you can choose which groups you'd like to
join using the check-boxes in this section. Review Requests which are assigned
to groups that you are in will show up on your dashboard.


Gravatar Images
===============

Review Board uses the gravatar system to associate photos or pictures with user
accounts. To set your gravatar, go to http://gravatar.com/ and enter the email
address used on your Review Board account.


.. comment: vim: ft=rst et
