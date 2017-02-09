.. _repository-hosting-fedorahosted:

==========================
Fedora Hosted Repositories
==========================

Review Board supports posting and reviewing code on Fedora Hosted
repositories.

The following types of Fedora Hosted repositories are supported:

* Git
* Mercurial
* Subversion

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier.

.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure a Fedora Hosted repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`Fedora Hosted` from
the :guilabel:`Hosting type` field.


Step 1: Link Your Fedora Hosted Account
---------------------------------------

You will need to link an account on Fedora Hosted to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Account username`:
    The username used to log into your Fedora Hosted account.

:guilabel:`Account password`:
    The password used to log into your Fedora Hosted account.

    Due to some requirements when accessing your repositories, your password
    will be stored in encrypted form in the database.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository type`:
    The type of repository you're adding. This can be either "Git",
    "Mercurial", or "Subversion".

:guilabel:`Repository name`:
    The name of the repository. This must be the name found in the
    checkout/clone URL.


Step 3: Choose a Bug Tracker
----------------------------

If you're using the issue tracking feature on this repository, you can simply
check the :guilabel:`Use hosting service's bug tracker` checkbox. All bug IDs
will link to the appropriate issues for your repository.

If you're using a separate bug tracker, or a separate repository on Fedora
Hosted, you can leave the checkbox unchecked and choose a bug tracker from the
list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Fedora Hosted's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
