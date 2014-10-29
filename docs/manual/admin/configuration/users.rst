.. _users:

=====
Users
=====

Users. Without them, nobody would use Review Board.

Users will receive an account in Review Board when they register or, in LDAP
and NIS configurations, log in for the first time. See :ref:`Authentication`
for more information on this.


.. _`edit the user`:
.. _editing-users:

Editing Users
=============

To edit a user's information, click on :guilabel:`Users` in the
:ref:`Database <database-management>` section or
:ref:`administrator-dashboard` in the
:ref:`Administration UI <administration-ui>`. Find the user to edit and click
the username.

A form will appear with the following fields:

* **Username** (required)
    The username. This is limited to letters, numbers, underscores (``_``),
    periods (``.``), at signs (``@``), apostrophes (``'``), and plus signs
    (``+``).

    This field is usually left unchanged.

* **Password** (required)
    The user's password. The password is encrypted, and shouldn't be changed.

* **First name** (optional)
    The user's first name.

* **Last name** (optional)
    The user's last name.

* **E-mail address** (optional)
    The user's e-mail address.

.. _staff-status:

* **Staff status** (optional)
    This is used to set whether or not this user has access to the
    :ref:`Administration UI <administration-ui>`. Note that this does not
    necessarily give the user the ability to modify the database. For that,
    either Super User status will need to be set, or the user will need the
    appropriate permissions.

    See :ref:`super-users` and :ref:`setting-permissions` for more information.

.. _`Active checkbox`:

* **Active** (optional)
    This is used to set whether or not this user can log in to Review Board.

    See :ref:`disabling-users` for more information.

.. _`Superuser status`:

* **Superuser status** (optional)
    This is used to set whether or not this user is a super user.

    See :ref:`super-users` for more information.

* **User permissions** (optional)
    Specifies the permissions the user has. If Super User status is set,
    then this field is ignored, as being a super user implies having all
    permissions.

    See :ref:`setting-permissions` for more information.

* **Last login** (required)
    The last login time for this user. You shouldn't change this field.

* **Date joined** (required)
    The date and time the user joined Review Board. You shouldn't change
    this field.

* **Groups** (required)
    The :ref:`Permission Groups <permission-groups>` the user is a part of.


Deleting Users
==============

It is generally not a good idea to delete users. Any review requests or
comments made by that user will be deleted. Usually, it is best to
:ref:`disable the user <disabling-users>`.

If you do want to delete the user (such as if the user is generating a lot of
spam), you can find the user by clicking "Users" in the
:ref:`Database section <database-management>` or
:ref:`administrator-dashboard` in the
:ref:`Administration UI <administration-ui>`. At the bottom of the page, click
"Delete."


.. _disabling-users:

Disabling Users
===============

To disable a user, first `edit the user`_ and then uncheck the `Active
checkbox`_. Then save the information. The user will no longer be able to log
in.


.. _super-users:

Super Users
===========

Super users are users that have complete control over the Review Board server.
They can modify the database, change :ref:`settings <settings>`, and even
modify or close out other users' review requests.

A super user has all possible permissions assigned, and do not need to belong
to :ref:`Permission Groups <permission-groups>`. It also implies
:ref:`staff status <staff-status>`.

Because of the power and potential for problems, only the most trusted people
should have super user status.

To make a user a super user, `edit the user`_ and then check the `Superuser
status`_ checkbox. Then save the information.

If you get into a position where there's no super users on the system (such as
if an existing account's super user status is accidentally removed, or the last
super user is no longer with the company or project), you can create a new
super user on the command line. See :ref:`creating-a-super-user`.


.. _setting-permissions:

Setting Permissions
===================

There are a handful of permissions that can be set for users. Most are
used only within the Administration UI, though there are permissions
with special purposes.

To change permissions for a user, `edit the user`_ and then scroll down
to :guilabel:`User permissions`. The left box lists the permissions
available, and the right box lists the permissions currently assigned to
the user.

To find a specific permission, enter part of the name in the search box.
The search will happen automatically.

Permissions are listed in the form of
``app name | model name | permission name``. The app name and model name
reference the part of the database that the permission applies to.

A `super user <super-users>`_ doesn't need to have permissions assigned, as
it's assumed they have all permissions automatically.


"Can add" Permissions
---------------------

These permissions define whether the user can add entries to a table.
The table in question is defined by the ``app name | model name`` portion.


"Can delete" Permissions
------------------------

These permissions define whether the user can delete entries from a table.
The table in question is defined by the ``app name | model name`` portion.


"Can change" Permissions
------------------------

These permissions define whether the user can change existing entries in a
table. The table in question is defined by the ``app name | model name``
portion.

Note that this is different from the :ref:`can-change-status-permission`.


.. _can-submit-as-user-permission:

"Can submit as user" Permission
-------------------------------

This permission (listed as ``reviews | review request | Can submit as user``)
indicates that this user has the ability to post or modify a review request
on another user's behalf through the API. This is useful from a
:term:`post-commit hook`. See :ref:`automating-rbt-post` for more
information.


.. _can-change-status-permission:

"Can change status" Permission
------------------------------

This permission (listed as ``reviews | review request | Can change status``)
indicates that this user can modify the status of another user's review
request. This means they can close the review request, reopen, and discard it.


.. _can-edit-review-request-permission:

"Can edit review request" Permission
------------------------------------

This permission (listed as ``reviews | review request | Can edit review
request``), indicates that the user can edit another user's review request
information (such as the description, testing done, etc).


.. _authentication:

Authentication
==============

The way authentication is handled differs depending on the
:ref:`Authentication Method <authentication-method>` chosen. The main
differences are in the way the password is handled.

Standard authentication will use the password specified for the user.

LDAP and NIS authentication set a dummy password in the password field for
the user. Instead of authenticating against that password field,
authentication will happen against the server.
