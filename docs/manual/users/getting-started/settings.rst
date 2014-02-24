================
Account Settings
================

Overview
========

To get to the account settings page, go to the user menu at the top right of the
page (signified by your gravatar image). From here, select :menuselection:`My
Account`.


Groups
======

If Review Board has review groups, you can choose which groups you'd like to
join using the checkboxes in this section. Review Requests which are assigned
to groups that you are in will show up on your dashboard.


Settings
========

There are a few settings which allow you to affect how you interact with Review
Board:

* **Time zone**
    This setting will change which time zone is used to show times and dates.
    This should be set to the time zone in your current location.

* **Enable syntax highlighting in the diff viewer**
    By default, code is shown using syntax highlighting. If you'd like to turn
    it off, de-select this item.

* **Always open an issue when comment box opens**
    By default, when you create a comment, the "Open an issue" checkbox will
    be pre-selected. If you prefer to opt-in to creating issues for each
    comment, de-select this item.


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
    and when you last logged in. If you'd like to hide this information, select
    this item.


Gravatar Images
===============

Review Board uses the gravatar system to associate photos or pictures with user
accounts. To set your gravatar, go to http://gravatar.com/ and enter the email
address used on your Review Board account.
