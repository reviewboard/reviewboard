.. _repository-scm-sos:

=========================
Cliosoft SOS Repositories
=========================

Review Board supports posting and reviewing code on
:rbintegration:`Cliosoft SOS <cliosoft-sos>` repositories, enabling your team
to review code or other files across all of your projects.

RBTools_ is used to take your pending changes in a workarea and put them up
for review. This is a collection of command line tools that simplifies
working with Review Board. See :ref:`rbtools-workflow-sos` for a guide on how
developers can use RBTools to manage their review requests.


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Requirements
============

For Review Board:

* SOS 7.20 or higher, with a valid license.

* `Power Pack`_ 5.2 or higher, with a valid license. You can `download a trial
  license`_ or `purchase a license`_ for your team.

For developers:

* SOS 7.20 or higher, with a valid license.

* RBTools_ 4 or higher, used to post changes for review.


.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _download a trial license: https://www.reviewboard.org/powerpack/trial/
.. _purchase a license: https://www.reviewboard.org/powerpack/purchase/


.. _repository-scm-sos-connectivity:

Connectivity and SOS Licensing
==============================

Review Board can talk to SOS via:

* **An SSH connection** to a server running SOS.

  This is the recommended way to talk to SOS, and allows you to communicate
  with SOS using any licensed user on a remote server or on the Review Board
  server.

* **Local communication with SOS**.

  This requires SOS to be running on the Review Board server, and requires
  having a license for the web server's user (often ``httpd`` or ``apache2``).

SSH communication is available in `Power Pack`_ 5.2 or higher.

The licensed user in SOS must have read access to all files in all SOS
projects that may need to be posted for review.

Review Board will not write any files or modify any SOS settings.


.. _repository-scm-sos-add-repository:

Adding the Repository
=====================

You will need to complete these steps for each SOS project you want set up in
Review Board.

To get started:

1. :ref:`Add a repository <adding-repositories>`

2. Choose :guilabel:`Repository type -> Cliosoft SOS`.


.. _repository-scm-sos-fields:

Step 1: Fill in the SOS fields
------------------------------

You will need to tell Review Board where your SOS installation is, which
license you want to use, and which SOS server and project this repository will
map to.

You can specify these with the following fields:

:guilabel:`Connection method`:
    The method Review Board will use to talk to SOS. This will be one of:

    * :guilabel:`Connect using SSH (local or remote)`

    * :guilabel:`Local install of SOS`

    We recommend always using SSH. See :ref:`repository-scm-sos-connectivity`
    above.

:guilabel:`Connected SSH server`:
    The hostname and optional port (in ``hostname:port`` form) of the
    server running SOS and SSH.

    *This is only available when choosing SSH connection methods.*

:guilabel:`Connected/licensed user`:
    The username used to SSH into the server. This user must be licensed to
    use SOS (see :ref:`repository-scm-sos-connectivity` above).

    *This is only available when choosing SSH connection methods.*

:guilabel:`SOS installation directory`:
    The absolute path to the SOS installation on the server.

    This is equivalent to :envvar:`CLIOSOFT_DIR` environment variable.

:guilabel:`SOS license`:
    The absolute path to the license file for this installation on the
    target server running SOS, or the port and host for the license server.

    This is equivalent to the :envvar:`CLIOLMD_LICENSE_FILE` or
    :envvar:`LM_LICENSE_FILE` environment variables.

:guilabel:`SOS server name`:
    The name of the SOS server where the project resides.

:guilabel:`SOS project name`:
    The name of the SOS project that this repository will map to.


.. _repository-scm-sos-bug-tracker:

Step 2: Choose a Bug Tracker
----------------------------

You can specify a bug tracker where any bug numbers will link to.

Review Board provides a built-in list of bug trackers, but you can also set
a URL to any additional bug tracker you want to use.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


.. _repository-scm-sos-access-control:

Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it).

.. note::

   This is separate from any access controls defined in SOS! If you need to
   limit SOS project access to individual teams or users, you will need to
   configure access control lists in this repository.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository by clicking
:guilabel:`Save`.

If saving succeeds, you're done on the Review Board side! Let's set up
RBTools.


Step 6: Setting Up RBTools
--------------------------

You'll need to set up RBTools_ to map the project to the repository on
developer machines. The best way is to configure a :file:`.reviewboardrc` file
in the SOS project, making it available for everyone to use.

Place the following in this file:

.. code-block:: python

   REVIEWBOARD_URL = 'https://<server>/'
   REPOSITORY_TYPE = 'sos'
   REPOSITORY = '<configured repository name>'

You can click :guilabel:`RBTools Setup` beside your new repository in the
repository list page to get some sample lines. Make sure to include
``REPOSITORY_TYPE`` along with this!

Now that you're set up, :ref:`learn how to use RBTools with SOS
<rbtools-workflow-sos>`.
