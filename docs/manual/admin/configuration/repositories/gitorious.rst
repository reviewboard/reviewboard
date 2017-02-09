.. _repository-hosting-gitorious:

======================
Gitorious Repositories
======================

Review Board supports posting and reviewing code on :rbintegration:`Gitorious
<gitorious>` repositories.

Existing commits in a repository can be browsed and put up for review. Pull
requests, however, are not currently supported (though planned for a future
release).

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. See :ref:`Using RBTools with Git <rbt-post-git>` for
more information.

.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure a Gitorious repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Gitorious` from the
:guilabel:`Hosting type` field.


Step 1: Link Your Gitorious Account
-----------------------------------

You will need to link an account on Gitorious to Review Board, so that Review
Board can access content from the repository. If you've already linked an
account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Service URL`:
    The URL to the root of your Gitorious server. This should *not* have a
    trailing ``/``.

    This option was added in Review Board 2.5.8. If you're using a previous
    version, only Gitorious.org is supported (which is no longer being
    maintained).

:guilabel:`Account username`:
    The username used to log into your Gitorious server. This will be used
    for any Basic HTTP authentication.

:guilabel:`Account password`:
    The password used to log into your Gitorious account. This will be used
    for any Basic HTTP authentication.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Project name`:
    The project name that hosts the repository on Gitorious. This must be the
    name found in the clone URL.

    For example, if your repository was at
    ``https://gitorious.example.com/myproject/myrepo``, your project name
    would be ``myproject``.

:guilabel:`Repository name`:
    The name of the repository. This must be the name found in the clone URL.

    For example, if your repository was at
    ``https://gitorious.example.com/myproject/myrepo``, your project name
    would be ``myrepo``.


Step 3: Choose a Bug Tracker
----------------------------

If you're using the issue tracking feature on this repository, you can simply
check the :guilabel:`Use hosting service's bug tracker` checkbox. All bug IDs
will link to the appropriate issues for your repository.

If you're using a separate bug tracker, or a separate repository on Gitorious,
you can leave the checkbox unchecked and choose a bug tracker from the list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Gitorious's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
