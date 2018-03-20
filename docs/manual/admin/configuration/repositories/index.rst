.. _repositories:

============
Repositories
============

Review Board supports talking to multiple source code repositories of various
types. A single Review Board server can be configured with nearly an unlimited
number of repositories, making it useful in large projects and companies as
well as small. These are managed in the
:ref:`Administration UI <administration-ui>` through either the
:ref:`database section <database-management>` or the
:ref:`administrator-dashboard`.

A repository can be linked up with a supported hosting service. This provides
a fast and easy way to configure a repository without having to figure out
specific paths. See :ref:`hosting-services` for more information.


Managing Repositories
=====================

.. _adding-repositories:

Adding Repositories
-------------------

In order for Review Board to talk to a source code repository, it must first
know how to access it.

To add a new repository, click the :guilabel:`Add` link next to the
:guilabel:`Repositories` entry in the
:ref:`database section <database-management>` or the
:ref:`administrator-dashboard`.

A form will appear with fields split into the following sections:

* `General Information`_
* `Repository Hosting`_
* `Repository Information`_
* `Bug Tracker`_
* `Access Control`_
* `Advanced Settings`_


General Information
~~~~~~~~~~~~~~~~~~~

* **Name** (required)
    This is the human-readable name of the repository that users will see.
    The name can be whatever you like and will appear on the "New Review
    Request" page and in the review request's displayed information.

* **Show this repository** (optional)
    Determines whether or not the repository will be show. If this is
    unchecked, then users won't see the repository in Review Board or
    through third-party applications that talk to Review Board.

    This is most often used for hiding a repository that's no longer in use.


Repository Hosting
~~~~~~~~~~~~~~~~~~

This is a complete list of fields that can be shown in this section. Not all
of them will actually be shown at once. The fields will depend on the
selected `Hosting service`_ and `Repository type`_.

.. _`Hosting service`:

* **Hosting service** (required)
    The source code hosting service this repository will use, if any.
    Review Board provides a list of supported hosting services.

    See :ref:`hosting-services` for more information.

* **Account** (required)
    The account used for the hosting service, if one is used. Select
    :guilabel:`<Link a new account>` to specify a new account for the
    service.

* **Account username** (required)
    The username for the new account, if :guilabel:`<Link a new account>`
    is used.

* **Account password** (required)
    The password for the new account, if :guilabel:`<Link a new account>`
    is used and the hosting service requires a password.


Repository Information
~~~~~~~~~~~~~~~~~~~~~~

This is a partial list of fields that can be shown in this section. The fields
listed will depend on the requirements of the hosting service.

.. _`Repository type`:

* **Repository type** (required)
    This is the type of the repository. This will depend on the
    `Hosting service`_ selected.

* **Repository plan** (required)
    The plan on the hosting service used for this repository, if needed.
    This may be used to specify a public vs. private repository, for
    example.

    This is only shown for certain hosting services.

.. _`Path field`:

* **Path** (required)
    This is the path to the repository on the server. It must be accessible
    by the server running Review Board. The value depends on the repository
    type. See :ref:`determining-repository-information` below for more
    information.

    This is only shown when `Hosting service`_ is set to
    :guilabel:`(None - Custom Repository)`.

.. _`Mirror path field`:

* **Mirror Path** (optional)
    This is an alternate path for the repository that is used during
    lookups. It's usually used when there's separate developer and anonymous
    URLs for the repository, with the anonymous URL entered in
    :guilabel:`Path` and the developer URL entered in :guilabel:`Mirror Path`.
    Review Board will always use the main path when looking up files.

    This is only shown when `Hosting service`_ is set to
    :guilabel:`(None - Custom Repository)`.

    See :ref:`determining-repository-information` below for more
    information on the URLs.

.. _`Raw file URL mask`:

* **Raw file URL mask** (optional)
    The raw file URL mask is a path to a raw file blob on a cgit or Gitweb
    server with special tags that will be substituted to build a real URL to a
    file in the repository. This field is needed when using Review Board with
    a remote Git repository.

    For example:

    * **cgit**:
      ``http://git.gnome.org/browse/gtk+/blob/<filename>?id=<revision>``
    * **Gitweb**:
      ``http://git.kernel.org/?p=bluetooth/bluez-gnome.git;a=blob_plain;f=<filename>;h=<revision>``

    This is only shown when `Hosting service`_ is set to
    :guilabel:`(None - Custom Repository)` and `Repository type`_ is set to
    :guilabel:`Git`.

.. _`Username and Password fields`:
.. _`Username field`:

* **Username** and **Password** (optional)
    Some repositories will require a username and password for access,
    some require only a username, and some don't require either and instead
    allow for anonymous access.

    Subversion repositories, for example, generally provide anonymous access,
    while CVS and Perforce generally require a username but not a password.

    The administrator of the repository should know what is required. This
    varies depending on the setup.

    This may or may not be shown depending on `Hosting service`_ and
    `Repository type`_.


.. _repository-bug-tracker:

Bug Tracker
~~~~~~~~~~~

In most projects, there's a bug tracker associated with the repository
or project, and review requests will often reference bugs.

Review Board will automatically link any bugs to the bug tracker
associated with the repository if this field is provided.


