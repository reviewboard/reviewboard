.. _review-groups:

=============
Review Groups
=============

Review requests are usually posted to one or more review groups, which users
can subscribe to. Every review group has an ID name, a human-readable display
name, and an optional mailing list.


.. _e-mail-and-review-groups:

E-Mail and Review Groups
========================

Review groups may have a mailing list associated with it. If
:ref:`Send e-mails for review requests and reviews <send-e-mails>` is enabled
in :ref:`email-settings`, and a mailing list is associated with a group on
the review request's reviewers list, then e-mails will be sent to the list on
all updates and reviews.

If a mailing list is not provided, and the setting is enabled, e-mails will
instead go out to every user who has joined the review group.


Adding Review Groups
====================

To add a new review group, click the :guilabel:`Add` link next to the
:guilabel:`Review groups` entry in the
:ref:`database section <database-management>` or the
:ref:`administrator-dashboard` in the
:ref:`Administration UI <administration-ui>`. Make sure to
choose :guilabel:`Review groups` and not :guilabel:`Groups`, as the latter
is for :ref:`permission-groups`.

A form will appear with fields split into the following sections:

* `General Information`_
* `Access Control`_


General Information
~~~~~~~~~~~~~~~~~~~

.. _`General Information`:

* **Name** (required)
    This is the ID name of the group. Users will type this when adding the
    group to their reviewers list, and it will appear in their dashboard.

* **Display name** (required)
    This is the human-readable display name that will be shown in the
    browseable Groups list. It should generally be kept short.

* **Mailing list** (optional)
    The mailing list that e-mails will be sent to, if enabled. If not
    provided, e-mails will be sent to all members of the group. See
    `E-Mail and Review Groups`_ for more information.

.. _review-group-visible:

* **Visible**
    If checked, the group is visible to all users. Otherwise, it will be
    hidden from all lists. This is often used in conjunction with
    `Invite only`_.

    By default, this is checked.


Access Control
~~~~~~~~~~~~~~

Review group access can be made invite-only and limited only to the users
the administrator specifically added.

See :ref:`access-control` for more information on how this works.

.. _`Invite only`:
.. _review-group-invite-only:

* **Invite only**
    If checked, the group is invite-only. Users won't be able to add
    themselves to it, requiring the administrator to add them.

    By default, this is not checked.

* **Users** (optional)
    The list of users that belong to the group. This is useful when you
    want to pre-populate a group with specific users. This can usually be
    left blank, since users can join the group themselves.

    The list contains possible users to match. Selected entries are the users
    you want to add. Hold down :kbd:`Control` (on the PC) or :kbd:`Command`
    (on the Mac) to select more than one.

* **Local site** (optional)
    The Local Site to tie this review group to. This is an advanced feature
    that you are unlikely to need.

When done, click :guilabel:`Save` to create the review group.


Editing Review Groups
=====================

To edit a review group, click :guilabel:`Review groups` in the
:ref:`administrator-dashboard` or :ref:`Database section <database-management>`
of the :ref:`Administration UI <administration-ui>`.  You can then browse to
the group you want to modify and click it.

See `Adding Review Groups`_ for a description of each field.

When done, click :guilabel:`Save` to save your changes.


Deleting Review Groups
======================

To delete a review group, follow the instructions in `Editing Review Groups`_
to find the group you want to get rid of. Then click :guilabel:`Delete` at the
bottom of the page.

.. warning::

   It is recommended that you not delete review groups, as it will affect
   existing review requests. It is generally best to keep old groups around
   to keep the review histories intact.
