.. _repository-hosting-assembla:

=====================
Assembla Repositories
=====================

Review Board supports posting and reviewing code on :rbintegration:`Assembla
<assembla>` repositories.

The following types of Assembla repositories are supported:

* Perforce
* Subversion

Git is *not* supported due to limitations in the Assembla API.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. If you're using Perforce, this is a requirement.

.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure an Assembla repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Assembla` from the
:guilabel:`Hosting type` field.


Step 1: Link Your Assembla Account
----------------------------------

You will need to link an account on Assembla to Review Board, so that Review
Board can access content from the repository. If you've already linked an
account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Account username`:
    The username used to log into your Assembla account. This is *not*
    your e-mail address.

:guilabel:`Account password`:
    The password used to log into your Assembla account.

    Due to the way the Assembla API must be accessed, your password will be
    stored in encrypted form in the database.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository type`:
    The type of repository you're adding. This can be either "Perforce" or
    "Subversion".

:guilabel:`Project ID`:
    An identifier for your repository. This will depend on the type of
    repository.

    If you selected :guilabel:`Subversion`, then you'll need to provide your
    Subversion space name. This is the name of the repository on Assembla, as
    shown in the UI or in the URL. It would be the ``space_name`` in
    :samp:`https://www.assembla.com/spaces/{space_name}`.

    If you selected :guilabel:`Perforce`, then you'll need to provide your
    Depot Host. Click :guilabel:`P4 -> Instructions` on your Assembla space
    and choose the value in :guilabel:`Depot Host`.


Step 3: Choose a Bug Tracker
----------------------------

If you're using the issue tracking feature on this repository, you can simply
check the :guilabel:`Use hosting service's bug tracker` checkbox. All bug IDs
will link to the appropriate issues for your repository.

If you're using a separate bug tracker, or a separate space on Assembla, you
can leave the checkbox unchecked and choose a bug tracker from the list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Assembla's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
