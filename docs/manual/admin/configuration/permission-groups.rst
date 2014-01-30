.. _permission-groups:

=================
Permission Groups
=================

When managing :ref:`users <users>`, it's sometimes useful to give certain
groups of users special abilities in Review Board. For example, giving a
certain group the ability to mark other users' review requests as submitted.

While these permissions can be applied to users individually, it's better to
define special permission groups that the users can belong to.

In most installations with one or two administrators, this feature isn't used.
It's most useful in open source projects when you have a group of developers
who are responsible for committing the contributed patch and then marking the
review request as submitted.


.. _adding-permission-groups:

Adding Permission Groups
========================

To add a new permission group, click the :guilabel:`Add` link next to the
:guilabel:`Groups` entry in the :ref:`Database section <database-management>`
of the :ref:`Administration UI <administration-ui>`. Make sure to choose
:guilabel:`Groups` and not :guilabel:`Review groups`.

A form will appear with the following fields:

* **Name** (required)
    The name of the group. This will only ever be seen in the
    :ref:`Administration UI <administration-ui>`.

* **Permissions** (optional)
    The list of permissions applied to users in the group.

    Most of the permissions have to do with giving users the ability to modify
    things in the
    :ref:`Database section <database-management>` of the
    :ref:`Administration UI <administration-ui>`. The only
    permissions that apply to Review Board itself are:

    * ``reviews | review request | Can change status``
    * ``reviews | review request | Can submit as another user``
    * ``reviews | review request | Can edit review request``

    See :ref:`setting-permissions` for more information.

When done, click :guilabel:`Save` to create the permission group.


Assigning Permission Groups
===========================

To assign a user to a permission group, :ref:`edit the user <editing-users>`
and select the group in the :guilabel:`Groups` box toward the bottom. This is
a multiple selection list. Only highlighted groups are assigned. You can hold
down :kbd:`Control` (on the PC) or :kbd:`Command` (on the Mac) to select
multiple groups.


.. _editing-permission-groups:

Editing Permission Groups
=========================

To edit a permission group, click :guilabel:`Groups` in the
:ref:`Database section <database-management>` of the
:ref:`Administration UI <administration-ui>`. You can then browse to the group
you want to modify and click it.

See :ref:`adding-permission-groups` for a description of each field.

When done, click :guilabel:`Save` to save your changes.


Deleting Permission Groups
==========================

To delete a permission group, follow the instructions in
:ref:`editing-permission-groups` to find the group you want to get rid of.
Then click :guilabel:`Delete` at the bottom of the page.