* **Use hosting service's bug tracker** (optional)
   If checked, and if the selected `Hosting service`_ has a built-in
   bug tracker, then that bug tracker will be used for this repository.

   If unchecked, a bug tracker can be specified below.

* **Type**
    The type of bug tracker to use. Depending on your choice here, you may be
    presented with additional fields for choosing the bug tracker.

    If you choose :guilabel:`(Custom Bug Tracker)`, you will be presented
    with a :guilabel:`Bug tracker URL` field, as documented below.

    If you choose :guilabel:`(None)`, bug linking will be disabled for this
    repository.

* **Bug tracker URL** (optional)
    A custom URL to your bug tracker.

    The value of the field should be the path of a bug/ticket, except with
    ``%s`` substituted for the bug/ticket ID.

    For example::

        https://mytracker.example.com/bugs/%s


.. _repository-access-control:

Access Control
~~~~~~~~~~~~~~

Repository access can be limited to certain users and review groups.
See :ref:`access-control` for more information on how this works.

.. _repository-publicly-accessible:

* **Publicly accessible**
    If checked, all users will be able to access review requests and files
    on this repository. Otherwise, they'll only be accessible to users
    or groups that are granted access below.

    By default, this is checked.

* **Users with access** (optional)
    If the repository is not publicly accessible, only users listed here
    will have access to the repository and review requests on it.

* **Review groups with access** (optional)
    If the repository is not publicly accessible, only users on the
    invite-only review groups listed here will have access to the repository
    and review requests on it.


Advanced Settings
~~~~~~~~~~~~~~~~~

* **Encoding** (optional)
    In some cases there's confusion as to the proper encoding to expect from
    files in a repository. You can set this to the proper encoding type (such
    as utf-8) if you need to, but generally you don't want to touch this field
    if things are working fine. You can leave this blank.

When done, click :guilabel:`Save` to create the repository entry.


.. _editing-repositories:

Editing Repositories
--------------------

In the event that you need to change the information on a repository (for
example, if the repository path or the bug tracker URL has changed), you can
edit your repository information by clicking :guilabel:`Repositories` in the
:ref:`administrator-dashboard` or
:ref:`Database section <database-management>` of the
:ref:`Administration UI <administration-ui>`.

See :ref:`adding-repositories` for a description of each field.

When done, click :guilabel:`Save` to save your changes.


Deleting Repositories
---------------------

To delete a repository, follow the instructions in
:ref:`editing-repositories` to find the repository you want to get rid of.
Then click :guilabel:`Delete` at the bottom of the page.

.. warning::

   Deleting a repository will delete any and all review requests, reviews,
   diffs, or other data associated with it. You should never delete a
   repository that has been previously used, unless the server is really
   dead and gone with no replacement (in which case review requests won't be
   able to grab the diff information anyway).


SSH-Backed Repositories
=======================

Many types of repository setups can only be accessed through a working
SSH connection. This requires a public/private key setup, where the
repository to be accessible by a Review Board server providing a pre-approved
SSH key.

Review Board can generate an SSH key to be used with repositories. An existing
SSH key can also be uploaded. Once a key is stored in Review Board, the
accompanying public key can be assigned to the server.

See the :ref:`ssh-settings` documentation on how to configure an SSH key.

Configuring the SSH key access on the repository or on the server hosting
the repository is not covered here. There are plenty of resources on
granting access via SSH keys.


.. _hosting-services:

Hosting Services
================

Review Board can be easily configured to work with different hosting
services. This is a convenient method for specifying the repository paths
and other information necessary to talk to the particular repository.

By changing the `Hosting service`_ field, the list of repository types
(Subversion, Git, etc.) will be limited to the list that the hosting
service supports. The list of fields you need to fill out will also change.

If you're using a custom code repository, whether hosted on a private server
or on some other hosting provider, you can set `Hosting service`_ to
:guilabel:`(None - Custom Repository)` and fill out the information manually

If you have a repository with a hosting service from a version of Review Board
prior to 1.6.7, you will need to set your hosting service again, as the
mechanism for storing and linking hosting services has changed.


Linking Accounts
----------------

When configuring a hosting service, an account must be linked. For some
hosting services, linking an account will first authenticate against the
hosting service and store a token as part of the account.

Some hosting services will require a password as part of the linking
process. The password will not be stored, just used to initially link
the account.


.. _determining-repository-information:

Determining Repository Information
==================================

The `Path field`_ for a repository is very dependent on the type of repository
you're configuring. This section provides some help for determining which
value to use.


.. _configuring-self-hosted-repos:

Configuring Self-Hosted Repositories
====================================

.. toctree::
   :maxdepth: 1

   bazaar
   clearcase
   cvs
   git
   mercurial
   perforce
   subversion


.. _configuring-hosted-repos:

Configuring Hosted Repositories
===============================

.. toctree::
   :maxdepth: 1

   assembla
   aws-codecommit
   beanstalk
   bitbucket
   bitbucket-server
   codebasehq
   fedorahosted
   gerrit
   github
   github-enterprise
   gitlab
   gitorious
   sourceforge
   unfuddle
   visualstudio
